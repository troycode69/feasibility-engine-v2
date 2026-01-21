import logging
import os
import sys
import pandas as pd
import re
import random
import uuid
import math
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import Config
from googleapiclient.discovery import build
from src.auth import authenticate_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CRMAdjustor")

# --- PARAMETERS & SCHEMAS ---
DRIVE_ANALYSIS_FOLDER_ID = "17ibTmJ_sVBCg61BymJEHMzgLbuJ6wqE7"
INPUT_FOLDER = "src/data/input"

CONTACT_COLS = ['Contact ID', 'Contact Type', 'First Name', 'Last Name', 'Company Name', 'Email', 'Phone', 'Mailing Address', 'Lead Source', 'Lead Date', 'Last Contact', 'Notes']
PROPERTY_COLS = ['Property ID', 'Primary Contact ID', 'Facility Name', 'Site Address', 'City', 'State', 'ZIP', 'Operating Status', 'Stories', 'Year Built', 'Lot Size (Acres)', 'Website', 'Last Sale Date', 'Last Sale Price', 'Outreach']
METRICS_COLS = ['Property ID', 'Gross Drive-Up SF', 'Gross Indoor SF', 'Rentable Drive-Up SF', 'Rentable Indoor SF', 'Total Gross SF', 'Total Rentable SF', 'Climate Controlled']
FINANCIALS_COLS = ['Property ID', 'Assessed Land Value', 'Assessed Improvement Value', 'Assessed Total Value', 'Annual Taxes', 'NOI', 'Cap Rate', 'Estimated Value']
OPPORTUNITY_COLS = ['Opportunity ID', 'Property ID', 'Opportunity Type', 'Stage', 'Estimated Fee', 'Expected Close Date', 'Outreach Potential']

# --- SANITIZER (DEFCON 1) ---
def sanitize_payload(batch_data):
    """
    Iterates through a list of lists and forces every element to be a JSON-safe string.
    Replaces NaN, None, Infinity with "".
    """
    clean_batch = []
    for row in batch_data:
        clean_row = []
        for val in row:
            if val is None:
                clean_row.append("")
                continue
            try:
                if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                    clean_row.append("")
                    continue
                if pd.isna(val):
                    clean_row.append("")
                    continue
            except:
                pass 
            
            s_val = str(val).strip()
            if s_val.lower() == "nan":
                clean_row.append("")
            else:
                clean_row.append(s_val)
        clean_batch.append(clean_row)
    return clean_batch

# --- FUZZY MATCHING HELPERS ---
def normalize_header(header):
    """lowercase and alphanumeric only"""
    return re.sub(r'[^a-z0-9]', '', str(header).lower())

def find_col(row, headers_map, possible_keywords):
    """
    Fuzzy Keyword Matcher.
    headers_map: {normalized_header: actual_header}
    possible_keywords: ['mailingaddr', 'address']
    """
    for kw in possible_keywords:
        # Check if keyword SUBSTRING exists in any header
        for norm_col, actual_col in headers_map.items():
            if kw in norm_col:
                return row.get(actual_col, "")
    return ""

def generate_ids(zip_code, nra, timestamp_batch):
    """
    IDs encoded with Batch Timestamp for Undo capability.
    Format: C-BatchTS-Random
    """
    c_id = f"C-{timestamp_batch}-{random.randint(100, 999)}"
    
    safe_zip = str(zip_code).split('-')[0].strip()
    if not safe_zip.isdigit(): safe_zip = "00000"
    safe_size = str(nra).replace(',', '').replace('.', '').strip()
    if not safe_size.isdigit(): safe_size = "0"
    
    p_id = f"P-{timestamp_batch}-{safe_zip}-{safe_size}"
    o_id = f"O-{timestamp_batch}-{random.randint(100, 999)}"
    
    return c_id, p_id, o_id

# --- DRIVE INDEXER ---
class DriveIndexer:
    def __init__(self, service):
        self.service = service
        self.drive_index = {} 
        self.build_index()

    def build_index(self):
        try:
            query = f"'{DRIVE_ANALYSIS_FOLDER_ID}' in parents and trashed = false"
            results = self.service.files().list(
                q=query, pageSize=1000, fields="nextPageToken, files(id, name, webViewLink)"
            ).execute()
            items = results.get('files', [])
            for item in items:
                name_key = item['name'].lower().replace('.pdf', '').replace('.xlsx', '').strip()
                self.drive_index[name_key] = item['webViewLink']
        except Exception:
            pass

    def find_match(self, address, facility_name):
        addr_clean = str(address).lower().split(',')[0].strip() 
        name_clean = str(facility_name).lower().strip()
        for fname, link in self.drive_index.items():
            if addr_clean and len(addr_clean) > 5 and addr_clean in fname: return link
            if name_clean and len(name_clean) > 5 and name_clean in fname: return link
        return ""

def process_dataframe(df, origin_filename, indexer, batch_ts):
    contacts_buf = []
    props_buf = []
    metrics_buf = []
    finance_buf = []
    opps_buf = []

    headers_map = {normalize_header(c): c for c in df.columns}
    
    is_tractiq = 'dealname' in headers_map or 'tractiq' in origin_filename.lower()
    source = "TractiQ" if is_tractiq else "Broker List"

    for _, row in df.iterrows():
        try:
            # 1. OWNER
            if is_tractiq:
                company = find_col(row, headers_map, ['parcelowner'])
                raw_name = find_col(row, headers_map, ['ownername', 'owner'])
            else:
                raw_name = find_col(row, headers_map, ['ownername', 'owner'])
                company = find_col(row, headers_map, ['company', 'entity'])

            entity_keywords = r"(?i)\b(LLC|Inc|Corp|Storage|Properties|Trust|LP|Holdings|Management|Group|Partners|Fund|Capital)\b"
            if re.search(entity_keywords, str(raw_name)) and not company:
                company = raw_name
                first, last = "", ""
            else:
                parts = str(raw_name).split(' ', 1)
                first = parts[0]
                last = parts[1] if len(parts) > 1 else ""
            contact_type = "Business" if company else "Individual"

            # 2. CONTACT
            mailing = find_col(row, headers_map, ['mailingaddr', 'mailing', 'address'])
            phone = find_col(row, headers_map, ['phone', 'cell', 'mobile', 'contact'])
            email = find_col(row, headers_map, ['email', 'mail'])
            
            # 3. PROPERTY
            site_addr = find_col(row, headers_map, ['dealaddress', 'siteaddress', 'address'])
            city = find_col(row, headers_map, ['sitecity', 'city'])
            state = find_col(row, headers_map, ['sitestate', 'state'])
            zip_code = find_col(row, headers_map, ['zip', 'postal'])
            fac_name = find_col(row, headers_map, ['dealname', 'facilityname', 'name'])
            
            # Broker City Split
            if not state and city:
                parts = str(city).split()
                if len(parts) >= 2 and len(parts[-1]) == 2:
                    state = parts[-1]
                    city = " ".join(parts[:-1])

            # 4. OTHER
            website = find_col(row, headers_map, ['website', 'url', 'web', 'source'])
            date_now = datetime.now().strftime("%Y-%m-%d")
            nra = find_col(row, headers_map, ['rentablesquarefeet', 'nra', 'size'])
            
            c_id, p_id, o_id = generate_ids(zip_code, nra, batch_ts)
            drive_link = indexer.find_match(site_addr, fac_name)
            
            contacts_buf.append([
                c_id, contact_type, first, last, company,
                email, phone, mailing,
                source, date_now, "", 
                find_col(row, headers_map, ['notes'])
            ])
            
            props_buf.append([
                p_id, c_id, fac_name,
                site_addr, city, state, zip_code,
                find_col(row, headers_map, ['operatingstatus', 'status']) or "Active",
                find_col(row, headers_map, ['stories']),
                find_col(row, headers_map, ['structureyear', 'yearbuilt']),
                find_col(row, headers_map, ['acres']),
                website,
                find_col(row, headers_map, ['saledate', 'lastsale']),
                find_col(row, headers_map, ['saleprice', 'lastsaleprice']),
                find_col(row, headers_map, ['outreach'])
            ])
            
            metrics_buf.append([
                p_id, 
                find_col(row, headers_map, ['grossdriveup']),
                find_col(row, headers_map, ['grossindoor']),
                find_col(row, headers_map, ['rentabledriveup']),
                find_col(row, headers_map, ['rentableindoor']),
                find_col(row, headers_map, ['totalgross']),
                nra,
                find_col(row, headers_map, ['climate'])
            ])
            
            finance_buf.append([
                p_id, 
                find_col(row, headers_map, ['landvalue']),
                find_col(row, headers_map, ['improvementvalue']),
                find_col(row, headers_map, ['totalparcelvalue', 'totalvalue']),
                find_col(row, headers_map, ['taxes']), 
                find_col(row, headers_map, ['noi']),
                find_col(row, headers_map, ['caprate']), 
                find_col(row, headers_map, ['estimatedvalue'])
            ])

            opps_buf.append([
                o_id, p_id, "Acquisition", "New", "", "", "High"
            ])
            
        except Exception as e:
            pass # Skip bad rows
            
    return contacts_buf, props_buf, metrics_buf, finance_buf, opps_buf

def run_adjustor_sync():
    """App Entry Point"""
    creds = authenticate_user()
    try:
        drive_service = build('drive', 'v3', credentials=creds)
        sheets_service = build('sheets', 'v4', credentials=creds)
        indexer = DriveIndexer(drive_service)
    except Exception:
        return []
    
    if not os.path.exists(INPUT_FOLDER): os.makedirs(INPUT_FOLDER, exist_ok=True)
    files = [f for f in os.listdir(INPUT_FOLDER) if f != ".DS_Store"]
    processed = []
    
    # GENERATE UNIQUE BATCH TS (YYMMDDHHMM)
    batch_ts = datetime.now().strftime("%y%m%d%H%M")
    
    for fname in files:
        fpath = os.path.join(INPUT_FOLDER, fname)
        try:
            if fpath.endswith('.xlsx'): df = pd.read_excel(fpath)
            elif fpath.endswith('.csv'): df = pd.read_csv(fpath)
            else: continue
            
            c, p, m, f, o = process_dataframe(df, fname, indexer, batch_ts)
            
            def append_to_sheet(tab, data):
                if not data: return
                clean_data = sanitize_payload(data)
                chunk_size = 500
                for i in range(0, len(clean_data), chunk_size):
                    chunk = clean_data[i:i+chunk_size]
                    sheets_service.spreadsheets().values().append(
                        spreadsheetId=Config.SHEET_ID, range=f"{tab}!A1",
                        valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS", body={"values": chunk}
                    ).execute()

            append_to_sheet(Config.CONTACTS_TAB, c)
            append_to_sheet(Config.PROPERTIES_TAB, p)
            append_to_sheet(Config.UNIT_METRICS_TAB, m)
            append_to_sheet(Config.FINANCIALS_TAB, f)
            append_to_sheet(Config.OPPORTUNITIES_TAB, o)
            
            processed.append(fname)
            
            archive_dir = os.path.join("src/data/archive")
            os.makedirs(archive_dir, exist_ok=True)
            os.rename(fpath, os.path.join(archive_dir, f"{batch_ts}_{fname}"))
            
        except Exception as e:
            logger.error(f"Error: {e}")
            
    return processed

def undo_last_upload():
    """
    LOGIC: Fetches last row of CONTACTS. Extracts BatchTS. Clears matched rows in all tabs.
    """
    creds = authenticate_user()
    sheets_service = build('sheets', 'v4', credentials=creds)
    
    # 1. Get Last Row of Contacts to find BatchTS
    res = sheets_service.spreadsheets().values().get(
        spreadsheetId=Config.SHEET_ID, range=f"{Config.CONTACTS_TAB}!A:A"
    ).execute()
    values = res.get('values', [])
    
    if not values or len(values) < 2:
        return "No data to undo."
        
    last_id = values[-1][0] # e.g. C-2601172240-123
    
    # Extract BatchTS (regex C-(\d+)-)
    match = re.search(r"C-(\d+)-", last_id)
    if not match:
        return "Last ID format not recognized. Cannot undo."
        
    batch_ts = match.group(1)
    logger.info(f"Targeting BatchTS for UNDO: {batch_ts}")
    
    undo_count = 0
    
    # 2. Iterate Tabs and Clear matching rows
    tabs = [Config.CONTACTS_TAB, Config.PROPERTIES_TAB, Config.UNIT_METRICS_TAB, Config.FINANCIALS_TAB, Config.OPPORTUNITIES_TAB]
    
    for tab in tabs:
        # Read Column A (IDs)
        res = sheets_service.spreadsheets().values().get(
            spreadsheetId=Config.SHEET_ID, range=f"{tab}!A:A"
        ).execute()
        rows = res.get('values', [])
        
        # Identify ranges to delete (bottom up)
        # Assuming append-only, recent batches are at bottom.
        # Find first index where ID contains batch_ts, delete from there to end?
        # Safer: Find ALL indices. API batchClear is range based.
        
        # Simple Logic: Check if the bottom block matches.
        # If user did mixed operations, this might be tricky.
        # Strict Undo: Only delete if they are at the bottom.
        
        rows_to_delete = 0
        for i in range(len(rows) - 1, 0, -1): # Backward
            row_id = rows[i][0]
            if batch_ts in row_id:
                rows_to_delete += 1
            else:
                break # Stop if we hit a non-matching row (assuming contiguous batch)
        
        if rows_to_delete > 0:
            # Delete rows
            req = {
                "requests": [
                    {
                        "deleteDimension": {
                            "range": {
                                "sheetId": _get_sheet_id(sheets_service, tab),
                                "dimension": "ROWS",
                                "startIndex": len(rows) - rows_to_delete,
                                "endIndex": len(rows)
                            }
                        }
                    }
                ]
            }
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=Config.SHEET_ID, body=req
            ).execute()
            undo_count += rows_to_delete

    return f"Undo Complete. Removed {undo_count} rows from Batch {batch_ts}."

def _get_sheet_id(service, tab_name):
    meta = service.spreadsheets().get(spreadsheetId=Config.SHEET_ID).execute()
    for sheet in meta['sheets']:
        if sheet['properties']['title'] == tab_name:
            return sheet['properties']['sheetId']
    return 0

# === LEAD FILTERING HELPERS ===
def get_actionable_leads(limit=10):
    """
    Returns leads with both Phone AND Email.
    Limit: Top N results.
    """
    try:
        creds = authenticate_user()
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=Config.SHEET_ID,
            range=f"{Config.CONTACTS_TAB}!A:H"
        ).execute()
        
        values = result.get('values', [])
        if len(values) < 2:
            return pd.DataFrame()
        
        df = pd.DataFrame(values[1:], columns=values[0])
        df.columns = [c.lower() for c in df.columns]
        
        # Filter: Has phone AND email
        def has_both(row):
            phone = str(row.get('phone', ''))
            email = str(row.get('email', ''))
            return len(phone) > 5 and len(email) > 5 and '@' in email
        
        actionable = df[df.apply(has_both, axis=1)].head(limit)
        return actionable[['first name', 'last name', 'company name', 'phone', 'email']]
    except:
        return pd.DataFrame()

def get_profile_candidates(limit=8):
    """
    Returns leads with Status = New or FollowUp.
    Limit: Top N results.
    """
    try:
        creds = authenticate_user()
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=Config.SHEET_ID,
            range=f"{Config.CONTACTS_TAB}!A:L"
        ).execute()
        
        values = result.get('values', [])
        if len(values) < 2:
            return pd.DataFrame()
        
        df = pd.DataFrame(values[1:], columns=values[0])
        df.columns = [c.lower() for c in df.columns]
        
        # Filter: Status = New or FollowUp
        if 'lead status' in df.columns:
            candidates = df[df['lead status'].str.lower().isin(['new', 'followup', 'follow-up'])].head(limit)
            return candidates[['first name', 'last name', 'company name', 'lead status']]
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def get_skip_trace_list(limit=20):
    """
    Returns leads missing Phone OR Email (need skip tracing).
    Limit: Top N results.
    """
    try:
        creds = authenticate_user()
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=Config.SHEET_ID,
            range=f"{Config.CONTACTS_TAB}!A:H"
        ).execute()
        
        values = result.get('values', [])
        if len(values) < 2:
            return pd.DataFrame()
        
        df = pd.DataFrame(values[1:], columns=values[0])
        df.columns = [c.lower() for c in df.columns]
        
        # Filter: Missing phone OR email
        def needs_skip_trace(row):
            phone = str(row.get('phone', ''))
            email = str(row.get('email', ''))
            missing_phone = len(phone) < 5 or 'nan' in phone.lower()
            missing_email = len(email) < 5 or '@' not in email
            return missing_phone or missing_email
        
        skip_list = df[df.apply(needs_skip_trace, axis=1)].head(limit)
        return skip_list[['first name', 'last name', 'company name', 'phone', 'email']]
    except:
        return pd.DataFrame()

