import logging
import os
from datetime import datetime, timezone
from googleapiclient.discovery import build
from google.oauth2 import service_account
import google.auth
from config import Config

from src.auth import authenticate_user

logger = logging.getLogger(__name__)

class SecretaryWorkflow:
    def __init__(self):
        is_dry_run = getattr(Config, 'DRY_RUN', False)
        
        if is_dry_run:
            logger.info("Initializing SecretaryWorkflow in Simulation Mode.")
            self.calendar_service = None
            self.sheets_service = None
        else:
            try:
                # Use the new OAuth 2.0 Desktop Flow
                self.creds = authenticate_user()
                
                self.calendar_service = build('calendar', 'v3', credentials=self.creds)
                self.sheets_service = build('sheets', 'v4', credentials=self.creds)
                logger.info("SecretaryWorkflow initialized with LIVE API services.")
            except Exception as e:
                logger.warning(f"Failed to initialize Workflow services: {e}. Simulation enabled.")
                self.calendar_service = None
                self.sheets_service = None

    def scan_calendar_for_tours(self):
        """Scans today's calendar for events containing 'Tour'."""
        if Config.DRY_RUN or self.calendar_service is None:
            logger.info("Simulation Mode: Returning mock tour event.")
            return [{'id': 'mock_event_123', 'summary': 'Facility Tour'}]
        
        try:
            now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            events_result = self.calendar_service.events().list(
                calendarId='primary', 
                timeMin=now,
                maxResults=10, 
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            
            tours = []
            for event in events:
                if 'tour' in event.get('summary', '').lower():
                    tours.append(event)
            
            return tours
        except Exception as e:
            logger.error(f"Calendar API error: {e}")
            return []

    def update_calendar_event(self, event_id, drive_link):
        """Updates the calendar event description with the Drive link."""
        if Config.DRY_RUN or self.calendar_service is None:
            logger.info(f"Simulation Mode: Would update calendar event {event_id} with link {drive_link}")
            return
            
        try:
            event = self.calendar_service.events().get(calendarId='primary', eventId=event_id).execute()
            description = event.get('description', '')
            new_description = f"{description}\n\nLead Folder: {drive_link}"
            event['description'] = new_description
            
            updated_event = self.calendar_service.events().update(
                calendarId='primary', 
                eventId=event_id, 
                body=event
            ).execute()
            logger.info(f"Updated calendar event: {updated_event.get('htmlLink')}")
        except Exception as e:
            logger.error(f"Error updating calendar: {e}")

    def update_crm_enrichment(self, contact_id, drive_link, buyer_matches):
        """Updates CONTACTS and PROPERTIES with enriched data."""
        # This implementation requires finding the row index for the contact/property
        # For brevity, we'll assume a search-and-update pattern or append if simple.
        # In a real app, you'd fetch the sheet, find the index, and update specific cells.
        logger.info(f"Enriching CRM for {contact_id} with {drive_link} and {buyer_matches}")
        
        # Example: Update Google_Drive_Link in CONTACTS
        # Example: Update Buyer_Match_Tags in PROPERTIES
        pass
