"""
Context-Aware AI Intelligence Layer
Uses Gemini 1.5 Flash with CRM data injection for intelligent lead analysis
"""

import os
import glob
import pandas as pd
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from config import Config

class IntelligenceAgent:
    """
    CRM Analyst AI powered by Gemini 1.5 Flash.
    Injects latest CRM data into system prompt for context-aware responses.
    Also maintains legacy methods for main.py compatibility.
    """
    
    def __init__(self):
        self.model = None
        self.crm_context = ""
        self.chat_session = None
        self._initialize_model()
        self._load_crm_context()
    
    def _initialize_model(self):
        """Initialize Gemini 1.5 Flash model with auth error handling"""
        try:
            vertexai.init(project=Config.PROJECT_ID, location="us-central1")
            self.model = GenerativeModel("gemini-1.5-flash-001")
        except Exception as e:
            error_msg = str(e)
            if "RefreshError" in error_msg or "DefaultCredentialsError" in error_msg:
                print("⚠️ AI Offline: Google Cloud credentials not found or expired.")
            else:
                print(f"Model initialization failed: {e}")
            self.model = None
    
    def _load_crm_context(self):
        """
        Load the latest cleaned_leads_backup CSV into context.
        This data will be injected into the system prompt.
        """
        try:
            # Find latest backup file
            backup_files = glob.glob("src/data/cleaned_leads_backup_*.csv")
            if not backup_files:
                self.crm_context = "No CRM data available."
                return
            
            latest_file = max(backup_files, key=os.path.getctime)
            df = pd.read_csv(latest_file)
            
            # Convert to string buffer (limit to 100 rows for token efficiency)
            df_sample = df.head(100)
            
            # Create structured context
            context_lines = ["=== CRM DATABASE ==="]
            context_lines.append(f"Total Leads: {len(df)}")
            context_lines.append(f"Columns: {', '.join(df.columns.tolist())}")
            context_lines.append("\n=== LEAD DATA (First 100) ===")
            context_lines.append(df_sample.to_csv(index=False))
            
            self.crm_context = "\n".join(context_lines)
            
        except Exception as e:
            print(f"Failed to load CRM context: {e}")
            self.crm_context = "CRM data loading failed."
    
    def _get_system_prompt(self):
        """
        Generate system prompt with injected CRM context.
        The AI will act as a CRM Analyst, not a generic chatbot.
        """
        return f"""You are a CRM Analyst for a self-storage acquisition firm. Your role is to analyze lead data, identify opportunities, and answer specific questions about contacts in the database.

CRITICAL INSTRUCTIONS:
- You are NOT a generic chatbot. You are a data analyst.
- When asked about leads, ALWAYS reference the actual data provided below.
- Be specific: cite names, companies, locations, and missing information.
- If asked "Which leads in Texas are missing phone numbers?", you must parse the data and list them.
- Format responses as bullet points or tables when appropriate.
- If data is not available, say so explicitly.

{self.crm_context}

Now respond to user queries based on this data."""
    
    def query(self, user_question):
        """
        Send a query to the AI with full CRM context.
        Includes comprehensive error handling for all auth failures.
        """
        if not self.model:
            return "⚠️ AI Offline: Model not initialized. Please check Vertex AI configuration."
        
        try:
            system_prompt = self._get_system_prompt()
            full_prompt = f"{system_prompt}\n\nUSER QUESTION: {user_question}\n\nANALYST RESPONSE:"
            response = self.model.generate_content(full_prompt)
            return response.text
            
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            # Handle specific auth errors
            if "RefreshError" in error_type or "RefreshError" in error_msg:
                return "⚠️ **AI Offline**: Auth Token Expired. Run `gcloud auth application-default login`."
            
            # Handle credential errors
            elif "DefaultCredentialsError" in error_msg or "Could not automatically determine credentials" in error_msg:
                return "⚠️ **AI Offline**: Google Cloud credentials not found. Please run `gcloud auth application-default login` locally to enable AI features."
            
            # Handle 503 service errors
            elif "503" in error_msg or "Service Unavailable" in error_msg:
                return "⚠️ **AI Offline**: Vertex AI service temporarily unavailable. The service may need reauthentication. Run `gcloud auth application-default login`."
            
            # Handle quota/permission errors
            elif "quota" in error_msg.lower() or "permission" in error_msg.lower():
                return f"⚠️ **AI Offline**: {error_msg}"
            
            # Generic fallback
            else:
                return f"⚠️ AI Error: {error_msg[:200]}"
    
    def refresh_context(self):
        """Reload CRM data (call this after new data ingestion)"""
        self._load_crm_context()
    
    # === LEGACY METHODS FOR MAIN.PY COMPATIBILITY ===
    
    def calculate_radius_matches(self, target_coords, buyer_leads_file):
        """Legacy method for main.py"""
        return ["Legacy Match A", "Legacy Match B"]
    
    def generate_prospect_profile(self, raw_data_json):
        """Legacy method for main.py"""
        return "Legacy Profile: High potential prospect based on raw data analysis."
    
    def manage_drive_assets(self, contact_id, facility_name, profile_text):
        """Legacy method for main.py"""
        return "https://drive.google.com/drive/folders/legacy_placeholder"

    def get_context_summary(self):
        """Return summary of loaded context for debugging"""
        lines = self.crm_context.split('\n')
        return '\n'.join(lines[:10]) + f"\n... ({len(lines)} total lines)"



# === GEOCODING HELPER ===
def geocode_address(address):
    """
    Convert address string to lat/lon coordinates using geopy Nominatim.

    Args:
        address: Street address string

    Returns:
        tuple: (latitude, longitude, resolved_address) or (lat, lon, None) if failed
    """
    try:
        from geopy.geocoders import Nominatim

        print(f"🌍 Attempting to geocode: '{address}'")

        # Create geocoder with updated user agent
        geolocator = Nominatim(user_agent="storage_feasibility_engine_v2", timeout=15)

        # Try geocoding with the full address first
        location = geolocator.geocode(address, exactly_one=True, addressdetails=True)

        if location:
            print(f"✅ Geocoded to: {location.address}")
            print(f"   Coordinates: {location.latitude}, {location.longitude}")
            return (location.latitude, location.longitude, location.address)
        else:
            print(f"⚠️ Geocoding returned no results for: {address}")
            # Fallback to NYC if geocoding fails
            return (40.7128, -74.0060, "Fallback: New York, NY (geocoding failed)")
    except Exception as e:
        print(f"❌ Geocoding error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to NYC coordinates
        return (40.7128, -74.0060, f"Fallback: New York, NY (error: {str(e)[:50]})")


def generate_mock_competitors_at_radius(center_lat, center_lon):
    """
    Generate mock competitors at specific distances to appear in radius rings.
    
    Args:
        center_lat: Center latitude
        center_lon: Center longitude
    
    Returns:
        List of competitor dicts with lat, lon, name, rate, occupancy
    """
    import math
    
    # Approximation: 1 degree latitude ≈ 69 miles
    # 1 degree longitude ≈ 69 miles * cos(latitude)
    lat_mi = 69.0
    lon_mi = 69.0 * math.cos(math.radians(center_lat))
    
    competitors = []
    
    # Competitor at 0.8 miles (inside 1-mile ring) - Northeast
    lat_0_8 = center_lat + (0.8 / lat_mi) * 0.7  # NE direction
    lon_0_8 = center_lon + (0.8 / lon_mi) * 0.7
    competitors.append({
        "name": "SecureStore Express",
        "lat": lat_0_8,
        "lon": lon_0_8,
        "rate": 135,
        "occupancy": 92
    })
    
    # Competitor at 2.5 miles (inside 3-mile ring) - Southwest
    lat_2_5 = center_lat - (2.5 / lat_mi) * 0.7  # SW direction
    lon_2_5 = center_lon - (2.5 / lon_mi) * 0.7
    competitors.append({
        "name": "StorMaster Facility",
        "lat": lat_2_5,
        "lon": lon_2_5,
        "rate": 115,
        "occupancy": 88
    })
    
    # Competitor at 4.0 miles (inside 5-mile ring) - Southeast
    lat_4_0 = center_lat - (4.0 / lat_mi) * 0.6  # SE direction
    lon_4_0 = center_lon + (4.0 / lon_mi) * 0.8
    competitors.append({
        "name": "U-Store-It Center",
        "lat": lat_4_0,
        "lon": lon_4_0,
        "rate": 125,
        "occupancy": 85
    })
    
    return competitors


# === PYDECK MAP GENERATOR ===
def generate_pydeck_map(subject_lat, subject_lon, competitors_data, radius_miles=3):
    """
    Generate PyDeck map configuration for Streamlit.
    
    Args:
        subject_lat: Subject site latitude
        subject_lon: Subject site longitude
        competitors_data: List of dicts with {name, lat, lon, rate, occupancy}
        radius_miles: Radius for circles (default 3)
    
    Returns:
        pydeck.Deck object
    """
    import pydeck as pdk
    
    # Subject site layer (Blue pin)
    subject_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{"lat": subject_lat, "lon": subject_lon, "name": "Subject Site"}],
        get_position=["lon", "lat"],
        get_color=[0, 0, 255, 200],
        get_radius=200,
        pickable=True
    )
    
    # Competitor layer (Orange pins)
    competitor_layer = pdk.Layer(
        "ScatterplotLayer",
        data=competitors_data,
        get_position=["lon", "lat"],
        get_color=[255, 140, 0, 200],
        get_radius=150,
        pickable=True
    )
    
    # Dynamic 3-Ring System (Selected Radius, 60%, 20%)
    # Convert miles to meters (1 mile = 1609.34 meters)
    r1 = radius_miles * 1609.34
    r2 = r1 * 0.6
    r3 = r1 * 0.2
    
    circles = [
        {"lat": subject_lat, "lon": subject_lon, "radius": r1, "color": [243, 156, 18, 20]},   # Primary (Orange tint)
        {"lat": subject_lat, "lon": subject_lon, "radius": r2, "color": [12, 35, 64, 30]},    # Secondary (Navy tint)
        {"lat": subject_lat, "lon": subject_lon, "radius": r3, "color": [12, 35, 64, 50]}     # Tertiary (Deep Navy)
    ]
    
    circle_layer = pdk.Layer(
        "ScatterplotLayer",
        data=circles,
        get_position=["lon", "lat"],
        get_radius="radius",
        get_fill_color="color",
        pickable=False,
        stroked=True,
        get_line_color=[12, 35, 64, 150],
        get_line_width=2
    )
    
    # View state
    view_state = pdk.ViewState(
        latitude=subject_lat,
        longitude=subject_lon,
        zoom=12,
        pitch=0
    )
    
    # Create deck
    deck = pdk.Deck(
        layers=[circle_layer, subject_layer, competitor_layer],
        initial_view_state=view_state,
        tooltip={
            "html": "<b>{name}</b><br/>Rate: ${rate}/mo<br/>Occupancy: {occupancy}%",
            "style": {"color": "white"}
        }
    )
    
    return deck
