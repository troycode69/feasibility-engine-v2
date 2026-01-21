import sqlite3
import json
import time
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from logic.tractiq_scraper import TractIQScraper

class DataManager:
    def __init__(self, db_path="feasibility.db"):
        self.db_path = db_path
        self._init_db()
        self.geolocator = Nominatim(user_agent="storage_feasibility_app")

    def _init_db(self):
        """Initialize SQLite table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS site_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT,
                lat REAL,
                lon REAL,
                demographics_json TEXT,
                competitors_json TEXT,
                scraped_date TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def get_lat_lon(self, address):
        """Geocodes an address to lat/lon."""
        try:
            location = self.geolocator.geocode(address, timeout=10)
            if location:
                return location.latitude, location.longitude
        except Exception as e:
            print(f"Geocoding error: {e}")
        # Fallback or error if fail
        return None, None

    def get_project_data(self, address):
        """Orchestrates the data retrieval (Cache -> Scrape)."""
        
        # Step 1: Geocode
        lat, lon = self.get_lat_lon(address)
        if not lat:
            return {"error": "Could not geocode address. Please check spelling."}

        # Step 2: Check Cache (SQL)
        cached_data = self._check_cache(lat, lon)
        if cached_data:
            print(f"✅ Loaded from Local SQL Cache for {address}")
            return cached_data

        # Step 3: Cache Miss -> Scrape
        print(f"⚡ Cache Miss! Initiating TractIQ Scraper for {address}...")
        scraper = TractIQScraper()
        
        try:
            scraper.start_session()
            scraper.login()
            scraper.search_site(address)
            
            # Extract
            competitors = scraper.get_competitors()
            demographics = scraper.get_demographics() # Ensure this method exists/is updated
            
            scraper.close_session()
            
            # Step 4: Save to Cache
            self._save_to_cache(address, lat, lon, demographics, competitors)
            
            return {
                "source": "live_scrape",
                "lat": lat,
                "lon": lon,
                "demographics": demographics,
                "competitors": competitors
            }
            
        except Exception as e:
            scraper.close_session()
            import traceback
            traceback.print_exc()
            return {"error": f"Scraper Exception: {str(e)}"}

    def _check_cache(self, lat, lon):
        """
        Query DB for analysis within ~0.1 miles (approx 0.0015 degrees)
        and less than 6 months old.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Simple bounding box for speed
        delta = 0.0015 
        min_lat, max_lat = lat - delta, lat + delta
        min_lon, max_lon = lon - delta, lon + delta
        
        six_months_ago = (datetime.now() - timedelta(days=180)).isoformat()
        
        query = '''
            SELECT demographics_json, competitors_json, scraped_date 
            FROM site_analysis 
            WHERE lat BETWEEN ? AND ? 
            AND lon BETWEEN ? AND ?
            AND scraped_date > ?
            ORDER BY scraped_date DESC
            LIMIT 1
        '''
        
        c.execute(query, (min_lat, max_lat, min_lon, max_lon, six_months_ago))
        row = c.fetchone()
        conn.close()
        
        if row:
            return {
                "source": "cache",
                "lat": lat, # Return query lat/lon for consistency
                "lon": lon,
                "demographics": json.loads(row[0]),
                "competitors": json.loads(row[1]),
                "scraped_date": row[2]
            }
        return None

    def _save_to_cache(self, address, lat, lon, demo, comps):
        """Saves fresh scrape to DB."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO site_analysis (address, lat, lon, demographics_json, competitors_json, scraped_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            address, 
            lat, 
            lon, 
            json.dumps(demo), 
            json.dumps(comps), 
            datetime.now().isoformat()
        ))
        
        conn.commit()
    def get_site_data(self, lat, lon):
        """
        Legacy/Mock wrapper for Home.py initial load.
        Attempts to find cache, otherwise returns placeholder data
        so the user can proceed to the Live Analysis page.
        """
        # 1. Try Cache
        cached = self._check_cache(lat, lon)
        if cached:
            return {
                'lat': lat, 'lon': lon,
                'demographics': cached['demographics'],
                'supply_data': {'competitors': cached['competitors']} # Adapter for old structure
            }
            
        # 2. Return Mock Data (Fallback)
        return {
            'lat': lat,
            'lon': lon,
            'demographics': {
                'population': 50000,
                'median_income': 75000,
                'household_growth': 0.015,
                'tracts_count': 5
            },
            'supply_data': {'competitors': []}
        }
