
import logging
import os
from src.ingest import IngestionEngine
from config import Config

# Configure logging to see EVERYTHING
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DEBUG_SYNC")

def test_sync():
    logger.info("--- STARTING SYNC DEBUG ---")
    
    # 1. Check Configuration
    logger.info(f"PROJECT_ID: {Config.PROJECT_ID}")
    logger.info(f"SHEET_ID: {Config.SHEET_ID}")
    logger.info(f"DRY_RUN: {Config.DRY_RUN}")
    
    # 2. Check for Credentials
    creds_path = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
    if os.path.exists(creds_path):
        logger.info(f"✅ Found ADC Credentials at: {creds_path}")
    else:
        logger.warning("❌ ADC Credentials NOT found at default location (~/.config/gcloud/...)")
        if os.path.exists("service_account.json"):
            logger.info("✅ Found service_account.json in local folder")
        else:
            logger.warning("❌ No service_account.json found either.")

    # 3. Initialize IngestionEngine
    try:
        engine = IngestionEngine()
        logger.info("IngestionEngine initialized.")
        
        if engine.sheets_service is None:
            logger.error("❌ engine.sheets_service is NONE. Sync will fail.")
        else:
            logger.info("✅ engine.sheets_service is initialized.")
            
            # 4. Try actual API call
            logger.info("Attempting to fetch contacts from Google Sheets...")
            contacts = engine.get_existing_contacts()
            logger.info(f"✅ Sheet Fetch Result: {contacts}")
            if contacts is not None:
                logger.info(f"✅ SUCCESS! Found {len(contacts)} rows in the sheet (including header).")
            else:
                logger.warning("⚠️ Connected, but the sheet returned None.")
                
    except Exception as e:
        logger.error(f"❌ CRITICAL FAILURE during debug: {e}", exc_info=True)

if __name__ == "__main__":
    test_sync()
