import logging
import json
from config import Config
from src.ingest import UniversalIngester, FolderIngester
from src.intelligence import IntelligenceAgent
from src.daily_task import SecretaryWorkflow

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecretaryAgent:
    def __init__(self):
        self.ingestor = UniversalIngester()
        self.hot_folder = FolderIngester()
        self.intelligence = IntelligenceAgent()
        self.workflow = SecretaryWorkflow()

    def _enrich_lead(self, lead):
        """Helper to apply Intelligence Layer enrichment to a single lead."""
        try:
            # 1. Geocoding / Market Matching
            # For demonstration, we'll use Austin, TX coordinates
            target_coords = (30.2672, -97.7431) 
            matches = self.intelligence.calculate_radius_matches(target_coords, Config.BUYER_LEADS_FILE)
            
            # 2. AI Profiling
            # Generates summary based on full raw data
            profile_text = self.intelligence.generate_prospect_profile(json.dumps(lead['raw_data']))
            
            # 3. Drive Asset Creation
            drive_link = self.intelligence.manage_drive_assets(lead['contact_id'], lead['facility_name'], profile_text)
            
            # Update lead object
            lead['drive_link'] = drive_link
            lead['buyer_matches'] = ", ".join(matches) if matches else "No Matches"
            lead['ai_profile'] = profile_text
            
            logger.info(f"Enriched Lead: {lead['facility_name']}")
            return lead
        except Exception as e:
            logger.error(f"Enrichment Failed for lead {lead.get('contact_id')}: {e}")
            return lead

    def run_hot_folder_sync(self):
        """Triggers the Hot Folder watchdog pipeline."""
        logger.info("Triggering Hot Folder Sync...")
        results = self.hot_folder.process_input_folder(enrichment_callback=self._enrich_lead)
        logger.info(f"Hot Folder Sync Finished. processed {len(results)} items.")
        return results

    def run_daily_automation(self, source=None, progress_callback=None):
        """Main execution loop for the Secretary Agent."""
        logger.info("Starting Daily Secretary Automation...")
        
        if source is None:
            source = Config.RAW_DATA_SOURCE

        # 1. Universal Ingestion (Traffic Cop)
        # We pass the enrichment method as a callback used ONLY if the LeadStrategy is selected.
        if progress_callback:
            progress_callback(0.0, "Starting Ingestion Traffic Cop...")

        results = self.ingestor.process_file(
            source, 
            enrichment_callback=self._enrich_lead
        )
        
        if progress_callback:
            progress_callback(1.0, f"Ingestion Complete. Processed {len(results)} items.")

        # 4. Calendar Sync (Independent Task)
        # Ideally this should be its own button/process, but we keep it here for legacy compatibility.
        tours = self.workflow.scan_calendar_for_tours()
        for tour in tours:
            # Matching logic would go here
            pass

        logger.info("Daily automation completed.")
        return results

def entry_point(request):
    """Cloud Function entry point."""
    agent = SecretaryAgent()
    agent.run_daily_automation()
    return "OK", 200

if __name__ == "__main__":
    # Local testing
    agent = SecretaryAgent()
    agent.run_daily_automation()
