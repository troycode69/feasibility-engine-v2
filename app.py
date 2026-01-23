import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime
import re

# VERSION MARKER - Force Streamlit Cloud to update
APP_VERSION = "2.4.0-PRODUCTION"

# CRITICAL: Use st.write() early to verify code is deployed
import streamlit as st
st.set_page_config(page_title="Storage Feasibility Engine", layout="wide")
# Debug mode disabled for production

# Add src to path for local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Fallback Config class
class Config:
    SHEET_ID = None
    DRIVE_FOLDER_ID = None
    DRY_RUN = True
    CONTACTS_TAB = "Contacts"
    PROPERTIES_TAB = "Properties"

# Try to import real config
try:
    from config import Config as RealConfig
    Config = RealConfig
except Exception as e:
    print(f"Using fallback Config: {e}")

# Import critical modules with fallbacks
FeasibilityScorer = None
try:
    from scoring_logic import FeasibilityScorer
except Exception as e:
    print(f"FeasibilityScorer unavailable: {e}")

generate_pro_forma = recommend_unit_mix = None
try:
    from financials import generate_pro_forma, recommend_unit_mix
except Exception as e:
    print(f"Financials unavailable: {e}")

render_7year_projection = render_feasibility_score = None
try:
    from projection_display import render_7year_projection, render_feasibility_score
except Exception as e:
    print(f"Projection display unavailable: {e}")

SecretaryAgent = None
try:
    from main import SecretaryAgent
except Exception as e:
    print(f"SecretaryAgent unavailable: {e}")

get_actionable_leads = get_profile_candidates = get_skip_trace_list = run_adjustor_sync = None
try:
    from crm_adjustor import get_actionable_leads, get_profile_candidates, get_skip_trace_list, run_adjustor_sync
except Exception as e:
    print(f"CRM features unavailable: {e}")

IntelligenceAgent = geocode_address = generate_pydeck_map = None
try:
    from intelligence import IntelligenceAgent, geocode_address, generate_pydeck_map
except Exception as e:
    print(f"Intelligence features unavailable: {e}")

get_competitors_realtime = None
try:
    # Detect if we're in Streamlit Cloud
    import os
    import socket

    # Environment detection (silent)
    env_runtime = os.getenv('STREAMLIT_RUNTIME_ENV')
    hostname = os.getenv('HOSTNAME', 'NOT_SET')
    socket_hostname = socket.gethostname()
    users_exists = os.path.exists('/Users')

    # Detect cloud environment
    is_cloud = (
        env_runtime == 'cloud' or
        'streamlit' in hostname.lower() or
        'streamlit' in socket_hostname.lower() or
        not users_exists  # Mac/local usually has /Users
    )

    # Load appropriate scraper based on environment (silent)
    if is_cloud:
        from src.scraper_cloud import get_competitors_realtime_cloud as get_competitors_realtime
    else:
        from src.scraper import get_competitors_realtime
except Exception as e:
    print(f"⚠️ Scraper import failed: {e}")
    import traceback
    traceback.print_exc()

extract_pdf_data = None
try:
    from pdf_processor import extract_pdf_data
except Exception as e:
    print(f"PDF processor unavailable: {e}")

LeaseUpModel = EnhancedLeaseUpModel = None
try:
    from src.leaseup_model import LeaseUpModel
    from src.leaseup_model_v2 import EnhancedLeaseUpModel
except:
    LeaseUpModel = EnhancedLeaseUpModel = None

# CRITICAL: CSV processor for Excel file uploads
extract_csv_data = None
try:
    from src.csv_processor import extract_csv_data
except Exception as e:
    print(f"CSV processor unavailable: {e}")
    # This is critical - show error to user
    # st.error(f"Excel/CSV processing unavailable: {e}") # Suppress error on startup

try:
    from src.feasibility_engine import FeasibilityEngine
except:
    FeasibilityEngine = None
# === TRACTIQ DATA INTEGRATION ===
def load_tractiq_data():
    """
    Loads TractIQ data from session state (uploaded files) or disk.
    Returns a list of competitor dictionaries.
    """
    records = []

    # PRIORITY 1: Use uploaded Excel/CSV data from session state
    if hasattr(st.session_state, 'pdf_ext_data') and st.session_state.pdf_ext_data:
        for file_data in st.session_state.pdf_ext_data.values():
            competitors = file_data.get('competitors', [])
            for comp in competitors:
                # Convert to format expected by merge function
                records.append({
                    "Name": comp.get('name', ''),
                    "Rate": f"${comp['rate_10x10']}" if comp.get('rate_10x10') else "Call for Rate",
                    "Address": comp.get('address', ''),
                    "Source": "TractIQ Upload"
                })
        if records:
            return records

    # FALLBACK: Try to load from disk
    search_dirs = ["src/data", "src/data/input"]
    tractiq_df = pd.DataFrame()
    for d in search_dirs:
        if not os.path.exists(d): continue
        files = [f for f in os.listdir(d) if "tractiq" in f.lower() and f.endswith(".csv")]
        if files:
            # Load the most recent TractiQ file
            latest_file = max([os.path.join(d, f) for f in files], key=os.path.getmtime)
            try:
                tractiq_df = pd.read_csv(latest_file)
                break
            except: continue
    if tractiq_df.empty:
        return []
    # Filter/Normalize columns
    records = []
    headers = {str(c).lower(): c for c in tractiq_df.columns}
    # Fuzzy column finders - Look for rent, exclude sale/purchase
    rate_cols = [c for c in headers if any(k in c for k in ["rate", "price", "rent", "10x10", "standard"]) and "sale" not in c and "purchase" not in c]
    sf_cols = [c for c in headers if any(k in c for k in ["sf", "size", "nra", "rentable"])]
    addr_cols = [c for c in headers if any(k in c for k in ["address", "site", "location"])]
    for _, row in tractiq_df.iterrows():
        name = str(row.get(headers.get("facility name", "Name"), "")).strip() or str(row.get(headers.get("name", "Name"), "")).strip()
        if not name or name == "nan": continue
        # Get rate (priority to 10x10 if found)
        rate_val = "Call for Rate"
        for rc in rate_cols:
            val = row.get(headers[rc])
            if pd.notna(val) and str(val).strip():
                rate_val = f"${int(float(str(val).replace('$','').replace(',','')))}" if str(val).replace('.','').isdigit() else str(val)
                break
        records.append({
            "Name": name,
            "Rate": rate_val,
            "Address": row.get(headers.get(addr_cols[0] if addr_cols else "Address", "Address"), ""),
            "Source": "TractiQ Export"
        })
    return records

def merge_competitor_data(scraper_results):
    """
    Enriches scraper results with TractiQ data.
    """
    t_data = load_tractiq_data()
    if not t_data:
        return scraper_results
    merged = []
    for sc in scraper_results:
        # Fuzzy match by name
        sc_name_clean = re.sub(r'[^a-zA-Z0-9]', '', sc["Name"].lower())
        match = None
        for td in t_data:
            td_name_clean = re.sub(r'[^a-zA-Z0-9]', '', td["Name"].lower())
            if sc_name_clean in td_name_clean or td_name_clean in sc_name_clean:
                match = td
                break
        if match:
            sc["Rate"] = match["Rate"]
            sc["Source"] = "TractiQ Export"
        else:
            sc["Source"] = "Google Maps"
        merged.append(sc)
    return merged

# Set page config with logo as icon
st.set_page_config(page_title="StorSageHQ", page_icon="assets/logo.png", layout="wide")

# === STORSAGE HQ BRANDING (THEME LOCKED) ===

# st.image("assets/logo.png", width=120)  # Removed from main area

# Session state
if "ai_assistant" not in st.session_state:
    st.session_state.ai_assistant = IntelligenceAgent()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "scorer" not in st.session_state:
    st.session_state.scorer = FeasibilityScorer()
if "property_data" not in st.session_state:
    st.session_state.property_data = {"name": "", "address": "", "lat": None, "lon": None}
if "financial_inputs" not in st.session_state:
    # New Format: { "key": {"value": X, "source": "Y"} }
    st.session_state.financial_inputs = {}
if "scoring_sources" not in st.session_state:
    st.session_state.scoring_sources = {}
if "all_competitors" not in st.session_state:
    st.session_state.all_competitors = []
if "pdf_ext_data" not in st.session_state:
    st.session_state.pdf_ext_data = {}
if "feasibility_engine" not in st.session_state and FeasibilityEngine:
    st.session_state.feasibility_engine = FeasibilityEngine()

# Display the logo and title in a horizontal lockup
# === STORSAGE HQ BRANDING (THEME LOCKED) ===
st.markdown("""
<style>
    /* --- 1. GLOBAL RESET --- */
    .stApp {
        background-color: #F4F6F8 !important; /* Light Gray Background */
    }
    
    /* Global Text Defaults - Navy */
    .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp li, .stApp span, .stApp label {
        color: #0C2340 !important;
    }

    /* --- 2. SIDEBAR - SEAMLESS BLEND --- */
    [data-testid="stSidebar"] {
        background-color: #0C2340 !important; /* Exact Brand Navy */
    }
    /* All sidebar text must be White */
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }

    /* --- 3. TOP NAVIGATION HEADER --- */
    /* Container for the Top Nav (Radio Group) */
    div[role="radiogroup"] {
        background-color: #0C2340 !important;
        padding: 10px 20px !important;
        border-radius: 8px !important;
        margin-bottom: 20px !important;
        border: 1px solid #1A3A5C !important;
    }
    /* Nav Items Text (Top Nav Labels) */
    div[role="radiogroup"] p {
        color: #FFFFFF !important; /* Force White Text */
        font-weight: 600 !important;
        background-color: transparent !important;
    }
    div[role="radiogroup"] div {
        color: #FFFFFF !important;
    }
    /* Active Tab Highlight */
    div[role="radiogroup"] [data-checked="true"] + div {
        color: #4A90E2 !important; /* Blue text for active tab */
    }

    /* --- 4. METRIC CARDS --- */
    div[data-testid="metric-container"] {
        background-color: #FFFFFF !important; /* White Card */
        border: 1px solid #0C2340 !important; /* Navy Border */
        border-radius: 8px !important;
        padding: 16px !important;
        box-shadow: 0 2px 4px rgba(12, 35, 64, 0.1) !important;
    }
    /* Label styling */
    [data-testid="stMetricLabel"] {
        color: #0C2340 !important; /* Navy Label */
    }
    /* Value styling */
    [data-testid="stMetricValue"] {
        color: #4A90E2 !important; /* Brand Blue */
        font-weight: 700 !important;
    }

    /* --- 5. INPUTS & BUTTONS --- */
    
    /* FILE UPLOADER - Navy Box, White Text */
    [data-testid="stFileUploader"] {
        background-color: #0C2340 !important;
        border: 1px dashed #FFFFFF !important;
        border-radius: 8px !important;
    }
    [data-testid="stFileUploader"] section {
        background-color: #0C2340 !important;
    }
    /* Force "Drag and drop" text to White */
    [data-testid="stFileUploader"] div, [data-testid="stFileUploader"] span, [data-testid="stFileUploader"] small {
        color: #FFFFFF !important;
    }
    /* "Browse files" button */
    [data-testid="stFileUploader"] button {
        background-color: #FFFFFF !important;
        color: #0C2340 !important;
        border: none !important;
    }

    /* PRIMARY BUTTONS (Rocket/Action) */
    .stButton > button {
        background-color: #0C2340 !important; /* Navy Background */
        color: #FFFFFF !important; /* White Text */
        border: 1px solid #FFFFFF !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }
    .stButton > button:hover {
        background-color: #4A90E2 !important; /* Blue Hover */
        color: #FFFFFF !important;
        border-color: #4A90E2 !important;
    }
    /* Ensure text inside button is white (redundant safety) */
    .stButton > button p {
        color: #FFFFFF !important;
    }

    /* EXPANDERS - Clean White & Navy */
    .streamlit-expanderHeader {
        background-color: #FFFFFF !important;
        color: #0C2340 !important;
        border: 1px solid #E0E0E0 !important;
    }
</style>
""", unsafe_allow_html=True)

# Display the logo and title in a horizontal lockup

# Top Navigation Layout
page = st.radio(
    "Navigation", 
    ["🎯 Command Center", "📊 Market Intel", "💰 Underwriting", "📋 Feasibility Report"], 
    index=0,
    horizontal=True,
    label_visibility="collapsed"
)

# Sidebar - Cleaned up (Logo + TractIQ only)
with st.sidebar:
    st.image("assets/logo.png", use_container_width=True)
    st.markdown("---")
    # TractIQ Cache Management
    st.markdown("### 💾 TractIQ Cache")
    from src.tractiq_cache import list_cached_markets, get_market_stats
    cached_markets = list_cached_markets()
    if cached_markets:
        st.caption(f"{len(cached_markets)} market(s) cached")
        # Show cached markets in expander
        with st.expander("View Cached Markets", expanded=False):
            for market in cached_markets:
                st.markdown(f"**{market['market_name']}**")
                st.caption(f"📊 {market['competitor_count']} competitors | 📁 {market['pdf_count']} PDFs")
                st.caption(f"Updated: {market['last_updated'][:10]}")
                st.markdown("---")
    else:
        st.caption("No cached markets yet")

# === PAGE 1: COMMAND CENTER ===
if page == "🎯 Command Center":
    st.header("Command Center")
    st.caption(f"📅 {datetime.now().strftime('%A, %B %d, %Y')}")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### 🌅 Dashboard")
        @st.cache_data(ttl=60)
        def get_crm_summary():
            if SecretaryAgent is None:
                return 0, 0
            try:
                agent = SecretaryAgent()
                data = agent.ingestor.fetch_crm_data()
                contacts = data.get(Config.CONTACTS_TAB, pd.DataFrame())
                props = data.get(Config.PROPERTIES_TAB, pd.DataFrame())
                return len(contacts), len(props)
            except:
                return 0, 0
        total_contacts, total_props = get_crm_summary()
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Contacts", total_contacts)
        m2.metric("Properties", total_props)
        m3.metric("Feasibility Score", f"{st.session_state.scorer.get_total_score()}/100")
        # === SMART LEAD LISTS ===
        st.markdown("---")
        st.markdown("### 📋 Smart Lead Lists")
        tab1, tab2, tab3 = st.tabs(["✅ Actionable", "🎯 Profile", "🔍 Skip Trace"])
        with tab1:
            st.caption("Leads with Phone & Email")
            if get_actionable_leads is not None:
                actionable = get_actionable_leads(limit=10)
                if not actionable.empty:
                    st.dataframe(actionable, hide_index=True)
                else:
                    st.info("No actionable leads")
            else:
                st.info("CRM features unavailable (cloud environment)")
        with tab2:
            st.caption("Status = New/FollowUp")
            if get_profile_candidates is not None:
                candidates = get_profile_candidates(limit=8)
                if not candidates.empty:
                    st.dataframe(candidates, hide_index=True)
                else:
                    st.info("No profile candidates")
            else:
                st.info("CRM features unavailable (cloud environment)")
        with tab3:
            st.caption("Missing contact info")
            if get_skip_trace_list is not None:
                skip_list = get_skip_trace_list(limit=20)
                if not skip_list.empty:
                    st.dataframe(skip_list, hide_index=True)
                else:
                    st.info("No skip trace needed")
            else:
                st.info("CRM features unavailable (cloud environment)")
        # === CONTEXT-AWARE AI ===
        st.markdown("---")
        st.markdown("### 🤖 CRM Analyst AI (Gemini Flash)")
        st.caption("Ask specific questions about your leads. Example: 'Which leads in Texas are missing phone numbers?'")
        chat_box = st.container(height=300)
        with chat_box:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        if prompt := st.chat_input("Ask about leads, data, or scoring..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.spinner("Analyzing CRM data..."):
                try:
                    response = st.session_state.ai_assistant.query(prompt)
                except Exception as e:
                    # Handle authentication and API errors gracefully
                    error_msg = str(e)
                    if "503" in error_msg or "auth" in error_msg.lower() or "credential" in error_msg.lower():
                        response = "⚠️ **AI Offline**: Please run `gcloud auth application-default login` in your terminal to enable Gemini."
                    else:
                        response = f"⚠️ AI Error: {error_msg}"
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()
    with col2:
        st.markdown("### 📥 Data Ingestion")
        INPUT_FOLDER = "src/data/input"
        os.makedirs(INPUT_FOLDER, exist_ok=True)
        uploaded = st.file_uploader("Upload CRM Data", type=['csv', 'xlsx'])
        if uploaded:
            path = os.path.join(INPUT_FOLDER, uploaded.name)
            with open(path, "wb") as f:
                f.write(uploaded.getbuffer())
            st.success(f"✅ {uploaded.name}")
        staged = [f for f in os.listdir(INPUT_FOLDER) if f != ".DS_Store"]
        if staged:
            st.caption(f"{len(staged)} files staged")
        if st.button("🚀 PROCESS", type="primary"):
            with st.spinner("Processing..."):
                try:
                    result = run_adjustor_sync()
                    st.success(f"✅ {result}")
                    st.session_state.ai_assistant.refresh_context()
                    get_crm_summary.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"{e}")
                except Exception as e:
                    st.error(f"{e}")

# === PAGE 2: MARKET INTEL ===
elif page == "📊 Market Intel":
    st.header("Market Intelligence & Feasibility Scoring")
    filtered_comps = [] # Default to avoid NameError
    # === PROJECT INFO ===
    st.markdown("### 📍 Project Information")
    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("Project Name", value=st.session_state.property_data.get("name", ""), placeholder="e.g. Allspace - Site A")
        subject_address = st.text_input("Subject Address (Natural Language)", value=st.session_state.property_data.get("address", ""), placeholder="e.g. 123 Main St, City, ST")
    with col2:
        st.write(" ") # Spacer for alignment
        st.write(" ")
    if st.button("🔍 Update Map", type="primary"):
        with st.spinner("Geocoding address..."):
            from src.intelligence import geocode_address
            result = geocode_address(subject_address)
            if result and len(result) == 3:
                coords_lat, coords_lon, resolved_addr = result
                st.session_state.property_data = {
                    "name": project_name,
                    "address": subject_address,
                    "lat": coords_lat,
                    "lon": coords_lon,
                    "resolved": resolved_addr
                }
                st.success(f"✅ **Found:** {resolved_addr}")
                st.info(f"📍 Coordinates: Lat {coords_lat:.6f}, Lon {coords_lon:.6f}")
                # PRE-FETCH: Scout full 20 miles immediately
                if get_competitors_realtime:
                    with st.spinner("🔍 Searching for competitors in 20-mile radius..."):
                        try:
                            scout_results = get_competitors_realtime(coords_lat, coords_lon, radius_miles=20)

                            if not scout_results or len(scout_results) == 0:
                                st.warning(f"⚠️ No competitors found within 20 miles.")
                            else:
                                # Enrich with TractiQ
                                enriched_results = merge_competitor_data(scout_results)
                                st.session_state.all_competitors = enriched_results
                                st.success(f"✅ Found {len(enriched_results)} competitors within 20 miles!")
                        except Exception as e:
                            st.error(f"❌ Failed to fetch competitor data: {str(e)}")
                else:
                    st.warning("Real-time competitor scraping unavailable. Upload TractIQ Excel files to add competitor data.")
    # === REAL-TIME COMPETITOR SCRAPING ===
    st.markdown("---")
    st.markdown("### 🕵️ Real-Time Competitive Scouting")
    st.caption("Scrape Google Maps for active competitors and extract websites/pricing.")
    if st.session_state.property_data.get("lat"):
        # Instant Slider (1-20)
        search_radius = st.slider("Trade Area Filter (Miles)", 1, 20, 5)
        # Filter logic (INSTANT)
        all_comps = st.session_state.all_competitors
        filtered_comps = [c for c in all_comps if c["Distance"] <= search_radius]
        # Display map
        try:
            deck = generate_pydeck_map(
                st.session_state.property_data["lat"],
                st.session_state.property_data["lon"],
                filtered_comps,
                radius_miles=search_radius
            )
            st.pydeck_chart(deck, use_container_width=True)
        except Exception as e:
            st.warning(f"Map visualization error: {e}")
        # Data Table
        st.markdown(f"#### 📋 Competitor Analysis ({len(filtered_comps)} facilities within {search_radius}mi)")
        if filtered_comps:
            comps_df = pd.DataFrame(filtered_comps)
            if "Source" not in comps_df.columns:
                comps_df["Source"] = "Google Maps"
            comps_df = comps_df.sort_values("Distance")
            st.dataframe(
                comps_df,
                column_config={
                    "Name": "Facility Name",
                    "Distance": st.column_config.NumberColumn("Distance (mi)", format="%.2f"),
                    "Rate": "Estimated Rate (10x10)",
                    "Source": "Data Source",
                    "Website": st.column_config.LinkColumn("Website"),
                    "Phone": "Phone",
                    "Source Term": "Found Via"
                },
                hide_index=True,
                column_order=("Distance", "Name", "Rate", "Source", "Website", "Phone", "Source Term")
            )
        else:
            st.info("No competitors found in this radius. Try expanding to 10-20 miles.")
    else:
        st.info("📍 Enter subject address and click 'Update Map' to enable scouting.")
    # === TRACTIQ DATA UPLOAD (PDF + CSV Support) ===
    st.markdown("---")
    st.markdown("### 📄 TractIQ Market Data")
    # File Upload - explicitly list Excel formats
    tractiq_files = st.file_uploader(
        "Drop TractIQ files here (PDF reports, CSV, Excel, or any data format)",
        type=['pdf', 'csv', 'xlsx', 'xls'],
        accept_multiple_files=True,
        key="tractiq_uploader",
        help="Upload TractIQ reports or rental comp exports - data is automatically extracted and cached"
    )
    if tractiq_files:
        if len(tractiq_files) > 6:
            st.warning("Maximum 6 files allowed. Using first 6.")
            tractiq_files = tractiq_files[:6]
        # Auto-detect market name from property address
        market_name = None
        if st.session_state.property_data.get('address'):
            # Extract city/metro from address
            address = st.session_state.property_data['address']
            # Simple extraction: take city from address (between last comma and state)
            parts = address.split(',')
            if len(parts) >= 2:
                market_name = parts[-2].strip() # City name
        # Fallback to generic name if no address
        if not market_name:
            market_name = "Market Data"
        # Extract data from all files (PDF and CSV)
        if st.button("🚀 Process Files", type="primary"):
            if not tractiq_files:
                st.warning("Please upload files first.")
            else:
                with st.spinner(f"Processing {len(tractiq_files)} files..."):
                    engine = st.session_state.feasibility_engine
                    if engine:
                        results = engine.process_uploaded_files(tractiq_files, market_name=market_name)
                        
                        # Update Session State
                        processed_data = results.get("results", {})
                        st.session_state.pdf_ext_data.update(processed_data)

                        # Convert Excel competitors to all_competitors format
                        excel_competitors = []
                        for file_data in st.session_state.pdf_ext_data.values():
                            competitors = file_data.get('competitors', [])
                            for comp in competitors:
                                excel_competitors.append({
                                    "Name": comp.get('name', 'Unknown'),
                                    "Address": comp.get('address', ''),
                                    "Distance": comp.get('distance_miles', 0),
                                    "Rate": f"${comp['rate_10x10']}" if comp.get('rate_10x10') else "Call for Rate",
                                    "Source": "TractIQ Upload",
                                    "Units": comp.get('units', 0),
                                    "NRSF": comp.get('nrsf', 0),
                                    "Occupancy": comp.get('occupancy', 0)
                                })
                        # Add to all_competitors
                        if excel_competitors:
                            st.session_state.all_competitors = excel_competitors
                            st.success(f"✅ Loaded {len(excel_competitors)} competitors from uploaded files")

                        # Show Summary
                        summary = results.get("summary", {})
                        st.success(f"✅ Extracted data from {summary['success_count']} files")
                        st.info(results.get("cache_status", ""))
                        
                        # Detailed Results
                        for fname, data in processed_data.items():
                            if data.get('error'):
                                st.error(f"{fname}: {data['error']}")
                            else:
                                with st.expander(f"📊 Details: {fname}", expanded=False):
                                    st.json({
                                        "competitors": len(data.get('competitors', [])),
                                        "rates": len(data.get('extracted_rates', [])),
                                        "unit_mix": list(data.get('unit_mix', {}).keys())
                                    })
                    else:
                        st.error("Feasibility Engine not initialized")
    # === AI-POWERED AUTOMATION ===
    st.markdown("---")
    st.markdown("### 🤖 AI-Powered Analysis")
    st.caption("Automatically analyze site, economic, and competitor data using AI")
    if st.session_state.property_data.get("lat"):
        col_ai1, col_ai2 = st.columns([3, 1])
        with col_ai1:
            st.info("💡 **NEW**: Click below to automatically analyze this site using AI vision, real-time economic data, and competitor intelligence")
        with col_ai2:
            if st.button("🚀 Run AI Analysis", type="primary", use_container_width=True):
                engine = st.session_state.feasibility_engine
                if not engine:
                    st.error("AI Engine unavailable")
                else:
                    try:
                        address = st.session_state.property_data.get('address')
                        lat = st.session_state.property_data.get('lat')
                        lon = st.session_state.property_data.get('lon')
                        
                        if not lat or not lon:
                            st.warning("Please update map coordinates first.")
                        else:
                            # Initialize results container
                            if 'ai_results' not in st.session_state:
                                st.session_state.ai_results = {}

                            # Create status containers
                            status_site = st.status("Analyzing site...", expanded=False)
                            status_demo = st.status("Fetching demographics...", expanded=False)
                            status_econ = st.status("Fetching economic data...", expanded=False)
                            status_comp = st.status("Analyzing competitors...", expanded=False)
                            
                            statuses = {
                                "site": status_site,
                                "demographics": status_demo,
                                "economic": status_econ,
                                "competitors": status_comp
                            }
                            
                            # Stream results from generator
                            for update in engine.run_ai_analysis_orchestration(
                                address=address, lat=lat, lon=lon, filtered_comps=filtered_comps
                            ):
                                step = update["step"]
                                status_widget = statuses.get(step)
                                
                                if update["status"] == "running":
                                    status_widget.update(label=update["message"], state="running")
                                elif update["status"] == "complete":
                                    # Update session state with result
                                    st.session_state.ai_results[step] = update["data"]
                                    # Update UI
                                    if "error" in update["data"]:
                                        status_widget.update(label=f"❌ {step.title()} Failed", state="error")
                                        st.error(f"{step}: {update['data']['error']}")
                                        # Keep expanded if error
                                        status_widget.update(expanded=True) 
                                    else:
                                        status_widget.update(label=f"✅ {step.title()} Complete", state="complete")
                            
                            st.success("🎉 AI Analysis Complete!")
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"Analysis failed: {e}")
        # Display AI Results
        if 'ai_results' in st.session_state and st.session_state.ai_results:
            st.markdown("---")
            st.markdown("#### 📊 AI Analysis Results")
            col_site, col_demo, col_econ, col_comp = st.columns(4)
            with col_site:
                st.markdown("**🏗️ Site Analysis**")
                if 'site' in st.session_state.ai_results:
                    site_data = st.session_state.ai_results['site']
                    if site_data.get('has_street_view'):
                        st.success("✅ AI Vision")
                        st.write(f"**Visibility:** {site_data['visibility']}")
                        st.write(f"**Access:** {site_data['access']}")
                        with st.expander("View Reasoning"):
                            st.write(site_data.get('reasoning', 'No reasoning available'))
                    else:
                        st.warning("⚠️ No Street View")
                        st.caption("Using defaults")
            with col_demo:
                st.markdown("**👥 Demographics**")
                if 'demographics' in st.session_state.ai_results:
                    demo_data = st.session_state.ai_results['demographics']
                    st.success("✅ Census API")
                    st.write(f"**Pop (3mi):** {demo_data.get('pop_3mi', 0):,}")
                    st.write(f"**Income:** ${demo_data.get('median_income', 0):,}")
                    st.write(f"**Growth:** {demo_data.get('growth_rate', 0)}%")
                    st.write(f"**Renter %:** {demo_data.get('renter_pct', 0)}%")
                    st.write(f"**Age 25-54:** {demo_data.get('age_25_54_pct', 0)}%")
                    st.caption(f"{demo_data.get('data_source', 'Census')}")
                else:
                    st.info("Using defaults")
            with col_econ:
                st.markdown("**📊 Economic**")
                if 'economic' in st.session_state.ai_results:
                    econ_data = st.session_state.ai_results['economic']
                    st.success("✅ BLS API")
                    st.write(f"**Unemployment:** {econ_data['unemployment']}%")
                    st.write(f"**Growth:** {econ_data['business_growth']}")
            with col_comp:
                st.markdown("**🏢 Competitors**")
                if 'competitors' in st.session_state.ai_results:
                    comp_data = st.session_state.ai_results['competitors']
                    st.success("✅ AI Analyzed")
                    st.write(f"**Count:** {comp_data['count']} facilities")
                    st.write(f"**Quality:** {comp_data['quality']}")
                    st.write(f"**Pricing:** {comp_data['pricing']}")
    else:
        st.info("📍 Enter a subject address above and click 'Update Map' to enable AI analysis")
    # === FEASIBILITY SCORING (STRICT RUBRIC) ===
    st.markdown("---")
    st.markdown("### 🎯 Feasibility Scoring Matrix")
    st.caption("Based on Allspace Storage Rubric - 100 Point System")
    scorer = st.session_state.scorer
    # Demographics (25 pts) - WITH FULL RUBRIC TABLE
    with st.expander("👥 Demographics (25 points)", expanded=True):
        # Auto-fill ALL demographics from AI if available
        default_pop_3mi = 50000
        default_income = 65000
        default_growth = 2.0
        default_renter_pct = 35
        default_age_pct = 40
        if 'ai_results' in st.session_state and 'demographics' in st.session_state.ai_results:
            demo_data = st.session_state.ai_results['demographics']
            default_pop_3mi = demo_data.get('pop_3mi', 50000)
            default_income = demo_data.get('median_income', 65000)
            default_growth = demo_data.get('growth_rate', 2.0)
            default_renter_pct = demo_data.get('renter_pct', 35)
            default_age_pct = demo_data.get('age_25_54_pct', 40)
            st.success(f"✅ All demographics loaded from Census API (ACS 5-Year 2022)")
        col1, col2 = st.columns(2)
        with col1:
            pop_3mi = st.number_input("Population (3mi)", value=int(default_pop_3mi), step=5000)
            income = st.number_input("Median Income ($)", value=int(default_income), step=5000)
            growth = st.number_input("Growth Rate (%)", value=float(default_growth), step=0.5)
        with col2:
            renter_pct = st.number_input("Renter %", value=float(default_renter_pct), step=5.0)
            age_pct = st.number_input("Age 25-54 %", value=float(default_age_pct), step=1.0,
                help="Percentage of population aged 25-54 (prime storage demographic)")
        demo_score = scorer.calculate_demographics_score(pop_3mi, income, growth, renter_pct, age_pct)
        st.metric("Demographics Score", f"{demo_score}/25")
        st.caption("🔍 **Source of Truth:** Census Bureau (ACS 5-Year Estimates)")
        # Display rubric breakdown (your scores)
        st.markdown("#### 📊 Your Scores")
        rubric_data = scorer.get_demographics_rubric(pop_3mi, income, growth, renter_pct, age_pct)
        rubric_df = pd.DataFrame(rubric_data, columns=["Metric", "Score", "Max", "Your Value", "Rubric Tier"])
        st.dataframe(rubric_df, hide_index=True)
        # Display full rubric standards (good vs bad)
        st.markdown("#### 📋 Full Rubric Standards")
        full_rubric = scorer.get_rubric_dict()["Demographics"]
        rubric_standards_df = pd.DataFrame([
            {"Metric": k, "Scoring Range": v}
            for k, v in full_rubric.items()
        ])
        st.dataframe(rubric_standards_df, hide_index=True)
    # Supply (25 pts)
    with st.expander("📦 Supply Analysis (25 points)"):
        col1, col2 = st.columns(2)
        with col1:
            sf_per_cap = st.number_input("SF per Capita", value=5.5, step=0.5)
            occupancy = st.number_input("Avg Occupancy %", value=87, step=1)
        with col2:
            # AUTO-FILL FROM PDF if available
            pdf_risk = "Standard"
            if st.session_state.pdf_ext_data:
                all_risks = [v['pipeline_risk'] for v in st.session_state.pdf_ext_data.values()]
                if any("High" in r for r in all_risks): pdf_risk = "High"
                elif any("Moderate" in r for r in all_risks): pdf_risk = "Moderate"
            default_trend = "Strong" if pdf_risk == "Standard" else "Moderate"
            trend = st.selectbox("Absorption Trend", ["Strong", "Moderate", "Weak", "Declining"],
                index=["Strong", "Moderate", "Weak", "Declining"].index(default_trend))
            default_pipeline = 0.8
            if pdf_risk == "High": default_pipeline = 4.5 # High risk placeholder
            elif pdf_risk == "Moderate": default_pipeline = 1.5
            pipeline = st.number_input("Pipeline SF per Capita", value=default_pipeline, step=0.1)
        supply_score = scorer.calculate_supply_score(sf_per_cap, occupancy, trend, pipeline)
        st.metric("Supply Score", f"{supply_score}/25")
        source_label = "Manual Input"
        if st.session_state.pdf_ext_data:
             source_label = "Uploaded Market Report (PDF Extraction)"
        st.caption(f"🌍 **Source of Truth:** {source_label}")
        # Breakdown
        st.markdown("#### 📊 Your Scores")
        supply_rubric_data = scorer.get_supply_rubric(sf_per_cap, occupancy, trend, pipeline)
        supply_df = pd.DataFrame(supply_rubric_data, columns=["Metric", "Score", "Max", "Value", "Rubric Tier"])
        st.dataframe(supply_df, hide_index=True)
        # Standards
        st.markdown("#### 📋 Full Rubric Standards")
        supply_standards = scorer.get_rubric_dict()["Supply"]
        supply_standards_df = pd.DataFrame([{"Metric": k, "Scoring Range": v} for k, v in supply_standards.items()])
        st.dataframe(supply_standards_df, hide_index=True)
    # Site (25 pts)
    with st.expander("🏗️ Site Attributes (25 points)"):
        # Auto-fill from AI if available
        default_visibility = "Good"
        default_access = "Good"
        default_size = "Adequate"
        if 'ai_results' in st.session_state and 'site' in st.session_state.ai_results:
            site_data = st.session_state.ai_results['site']
            default_visibility = site_data.get('visibility', 'Good')
            default_access = site_data.get('access', 'Good')
            default_size = site_data.get('site_size', 'Adequate')
            st.success("✅ AI values loaded - you can adjust manually if needed")
        col1, col2 = st.columns(2)
        with col1:
            visibility = st.selectbox("Visibility", ["Excellent", "Good", "Fair", "Poor"],
                index=["Excellent", "Good", "Fair", "Poor"].index(default_visibility))
            access = st.selectbox("Access", ["Excellent", "Good", "Fair", "Poor"],
                index=["Excellent", "Good", "Fair", "Poor"].index(default_access))
        with col2:
            zoning = st.selectbox("Zoning", ["Permitted", "Conditional", "Requires Variance"])
            size = st.selectbox("Size Adequacy", ["Ideal", "Adequate", "Marginal", "Insufficient"],
                index=["Ideal", "Adequate", "Marginal", "Insufficient"].index(default_size))
        site_score = scorer.calculate_site_score(visibility, access, zoning, size)
        st.metric("Site Score", f"{site_score}/25")
        # Breakdown
        st.markdown("#### 📊 Your Scores")
        site_rubric_data = scorer.get_site_rubric(visibility, access, zoning, size)
        site_df = pd.DataFrame(site_rubric_data, columns=["Metric", "Score", "Max", "Value", "Rubric Tier"])
        st.dataframe(site_df, hide_index=True)
        # Standards
        st.markdown("#### 📋 Full Rubric Standards")
        site_standards = scorer.get_rubric_dict()["Site"]
        site_standards_df = pd.DataFrame([{"Metric": k, "Scoring Range": v} for k, v in site_standards.items()])
        st.dataframe(site_standards_df, hide_index=True)
    # Competitor (15 pts)
    with st.expander("🎯 Competitor Analysis (15 points)"):
        # Auto-fill from AI if available
        default_comp_count = 4
        default_comp_quality = "Average"
        default_pricing = "At Market"
        if 'ai_results' in st.session_state and 'competitors' in st.session_state.ai_results:
            comp_data = st.session_state.ai_results['competitors']
            default_comp_count = comp_data.get('count', 4)
            default_comp_quality = comp_data.get('quality', 'Average')
            default_pricing = comp_data.get('pricing', 'At Market')
            st.success("✅ AI values loaded from competitor analysis - you can adjust manually if needed")
        elif st.session_state.pdf_ext_data:
            # Fallback to PDF if AI not run
            all_rates = []
            for v in st.session_state.pdf_ext_data.values():
                all_rates.extend(v['extracted_rates'])
            if all_rates:
                avg_rate = sum(all_rates) / len(all_rates)
                if avg_rate > 150: default_pricing = "Above Market"
                elif avg_rate < 100: default_pricing = "Below Market"
        col1, col2, col3 = st.columns(3)
        with col1:
            comp_count = st.number_input("Competitors (3mi)", value=default_comp_count, step=1)
        with col2:
            comp_quality = st.selectbox("Quality", ["Aging/Poor", "Average", "Modern/Strong"],
                index=["Aging/Poor", "Average", "Modern/Strong"].index(default_comp_quality))
        with col3:
            pricing = st.selectbox("Pricing Position", ["Above Market", "At Market", "Below Market"],
                index=["Above Market", "At Market", "Below Market"].index(default_pricing))
        comp_score = scorer.calculate_competitor_score(comp_count, comp_quality, pricing)
        st.metric("Competitor Score", f"{comp_score}/15")
        comp_source = "Google Maps Scraper"
        if any(c.get("Source") == "TractiQ Export" for c in filtered_comps):
            comp_source = "TractiQ Export (+ Google Maps)"
        st.caption(f"🎯 **Source of Truth:** {comp_source}")
        # Breakdown
        st.markdown("#### 📊 Your Scores")
        comp_rubric_data = scorer.get_competitor_rubric(comp_count, comp_quality, pricing)
        comp_df = pd.DataFrame(comp_rubric_data, columns=["Metric", "Score", "Max", "Value", "Rubric Tier"])
        st.dataframe(comp_df, hide_index=True)
        # Standards
        st.markdown("#### 📋 Full Rubric Standards")
        comp_standards = scorer.get_rubric_dict()["Competitor"]
        comp_standards_df = pd.DataFrame([{"Metric": k, "Scoring Range": v} for k, v in comp_standards.items()])
        st.dataframe(comp_standards_df, hide_index=True)
    # Economic (10 pts)
    with st.expander("💼 Economic Indicators (10 points)"):
        # Auto-fill from AI if available
        default_unemployment = 4.5
        default_biz_growth = "Moderate"
        default_stability = "Stable"
        if 'ai_results' in st.session_state and 'economic' in st.session_state.ai_results:
            econ_data = st.session_state.ai_results['economic']
            default_unemployment = econ_data.get('unemployment', 4.5)
            default_biz_growth = econ_data.get('business_growth', 'Moderate')
            default_stability = econ_data.get('stability', 'Stable')
            st.success("✅ AI values loaded from BLS API - you can adjust manually if needed")
        col1, col2, col3 = st.columns(3)
        with col1:
            unemployment = st.number_input("Unemployment %", value=default_unemployment, step=0.5)
        with col2:
            biz_growth = st.selectbox("Business Growth", ["Strong", "Moderate", "Weak"],
                index=["Strong", "Moderate", "Weak"].index(default_biz_growth))
        with col3:
            stability = st.selectbox("Economic Stability", ["Stable", "Moderate", "Volatile"],
                index=["Stable", "Moderate", "Volatile"].index(default_stability))
        econ_score = scorer.calculate_economic_score(unemployment, biz_growth, stability)
        st.metric("Economic Score", f"{econ_score}/10")
        # Breakdown
        st.markdown("#### 📊 Your Scores")
        econ_rubric_data = scorer.get_economic_rubric(unemployment, biz_growth, stability)
        econ_df = pd.DataFrame(econ_rubric_data, columns=["Metric", "Score", "Max", "Value", "Rubric Tier"])
        st.dataframe(econ_df, hide_index=True)
        # Standards
        st.markdown("#### 📋 Full Rubric Standards")
        econ_standards = scorer.get_rubric_dict()["Economic"]
        econ_standards_df = pd.DataFrame([{"Metric": k, "Scoring Range": v} for k, v in econ_standards.items()])
        st.dataframe(econ_standards_df, hide_index=True)
    # === TOTAL SCORE ===
    st.markdown("---")
    total = scorer.get_total_score()
    recommendation = scorer.get_recommendation()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
        <div class="score-card">
            <h1 style="color: white; margin: 0;">{total}/100</h1>
            <p style="color: white; margin: 10px 0 0 0; font-size: 18px;">TOTAL FEASIBILITY SCORE</p>
            <p style="color: white; margin: 10px 0 0 0; font-size: 16px;">{recommendation['decision']}</p>
        </div>
        """, unsafe_allow_html=True)

# === PAGE 3: UNDERWRITING ===
elif page == "💰 Underwriting":
    st.header("Financial Underwriting & 7-Year Projection")
    # Pull property data from Market Intel if available
    property_address = st.session_state.property_data.get('address', '')
    st.markdown("### 🏢 Property Inputs")
    col1, col2, col3 = st.columns(3)
    with col1:
        property_name = st.text_input("Property Name", value=st.session_state.property_data.get('name', ''),
            placeholder="e.g. Allspace - Site A")
        total_sf = st.number_input("Total NRA (SF)", value=105807, step=1000,
            help="Net Rentable Area")
    with col2:
        address_input = st.text_input("Address", value=property_address,
            placeholder="123 Main St, City, ST")
        total_units = st.number_input("Total Units", value=684, step=10)
    with col3:
        start_date = st.date_input("Projection Start", value=datetime(2026, 1, 31))
    # Infer starting rate from competitor data if available
    default_rate = 17.79
    if st.session_state.all_competitors:
        # Extract rates from competitors (simplified - could be more sophisticated)
        comp_rates = [float(c['Rate'].replace('$','').replace(',','')) for c in st.session_state.all_competitors
            if c.get('Rate') and c['Rate'] != 'Call for Rate' and '$' in str(c['Rate'])]
        if comp_rates:
            default_rate = sum(comp_rates) / len(comp_rates) / 100 * 12 # Convert monthly to annual $/SF
    starting_rate = st.number_input("Starting Rate ($/SF/yr)", value=default_rate, step=0.5,
        help="Annual rental rate per square foot")
    st.markdown("---")
    st.markdown("### 💰 Financial Assumptions")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        land_cost = st.number_input("Land Cost ($)", value=2500000, step=100000)
        construction_psf = st.number_input("Construction ($/SF)", value=65, step=5)
    with col2:
        stabilized_occ = st.slider("Stabilized Occ %", 80, 95, 90)
        months_to_stab = st.number_input("Months to Stabilization", value=24, step=6,
            help="How long to reach stabilized occupancy")
    with col3:
        rate_growth = st.slider("Annual Rate Growth %", 2.0, 6.0, 4.0, 0.5) / 100
        ltv = st.slider("LTV %", 50, 80, 70) / 100
    with col4:
        interest_rate = st.slider("Interest Rate %", 4.0, 8.0, 6.25, 0.25) / 100
        loan_term = st.number_input("Loan Term (yrs)", value=30, step=5)
    total_cost = land_cost + (construction_psf * total_sf)
    loan_amount = total_cost * ltv
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Development Cost", f"${total_cost:,.0f}")
    col2.metric("Loan Amount", f"${loan_amount:,.0f}")
    col3.metric("Equity Required", f"${total_cost - loan_amount:,.0f}")
    st.markdown("---")
    if st.button("🚀 GENERATE 7-YEAR PROJECTION", type="primary"):
        with st.spinner("Building 84-month lease-up model with enhanced attrition curves..."):
            try:
                # Initialize enhanced model
                model = EnhancedLeaseUpModel()
                # Property characteristics
                property_characteristics = {
                    'multi_story': True,
                    'climate_controlled_pct': 1.0,
                    'golf_cart': False,
                    'apartment': False
                }
                # Generate projection
                projection_df = model.generate_projection(
                    total_sf=total_sf,
                    total_units=total_units,
                    start_date=start_date,
                    starting_rate_psf_annual=starting_rate,
                    stabilized_occupancy=stabilized_occ / 100,
                    months_to_stabilization=months_to_stab,
                    new_tenant_rate_growth=rate_growth,
                    existing_tenant_rate_increase=0.12, # 12% for existing tenants
                    land_cost=land_cost,
                    construction_cost_psf=construction_psf,
                    loan_amount=loan_amount,
                    interest_rate=interest_rate,
                    loan_term_years=loan_term,
                    property_characteristics=property_characteristics
                )
                # Calculate equity and purchase price
                purchase_price = land_cost + (construction_psf * total_sf)
                equity_contribution = purchase_price - loan_amount
                # Generate annual summary
                annual_summary = model.generate_annual_summary(
                    projection_df,
                    purchase_price,
                    equity_contribution
                )
                # Store in session state
                st.session_state.financial_inputs = {
                    "projection_monthly": projection_df,
                    "projection_annual": annual_summary
                }
                st.success("✅ 7-Year projection generated with enhanced detail!")
                # Property info for display
                property_info = {
                    'name': property_name or 'Self Storage Development',
                    'address': address_input,
                    'total_sf': total_sf,
                    'total_units': total_units
                }
                # Render modern 7-year projection display
                render_7year_projection(
                    annual_summary=annual_summary,
                    monthly_projection=projection_df,
                    property_info=property_info
                )
            except Exception as e:
                st.error(f"Error generating projection: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

# === PAGE 4: INTELLIGENT FEASIBILITY REPORT ===
elif page == "📋 Feasibility Report":
    st.header("🤖 Intelligent Feasibility Report Generator")
    st.caption("Professional 20+ page reports powered by Claude AI + Data Analytics")

    # Show analytics engine status
    st.markdown("---")
    st.markdown("### 🔧 Analytics Engine Status")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Benchmarks", "✅ Ready", delta="50 states")
    with col2:
        st.metric("Scoring System", "✅ Ready", delta="100 points")
    with col3:
        st.metric("Financial Model", "✅ Ready", delta="Pro Forma")
    with col4:
        st.metric("LLM Integration", "⏳ Pending", delta="Need API Key")

    # Report Configuration
    st.markdown("---")
    st.markdown("### 📋 Report Configuration")

    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("Project Name",
            value=st.session_state.property_data.get('name', ''),
            placeholder="e.g., Nashville Storage Center")
        site_address = st.text_input("Site Address",
            value=st.session_state.property_data.get('address', ''),
            placeholder="123 Main St, Nashville, TN 37211")

    with col2:
        proposed_nrsf = st.number_input("Proposed NRSF", value=60000, step=5000,
            help="Net Rentable Square Feet")
        land_cost = st.number_input("Land Cost ($)", value=800000, step=50000)

    # Advanced Options
    with st.expander("⚙️ Advanced Configuration", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Site Attributes**")
            visibility = st.slider("Visibility (1-5)", 1, 5, 4)
            traffic_count = st.number_input("Daily Traffic", value=18500, step=1000)
        with col2:
            st.markdown("**Financial Assumptions**")
            loan_to_cost = st.slider("Loan-to-Cost %", 50, 80, 75) / 100
            interest_rate = st.slider("Interest Rate %", 4.0, 8.0, 6.5, 0.25) / 100
        with col3:
            st.markdown("**Lot Details**")
            lot_acres = st.number_input("Lot Size (acres)", value=5.2, step=0.1)
            access_quality = st.slider("Access Quality (1-5)", 1, 5, 5)

    st.markdown("---")

    # Preview of Analytics Pipeline
    st.markdown("### 🔄 Analytics Pipeline Preview")
    st.caption("This shows what happens when you generate a report")

    pipeline_steps = [
        ("1️⃣ Geocode Address", "Convert address to coordinates", True),
        ("2️⃣ Fetch Demographics", "Census API - Population, income, growth", True),
        ("3️⃣ Load Market Intel", "TractiQ cache + Google Maps scraper", True),
        ("4️⃣ Calculate Supply/Demand", "SF per capita, market saturation", True),
        ("5️⃣ Build Financial Model", "IRR, NPV, Cap Rate, DSCR, Break-even", True),
        ("6️⃣ Calculate Site Score", "100-point scoring (5 categories)", True),
        ("7️⃣ Generate AI Narrative", "Claude API - Executive Summary, Market Analysis, etc.", False)
    ]

    for step, desc, ready in pipeline_steps:
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            st.markdown(f"**{step}**")
        with col2:
            st.caption(desc)
        with col3:
            if ready:
                st.success("✅ Ready")
            else:
                st.warning("⏳ API Key")

    st.markdown("---")

    # Report Sections Preview
    st.markdown("### 📄 Report Sections (6 AI-Generated Narratives)")

    sections = [
        ("Executive Summary", "2-3 paragraphs with overall assessment, key findings, and recommendation"),
        ("Site Scoring System", "Detailed breakdown of 100-point score across all 5 categories"),
        ("Market Analysis", "Supply/demand dynamics, demographics, competitive landscape"),
        ("Financial Analysis", "Development costs, revenue projections, key metrics (IRR, NPV, Cap Rate)"),
        ("Risk Assessment", "Market risks, development risks, operational risks, mitigation strategies"),
        ("Conclusion & Recommendation", "GO/NO-GO decision with confidence level and next steps")
    ]

    for i, (section, desc) in enumerate(sections, 1):
        with st.expander(f"{i}. {section}", expanded=False):
            st.markdown(f"**What's included:**")
            st.markdown(f"• {desc}")
            st.markdown(f"• Data-driven insights from analytics engine")
            st.markdown(f"• Professional narrative generated by Claude 3.5 Sonnet")
            st.markdown(f"• Industry-standard formatting matching template")

    st.markdown("---")

    # Sample Output Preview (Nashville Test Data)
    st.markdown("### 📊 Sample Output (Test Data)")
    st.caption("This is the analytics output from our test run")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Site Score", "83/100", delta="Good")
    with col2:
        st.metric("Market Balance", "UNDERSUPPLIED", delta="Opportunity")
    with col3:
        st.metric("Cap Rate", "6.43%", delta="Fair")
    with col4:
        st.metric("10-Year IRR", "3.74%", delta="Below Target")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Dev Cost", "$7.9M")
    with col2:
        st.metric("Stabilized NOI", "$510K")
    with col3:
        st.metric("DSCR", "1.06x", delta="Tight")
    with col4:
        st.metric("Break-even Occ", "91.8%", delta="High Risk")

    # Show detailed scoring breakdown
    with st.expander("📊 Detailed Scoring Breakdown (Test Data)", expanded=False):
        st.markdown("**Demographics: 20/25 points**")
        st.markdown("- Population (3-Mile): 61,297 → 4/5 (good)")
        st.markdown("- Growth Rate: 0.37% → 2/5 (weak)")
        st.markdown("- Median Income: $77,883 → 4/5 (good)")
        st.markdown("- Renter-Occupied: 46.1% → 5/5 (excellent)")
        st.markdown("- Median Age: 38.6 → 5/5 (excellent)")

        st.markdown("**Supply/Demand: 18/25 points**")
        st.markdown("- SF Per Capita: 5.8 → 3/5 (fair)")
        st.markdown("- Avg Occupancy: 88% → 4/5 (good)")
        st.markdown("- Distance to Nearest: 1.2 mi → 3/5 (fair)")

        st.markdown("**Site Attributes: 22/25 points**")
        st.markdown("**Competitive Positioning: 11/15 points**")
        st.markdown("**Economic Market: 7/10 points**")

    st.markdown("---")

    # Generation Controls
    st.markdown("### 🚀 Generate Report")

    col1, col2 = st.columns([3, 1])
    with col1:
        st.warning("⚠️ **Anthropic API Key Required**: Add your API key to `.env` file to enable AI report generation")
        st.code("ANTHROPIC_API_KEY=your_key_here", language="bash")

    with col2:
        api_key_present = os.getenv("ANTHROPIC_API_KEY") is not None
        if api_key_present:
            st.success("✅ API Key Found")
        else:
            st.error("❌ No API Key")

    # Test Analytics Only (No LLM)
    if st.button("🧪 Test Analytics Pipeline (No AI)", type="secondary", use_container_width=True):
        with st.spinner("Running analytics pipeline..."):
            try:
                from src.report_orchestrator import ProjectInputs, generate_report

                # Create project inputs
                inputs = ProjectInputs(
                    project_name=project_name or "Test Project",
                    site_address=site_address or "123 Main St, Nashville, TN 37211",
                    proposed_nrsf=proposed_nrsf,
                    land_cost=land_cost,
                    visibility_rating=visibility,
                    traffic_count=traffic_count,
                    access_quality=access_quality,
                    lot_size_acres=lot_acres,
                    zoning_status=1,  # Approved
                    loan_to_cost=loan_to_cost,
                    interest_rate=interest_rate,
                    tractiq_market_id="tn_372113104" if "Nashville" in site_address or "37211" in site_address else None
                )

                # Generate report (analytics only, no LLM)
                report = generate_report(inputs, use_llm=False)

                # Display results
                st.success("✅ Analytics Pipeline Complete!")

                st.markdown("#### Final Results")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Site Score",
                        f"{report.analytics_results.site_scorecard.total_score}/100",
                        delta=report.analytics_results.site_scorecard.tier)
                with col2:
                    st.metric("Recommendation",
                        report.analytics_results.site_scorecard.recommendation)
                with col3:
                    st.metric("Cap Rate",
                        f"{report.analytics_results.pro_forma.metrics.cap_rate*100:.2f}%")
                with col4:
                    st.metric("10-Year IRR",
                        f"{report.analytics_results.pro_forma.metrics.irr_10yr:.2f}%")

                st.info("💡 **Next Step**: Add Anthropic API key to generate full narrative report with Claude AI")

            except Exception as e:
                st.error(f"Analytics test failed: {e}")
                import traceback
                st.code(traceback.format_exc())

    # Full Report Generation (With LLM)
    if st.button("📄 Generate Full AI Report", type="primary", use_container_width=True, disabled=not api_key_present):
        if not api_key_present:
            st.error("Cannot generate AI report without Anthropic API key")
        else:
            with st.spinner("Generating complete feasibility report with AI..."):
                st.info("This will take 30-60 seconds to generate all 6 report sections")
                try:
                    from src.report_orchestrator import ProjectInputs, generate_report

                    inputs = ProjectInputs(
                        project_name=project_name or "Test Project",
                        site_address=site_address or "123 Main St, Nashville, TN 37211",
                        proposed_nrsf=proposed_nrsf,
                        land_cost=land_cost,
                        visibility_rating=visibility,
                        traffic_count=traffic_count,
                        access_quality=access_quality,
                        lot_size_acres=lot_acres,
                        zoning_status=1,
                        loan_to_cost=loan_to_cost,
                        interest_rate=interest_rate
                    )

                    # Generate full report with LLM
                    report = generate_report(inputs, use_llm=True)

                    st.success("🎉 Complete Report Generated!")

                    # Display report sections
                    st.markdown("---")
                    st.markdown("## 📄 Generated Report")

                    for section_name, content in report.report_sections.items():
                        with st.expander(f"📋 {section_name.replace('_', ' ').title()}", expanded=False):
                            st.markdown(content)

                    # Offer download (would need PDF conversion)
                    st.download_button(
                        label="📥 Download Report (JSON)",
                        data=str(report.report_sections),
                        file_name=f"Feasibility_Report_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain",
                        type="primary"
                    )

                except Exception as e:
                    st.error(f"Report generation failed: {e}")
                    import traceback
                    st.code(traceback.format_exc())

    st.markdown("---")
    st.caption("💰 **Cost Estimate**: ~$0.75-$1.50 per report (Claude API usage)")
    st.caption("⏱️ **Generation Time**: 30-60 seconds per complete report")