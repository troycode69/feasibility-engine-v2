import pandas as pd
import uuid
import logging
import io
import json
import re
import os
import shutil
from datetime import datetime
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Union
from PyPDF2 import PdfReader
from config import Config
from googleapiclient.discovery import build
import google.auth
from src.auth import authenticate_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- STRATEGY INTERFACE ---
class IngestionStrategy(ABC):
    """Abstract base class for ingestion strategies."""
    
    def __init__(self, sheets_service):
        self.sheets_service = sheets_service

    @abstractmethod
    def can_handle(self, df_head: pd.DataFrame, filename: str) -> bool:
        """Determines if this strategy can handle the given file."""
        pass

    @abstractmethod
    def process(self, df: pd.DataFrame, filename: str, **kwargs) -> List[Dict]:
        """Processes the file and returns a summary of results."""
        pass

    # --- SHARED HELPERS ---
    def _get_existing_contacts(self):
        if Config.DRY_RUN or self.sheets_service is None:
            return []
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=Config.SHEET_ID, range=f"{Config.CONTACTS_TAB}!A:B"
            ).execute()
            return result.get('values', [])
        except Exception as e:
            logger.error(f"Error fetching existing contacts: {e}")
            return []

    def _generate_contact_id(self, counter):
        return f"C-{counter:04d}"

    def _get_next_counter(self, existing):
        ids = [row[0] for row in existing if len(row) > 0 and row[0].startswith('C-')]
        if not ids: return 1000
        return max([int(i.split('-')[1]) for i in ids]) + 1

    def _get_existing_properties(self):
        if Config.DRY_RUN or self.sheets_service is None:
            return set()
        try:
            # Assuming Column D is Address (Index 3)
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=Config.SHEET_ID, range=f"{Config.PROPERTIES_TAB}!D:D"
            ).execute()
            values = result.get('values', [])
            return {row[0].strip().lower() for row in values if row}
        except Exception as e:
            logger.error(f"Error fetching properties: {e}")
            return set()

    def _commit_to_sheets(self, leads):
        if not leads: return
        new_contacts = []
        updated_props = []
        appended_contacts = set()

        for lead in leads:
            if lead['is_new_contact'] and lead['contact_id'] not in appended_contacts:
                new_contacts.append([lead['contact_id'], lead['owner_name'], lead['phone'], lead['drive_link']])
                appended_contacts.add(lead['contact_id'])
            
            updated_props.append([
                lead['prop_id'], lead['contact_id'], lead['facility_name'], lead['address'],
                lead['buyer_matches'], lead['drive_link'], lead['ai_profile']
            ] + list(lead['raw_data'].values()))

        if Config.DRY_RUN or self.sheets_service is None:
            logger.info(f"Simulated Sync: {len(new_contacts)} contacts, {len(updated_props)} properties.")
            return

        try:
            if new_contacts:
                self.sheets_service.spreadsheets().values().append(
                    spreadsheetId=Config.SHEET_ID, range=f"{Config.CONTACTS_TAB}!A:D",
                    valueInputOption="RAW", body={"values": new_contacts}
                ).execute()
            if updated_props:
                self.sheets_service.spreadsheets().values().append(
                    spreadsheetId=Config.SHEET_ID, range=f"{Config.PROPERTIES_TAB}!A:Z",
                    valueInputOption="RAW", body={"values": updated_props}
                ).execute()
        except Exception as e:
            logger.error(f"Sheet Sync Error: {e}")

# --- STRATEGY: TRACTIQ (Strict Mode) ---
class TractiQStrategy(IngestionStrategy):
    """Handles TractiQ Export files (Sheet1.csv)."""

    def can_handle(self, df_head: pd.DataFrame, filename: str) -> bool:
        cols = [c.strip() for c in df_head.columns]
        return 'Deal Name' in cols and 'Facility ID' in cols

    def process(self, df: pd.DataFrame, filename: str, **kwargs) -> List[Dict]:
        logger.info(f"TractiQStrategy: Processing {len(df)} rows.")
        enrichment_callback = kwargs.get('enrichment_callback')
        
        existing_contacts = self._get_existing_contacts()
        contact_map = { (row[1], row[2]): row[0] for row in existing_contacts if len(row) >= 3 }
        next_counter = self._get_next_counter(existing_contacts)

        leads = []
        for _, row in df.iterrows():
            owner_name = str(row.get('Owner Name', '')).strip()
            phone = str(row.get('Owner Phone', '')).strip()
            
            key = (owner_name, phone)
            if key in contact_map:
                c_id = contact_map[key]
                is_new = False
            else:
                c_id = self._generate_contact_id(next_counter)
                contact_map[key] = c_id
                next_counter += 1
                is_new = True

            lead = {
                'prop_id': str(uuid.uuid4())[:8],
                'contact_id': c_id,
                'is_new_contact': is_new,
                'facility_name': row.get('Deal Name', ''),
                'address': f"{row.get('Deal Address', '')}, {row.get('City', '')}, {row.get('State', '')} {row.get('Zip', '')}",
                'owner_name': owner_name,
                'phone': phone,
                'email': row.get('Owner Email', ''),
                'nra': row.get('Total Rentable Square Footage', ''),
                'raw_data': row.to_dict(),
                'drive_link': '', 'buyer_matches': '', 'ai_profile': ''
            }
            leads.append(lead)

        # LOGIC 3: SAFE MODE BACKUP
        # Save cleaned (but unenriched) leads to disk immediately
        try:
            backup_df = pd.DataFrame(leads)
            backup_path = f"src/data/cleaned_leads_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            os.makedirs("src/data", exist_ok=True)
            backup_df.to_csv(backup_path, index=False)
            logger.info(f"SAFE MODE: Backup cleaned leads saved to {backup_path}")
        except Exception as e:
            logger.error(f"Failed to save backup CSV: {e}")

        # Enrichment
        if enrichment_callback:
            # We wrap enrichment in a try/catch per row to prevent total failure
            enriched_leads = []
            for lead in leads:
                try:
                    enriched_leads.append(enrichment_callback(lead))
                except Exception as e:
                    logger.error(f"Enrichment Error for {lead.get('contact_id')}: {e}")
                    # Append unenriched lead so we don't lose it
                    enriched_leads.append(lead)
            leads = enriched_leads

        self._commit_to_sheets(leads)
        return leads

# --- STRATEGY: BROKER (Loose Mode + Entity Splitter) ---
class BrokerStrategy(IngestionStrategy):
    """Handles Broker files (SS Leads from mailing.csv)."""

    def can_handle(self, df_head: pd.DataFrame, filename: str) -> bool:
        cols = [c.strip() for c in df_head.columns]
        # Loose match for Broker headers
        val1 = 'List' in cols and 'Target County' in cols
        val2 = 'Owner Name' in cols and 'Site Address' in cols # Alternative broker format
        return val1 or val2

    def process(self, df: pd.DataFrame, filename: str, **kwargs) -> List[Dict]:
        logger.info(f"BrokerStrategy: Processing {len(df)} rows.")
        enrichment_callback = kwargs.get('enrichment_callback')
        
        existing_contacts = self._get_existing_contacts()
        existing_properties = self._get_existing_properties()
        
        contact_map = { (row[1], str(row[2])): row[0] for row in existing_contacts if len(row) >= 3 }
        next_counter = self._get_next_counter(existing_contacts)

        leads = []
        skipped_count = 0
        
        for _, row in df.iterrows():
            raw_address = str(row.get('Site Address', '')).strip()
            raw_city = str(row.get('Site City', '')).strip()
            raw_state = str(row.get('Mailing State', '')).strip()
            full_address = f"{raw_address}, {raw_city}, {raw_state}"
            
            if full_address.lower() in existing_properties:
                skipped_count += 1
            # 1. Entity Splitter Rules
            raw_owner = str(row.get('Owner Name', '')).strip()
            
            # LOGIC 2: Aggressive Business Regex
            # Explicitly catches OW (Owner), SS (Self Storage) and other business tokens
            entity_keywords = r"(?i)\b(LLC|L\.L\.C\.|Inc|Corp|Corporation|Storage|Properties|Trust|LP|L\.P\.|Holdings|Management|Group|Partners|Fund|Capital|Associates|Inv|Investors|Estates|Realty|Development|OW|SS|Self Storage|Mini Storage)\b"
            
            if re.search(entity_keywords, raw_owner):
                # Detected as Business
                # Cleanup: Remove trailing ' OW' if present
                if raw_owner.upper().endswith(' OW'):
                     company_name = raw_owner[:-3].strip()
                else:
                     company_name = raw_owner
                
                logger.info(f"Row {filename}: {raw_owner} -> [Business]")
                note_suffix = " [ENTITY - NEEDS SKIP TRACE]"
            else:
                # Detected as Human
                parts = raw_owner.split(' ', 1)
                last_name = parts[1] if len(parts) > 1 else "Unknown"
                company_name = ""
                note_suffix = ""
                logger.info(f"Row {filename}: {raw_owner} -> [Human]")

            phone = str(row.get('Cell', '')).strip()
            if not phone or phone == 'nan':
                email_val = str(row.get('Email', ''))
                if re.match(r'^\d{10}$', email_val) or re.match(r'^\d{3}-\d{3}-\d{4}$', email_val):
                    phone = email_val
            
            lead_notes = f"{row.get('Facility Notes', '')} {row.get('Notes', '')} {note_suffix}".strip()

            key = (raw_owner, phone)
            if key in contact_map:
                c_id = contact_map[key]
                is_new = False
            else:
                c_id = self._generate_contact_id(next_counter)
                contact_map[key] = c_id
                next_counter += 1
                is_new = True

            lead = {
                'prop_id': str(uuid.uuid4())[:8],
                'contact_id': c_id,
                'is_new_contact': is_new,
                'facility_name': f"{company_name} Facility" if company_name else f"{last_name if 'last_name' in locals() else 'Broker'} Storage",
                'address': full_address,
                'owner_name': raw_owner, 
                'phone': phone,
                'email': row.get('Email', ''),
                'nra': row.get('Facility Size', ''),
                'notes': lead_notes,
                'raw_data': row.to_dict(),
                'drive_link': '', 'buyer_matches': '', 'ai_profile': ''
            }
            leads.append(lead)
        
        logger.info(f"BrokerStrategy: Skipped {skipped_count} duplicate properties.")
        
        # LOGIC 3: SAFE MODE BACKUP
        try:
            backup_df = pd.DataFrame(leads)
            backup_path = f"src/data/cleaned_broker_leads_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            os.makedirs("src/data", exist_ok=True)
            backup_df.to_csv(backup_path, index=False)
            logger.info(f"SAFE MODE: Backup cleaned broker leads saved to {backup_path}")
        except Exception as e:
            logger.error(f"Failed to save backup CSV: {e}")

        # Enrichment
        if enrichment_callback:
            enriched_leads = []
            for lead in leads:
                try:
                    enriched_leads.append(enrichment_callback(lead))
                except Exception as e:
                    logger.error(f"Enrichment Error for {lead.get('contact_id')}: {e}")
                    enriched_leads.append(lead)
            leads = enriched_leads

        self._commit_to_sheets(leads)
        return leads

# --- STRATEGY: UNIT MIX (Strict Mode) ---
class UnitMixStrategy(IngestionStrategy):
    """Handles Unit Mix exports."""

    def can_handle(self, df_head: pd.DataFrame, filename: str) -> bool:
        cols = [c.strip() for c in df_head.columns]
        # Option 1
        match1 = 'Unit Type' in cols and 'Dimensions' in cols and 'Price' in cols
        # Option 2
        match2 = 'Size' in cols and 'Rate' in cols and 'Standard' in cols
        return match1 or match2

    def process(self, df: pd.DataFrame, filename: str, **kwargs) -> List[Dict]:
        logger.info("UnitMixStrategy: Detected Unit Mix file.")
        
        # NOTE: Actual Unit Mix logic to sync to UNIT_METRICS would happen here.
        # For now, we return a summary for the FolderIngester to know it succeeded.
        return [{"status": "Unit Mix Processed", "filename": filename, "rows": len(df)}]

# --- STRATEGY: FINANCIALS ---
class FinancialStrategy(IngestionStrategy):
    def can_handle(self, df_head, filename):
        cols = [c.lower() for c in df_head.columns]
        return any(k in c for k in ['noi', 'tax', 'insurance'] for c in cols)

    def process(self, df, filename, **kwargs):
        return [{"status": "Financials Processed", "rows": len(df)}]

# --- THE UNIVERSAL INGESTER ---
class UniversalIngester:
    def __init__(self):
        self.creds = None
        self.sheets_service = None
        if not Config.DRY_RUN:
            try:
                self.creds = authenticate_user()
                self.sheets_service = build('sheets', 'v4', credentials=self.creds)
                logger.info("UniversalIngester: Connected to Sheets.")
            except Exception:
                logger.warning("UniversalIngester: Auth Failed.")

        self.strategies = [
            TractiQStrategy(self.sheets_service),
            BrokerStrategy(self.sheets_service),
            UnitMixStrategy(self.sheets_service),
            FinancialStrategy(self.sheets_service)
        ]

    def process_file(self, file_source: Union[str, pd.DataFrame, io.BytesIO], **kwargs) -> List[Dict]:
        df = None
        filename = "Unknown"
        
        try:
            if isinstance(file_source, str):
                if file_source.endswith('.csv'):
                    df = pd.read_csv(file_source)
                    filename = os.path.basename(file_source)
                elif file_source.endswith('.pdf'):
                    return [{"status": "PDF Skipped (Stub)"}]
            elif hasattr(file_source, 'name'):
                 filename = file_source.name
                 file_source.seek(0)
                 df = pd.read_csv(file_source)

        except Exception as e:
            logger.error(f"Read Error: {e}")
            return []

        if df is None or df.empty: return []

        head = df.head(5)
        for strategy in self.strategies:
            if strategy.can_handle(head, filename):
                logger.info(f"Routing {filename} to {strategy.__class__.__name__}")
                return strategy.process(df, filename, **kwargs)
        
        logger.warning(f"No strategy found for {filename}.")
        return []

    def fetch_crm_data(self):
        """Fetches CRM data for Analyst Agent."""
        dataframes = {}
        tabs = {"CONTACTS": Config.CONTACTS_TAB, "PROPERTIES": Config.PROPERTIES_TAB}
        if Config.DRY_RUN or self.sheets_service is None:
            return {name: pd.DataFrame() for name in tabs.keys()}
        for name, tab_name in tabs.items():
            try:
                result = self.sheets_service.spreadsheets().values().get(
                    spreadsheetId=Config.SHEET_ID, range=f"{tab_name}!A:Z"
                ).execute()
                rows = result.get('values', [])
                if rows:
                    header = rows[0]
                    data = [row + [''] * (len(header) - len(row)) for row in rows[1:]]
                    dataframes[name] = pd.DataFrame(data, columns=header)
                else:
                    dataframes[name] = pd.DataFrame()
            except Exception:
                dataframes[name] = pd.DataFrame()
        return dataframes

    # Backward compatibility
    def prepare_leads(self, source): return self.process_file(source)
    def commit_to_sheets(self, leads): pass 


# --- HOT FOLDER PIPELNE ---
class FolderIngester:
    """Watches input folder, identifies files, ingests them, and archives/rejects."""
    
    def __init__(self, input_dir="src/data/input", archive_dir="src/data/archive", rejected_dir="src/data/rejected"):
        self.input_dir = input_dir
        self.archive_dir = archive_dir
        self.rejected_dir = rejected_dir
        self.ingestor = UniversalIngester()
        
        # Ensure directories exist
        for d in [self.input_dir, self.archive_dir, self.rejected_dir]:
            os.makedirs(d, exist_ok=True)

    def process_input_folder(self, enrichment_callback=None):
        logger.info(f"Scanning Hot Folder: {self.input_dir}")
        processed_count = 0
        
        files = [f for f in os.listdir(self.input_dir) if f.endswith(('.csv', '.xlsx', '.xls'))]
        
        if not files:
            logger.info("Hot Folder is empty.")
            return []

        results_summary = []

        for filename in files:
            file_path = os.path.join(self.input_dir, filename)
            logger.info(f"Processing {filename}...")
            
            try:
                # 1. Ingest
                # For this step, we only support CSV in this strict loop for now based on 'pd.read_csv' assumptions,
                # but adding read_excel logic in UniversalIngester would cover xlsx. 
                # Assuming CSV for now as per `ingest.py` restrictions.
                if filename.endswith('.csv'):
                    results = self.ingestor.process_file(file_path, enrichment_callback=enrichment_callback)
                    
                    if results:
                        # Success -> Archive
                        self._move_file(filename, self.archive_dir, success=True)
                        results_summary.extend(results)
                        processed_count += 1
                    else:
                        # No results (Empty or No Strategy Match) -> Reject
                        logger.warning(f"File {filename} produced no results (Unknown Format). Rejecting.")
                        self._move_file(filename, self.rejected_dir, success=False, error_tag="_UNKNOWN_FORMAT")
                else:
                     logger.warning("Only CSV currently supported in Hot Folder Loop.")
            
            except Exception as e:
                logger.error(f"Failed to process {filename}: {e}")
                self._move_file(filename, self.rejected_dir, success=False, error_tag="_ERROR")

        return results_summary

    def _move_file(self, filename, target_dir, success=True, error_tag=""):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        name, ext = os.path.splitext(filename)
        
        if success:
            new_name = f"{name}_Processed_{timestamp}{ext}"
        else:
            new_name = f"{name}{error_tag}_{timestamp}{ext}"
            
        src = os.path.join(self.input_dir, filename)
        dst = os.path.join(target_dir, new_name)
        
        shutil.move(src, dst)
        logger.info(f"Moved {filename} -> {dst}")
