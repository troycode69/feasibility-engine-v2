
import pandas as pd
import logging
import re
from config import Config
from src.auth import authenticate_user
from googleapiclient.discovery import build

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CRMCleaner:
    def __init__(self):
        logger.info("Initializing CRM Cleaner...")
        try:
            self.creds = authenticate_user()
            self.service = build('sheets', 'v4', credentials=self.creds)
            self.spreadsheet_id = Config.SHEET_ID
            logger.info("Connected to Google Sheets successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            raise

    def fetch_data(self, tab_name):
        """Fetches all data from a tab into a DataFrame."""
        try:
            range_name = f"{tab_name}!A:Z"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range=range_name).execute()
            rows = result.get('values', [])
            
            if not rows:
                logger.warning(f"No data found in {tab_name}.")
                return pd.DataFrame()

            header = rows[0]
            data = rows[1:]
            
            # Ensure all rows have the same number of columns as header
            data = [row + [''] * (len(header) - len(row)) for row in data]
            
            df = pd.DataFrame(data, columns=header)
            logger.info(f"Fetched {len(df)} rows from {tab_name}.")
            return df
        except Exception as e:
            logger.error(f"Error fetching data from {tab_name}: {e}")
            return pd.DataFrame()

    def push_data(self, tab_name, df):
        """Overwrites a tab with the DataFrame content."""
        try:
            # 1. Clear existing data
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id, range=f"{tab_name}!A:Z").execute()
            
            # 2. Prepare new data
            data = [df.columns.tolist()] + df.values.tolist()
            
            body = {
                'values': data
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id, 
                range=f"{tab_name}!A1",
                valueInputOption='RAW', 
                body=body).execute()
            
            logger.info(f"Updated {tab_name} with {result.get('updatedCells')} cells.")
        except Exception as e:
            logger.error(f"Error pushing data to {tab_name}: {e}")

    def clean_contacts(self):
        """Fixes Entity Resolution in Contacts tab."""
        logger.info("--- Starting Contact Cleaning ---")
        df = self.fetch_data(Config.CONTACTS_TAB)
        if df.empty:
            return

        keywords = ['LLC', 'Inc', 'Storage', 'Management', 'Trust', 'Owner', 'Properties', 'Group']
        pattern = '|'.join(map(re.escape, keywords))
        
        count_fixed = 0
        
        for index, row in df.iterrows():
            first_name = str(row.get('First Name', '')).strip()
            last_name = str(row.get('Last Name', '')).strip()
            
            # Check if First Name looks like a company
            if re.search(pattern, first_name, re.IGNORECASE) or re.search(pattern, last_name, re.IGNORECASE):
                # Construct potential company name
                company_candidate = f"{first_name} {last_name}".strip()
                
                # Move to Company Name if it's currently empty or we want to overwrite 'Unknown'
                # Assuming if we find a keyword, it IS a company.
                current_company = str(row.get('Company Name', '')).strip()
                
                # Logic: Update Company Name, Clear Name fields
                df.at[index, 'Company Name'] = company_candidate
                df.at[index, 'First Name'] = "Unknown"
                df.at[index, 'Last Name'] = ""
                count_fixed += 1

        logger.info(f"Entity Resolution fixed {count_fixed} rows in Contacts.")
        self.push_data(Config.CONTACTS_TAB, df)


    def clean_properties(self):
        """Aligns columns and removes duplicates in Properties tab."""
        logger.info("--- Starting Property Cleaning ---")
        df = self.fetch_data(Config.PROPERTIES_TAB)
        if df.empty:
            return

        # 1. Column Realignment
        expected_cols = ['Property ID', 'Primary Contact ID', 'Facility Name', 'Site Address', 'City', 'State', 'ZIP', 'Operating Status', 'Stories', 'Year Built', 'Lot Size (Acres)', 'NRA', 'Zoning']
        
        # Ensure regex columns exist
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""

        # Create a new clean dataframe with strict column order
        clean_df = df[expected_cols].copy()

        # Clean "No Matches"
        clean_df.replace("No Matches", "", inplace=True)
        clean_df.replace("nan", "", inplace=True)

        # 2. Format ZIP Code (Start with simple cleaning, logic can be expanded)
        def fix_zip(z):
            z = str(z).replace('.0', '').strip()
            if z.lower() in ['nan', 'none', '']:
                return ''
            return z.zfill(5) # Ensure 5 digits
        
        clean_df['ZIP'] = clean_df['ZIP'].apply(fix_zip)

        # 3. Deduplication
        logger.info(f"Rows before deduplication: {len(clean_df)}")
        
        # Normalize Address for deduplication
        clean_df['norm_address'] = clean_df['Site Address'].astype(str).str.lower().str.strip()
        
        # Drop duplicates, keeping the one with more non-empty fields (simple heuristic might be keeping first, 
        # but user asked to keep "most complete". Sort by data completeness first)
        
        # Count non-empty values in each row
        clean_df['completeness'] = clean_df.replace('', pd.NA).notna().sum(axis=1)
        
        # Sort by completeness descending, then drop duplicates on normalized address
        clean_df = clean_df.sort_values('completeness', ascending=False)
        clean_df = clean_df.drop_duplicates(subset=['norm_address'], keep='first')
        
        # Remove helper columns
        clean_df.drop(columns=['norm_address', 'completeness'], inplace=True)
        
        logger.info(f"Rows after deduplication: {len(clean_df)}")
        
        self.push_data(Config.PROPERTIES_TAB, clean_df)

if __name__ == "__main__":
    cleaner = CRMCleaner()
    cleaner.clean_contacts()
    cleaner.clean_properties()
    logger.info("CRM Cleanup Complete!")
