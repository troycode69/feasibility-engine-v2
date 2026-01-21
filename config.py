import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SHEET_ID = os.getenv("SHEET_ID")
    DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    PROJECT_ID = os.getenv("PROJECT_ID", "storageos-acquisitions")
    LOCATION = os.getenv("LOCATION", "us-central1")
    
    # Spreadsheet Tab Names
    CONTACTS_TAB = "CONTACTS"
    PROPERTIES_TAB = "PROPERTIES"
    UNIT_METRICS_TAB = "UNIT_METRICS"
    FINANCIALS_TAB = "FINANCIALS"
    OPPORTUNITIES_TAB = "OPPORTUNITIES"
    
    # Lead Matching Criteria
    BUYER_LEADS_FILE = "Master v2.json"
    RAW_DATA_SOURCE = "TractiQ Export.csv"

    # Execution Mode
    DRY_RUN = os.getenv("DRY_RUN", "False").lower() == "true"
