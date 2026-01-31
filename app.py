import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime
import re

# VERSION MARKER - Force Streamlit Cloud to update
APP_VERSION = "2.4.0-PRODUCTION"

# CRITICAL: Use st.write() early to verify code is deployed
# Debug mode disabled for production
# st.set_page_config is called further down with icon and title

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

# Import UI components
try:
    from src.ui.command_center import render_command_center
except ImportError as e:
    print(f"Command Center UI unavailable: {e}")
    render_command_center = None
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
st.set_page_config(page_title="StorSageHQ", page_icon="assets/logo_transparent.png", layout="wide")

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
    /* --- 1. GLOBAL RESET & TYPOGRAPHY --- */
    .stApp {
        background-color: #F4F6F8 !important; /* Light Gray Background */
        color: #0C2340 !important;
        font-family: 'Inter', sans-serif !important;
        padding-top: 80px !important; /* Offset for Fixed SaaS Header */
    }
    
    /* --- 2. FIXED SAAS HEADER --- */
    /* Target the container that wraps the navigation radio group */
    div[data-testid="stVerticalBlock"] > div.element-container:has(div[role="radiogroup"]) {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important; /* Full Screen Width */
        height: 70px !important;
        background-color: #0C2340 !important; /* StorSageHQ Navy */
        z-index: 999999 !important; /* Above Deploy Bar */
        display: flex !important;
        align-items: center !important;
        justify-content: center !important; /* Center the tabs */
        border-bottom: 1px solid rgba(255,255,255,0.1) !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* Radio Group - Strict Single Row Flex */
    div[role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: center !important;
        flex-wrap: nowrap !important; /* CRITICAL: No wrapping */
        gap: 0 !important;
        background-color: transparent !important;
        border: none !important;
        width: auto !important;
    }
    
    /* Hide ugly radio circles */
    div[role="radiogroup"] input[type="radio"] {
        display: none !important;
    }
    div[role="radiogroup"] label > div:first-child {
        display: none !important;
    }
    
    /* Nav Tabs Styling */
    div[role="radiogroup"] label {
        flex: 0 1 auto !important; /* Do not stretch */
        white-space: nowrap !important; /* CRITICAL: Prevent wrapping */
        margin: 0 15px !important; /* Spacing between tabs */
        padding: 10px 20px !important;
        background-color: transparent !important;
        border: none !important;
        border-radius: 4px !important;
        transition: all 0.2s ease !important;
        cursor: pointer !important;
    }
    
    /* Tab Text */
    div[role="radiogroup"] p {
        color: #FFFFFF !important;
        font-weight: 500 !important;
        font-size: 15px !important;
        margin: 0 !important;
    }
    
    /* Active State Highlight */
    div[role="radiogroup"] label:has(div[data-checked="true"]) {
        background-color: #1A3A5E !important; /* Lighter Navy */
        border-bottom: 2px solid #4A90E2 !important; /* Accent Blue */
    }
    
    /* Hover State */
    div[role="radiogroup"] label:hover {
        background-color: rgba(255,255,255,0.05) !important;
    }

    /* --- 3. SIDEBAR STYLING --- */
    [data-testid="stSidebar"] {
        background-color: #0C2340 !important;
    }
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    /* Logo Transparency Hack */
    [data-testid="stSidebar"] img {
        mix-blend-mode: multiply !important;
    }

    /* --- 4. HERO SECTION (Juniper Square) --- */
    .hero-card {
        background-color: #FFFFFF !important;
        border-radius: 12px !important;
        padding: 2.5rem !important;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04) !important;
        border: 1px solid #E2E8F0 !important;
        margin-bottom: 2rem !important;
    }
    .hero-metric-label {
        color: #64748B !important;
        font-size: 0.85rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        font-weight: 600 !important;
    }
    .hero-metric-value {
        color: #0C2340 !important;
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        font-family: 'Georgia', serif !important;
    }

    /* --- 5. DATA TABLES (Stripe) --- */
    [data-testid="stDataFrame"] {
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
        background-color: #FFFFFF !important;
    }
    [data-testid="stDataFrame"] div[role="columnheader"] {
        background-color: #F8FAFC !important;
        color: #0C2340 !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        font-size: 0.75rem !important;
        border-bottom: 1px solid #E2E8F0 !important;
    }
    [data-testid="stDataFrame"] div[role="row"] {
        background-color: #FFFFFF !important;
        border-bottom: 1px solid #F1F5F9 !important;
        color: #334155 !important;
    }

    /* --- 6. INPUT CARDS (TryCactus) --- */
    /* Only apply card styling to columns that contain inputs or metrics */
    div[data-testid="stColumn"]:has(div[data-testid="stTextInput"], div[data-testid="stNumberInput"], div[data-testid="stTextArea"], div[data-testid="metric-container"], .hero-card) {
        background-color: #FFFFFF !important;
        border-radius: 16px !important;
        padding: 2rem !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05) !important;
        border: none !important;
        margin-bottom: 1rem !important;
    }

    div[data-testid="stTextInput"] input, 
    div[data-testid="stNumberInput"] input, 
    div[data-testid="stTextArea"] textarea {
        background-color: #FFFFFF !important;
        color: #0C2340 !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
        padding: 10px !important;
    }
    div[data-testid="stTextInput"] label, 
    div[data-testid="stNumberInput"] label {
         color: #0C2340 !important;
         font-weight: 600 !important;
    }

    /* --- 7. BUTTONS (Standard Brands) --- */
    .stButton > button {
        background-color: #0C2340 !important;
        color: #FFFFFF !important; /* Force White Text */
        border: 1px solid rgba(255,255,255,0.2) !important;
        border-radius: 6px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        width: 100% !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background-color: #1E293B !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
        transform: translateY(-1px) !important;
    }
    /* Rocket Button Label Specificity Fix */
    .stButton > button p {
        color: #FFFFFF !important;
    }

    /* --- 8. MISC UI --- */
    [data-testid="stFileUploader"] {
        background-color: #FFFFFF !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }
    .streamlit-expanderHeader {
        background-color: #FFFFFF !important;
        color: #0C2340 !important;
    }
</style>
""", unsafe_allow_html=True)

# Display the logo and title in a horizontal lockup

# Top Navigation Layout
page = st.radio(
    "Navigation",
    ["📝 Project Inputs", "📊 Market Intel", "💰 7-Year Operating Model", "🤖 AI Feasibility Report", "🎯 Command Center"],
    index=0,
    horizontal=True,
    label_visibility="collapsed"
)

# Sidebar - Cleaned up (Logo + TractIQ only)
with st.sidebar:
    # Sidebar Logo - Enforced Transparency
    st.image("assets/logo_transparent.png", use_container_width=True)
    st.sidebar.markdown("---")
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

# === PAGE 1: PROJECT INPUTS (NEW - SINGLE SOURCE OF TRUTH) ===
if page == "📝 Project Inputs":
    st.header("📝 Project Inputs")
    st.caption("Single source of truth for all project data - all analysis flows from here")

    # Initialize session state for analysis results
    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = None
    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False
    if "use_ai_size" not in st.session_state:
        st.session_state.use_ai_size = True
    if "use_default_financials" not in st.session_state:
        st.session_state.use_default_financials = True

    st.markdown("---")

    # REQUIRED INPUTS
    st.markdown("### 🎯 Required Information")

    # Use session state keys to persist text input values across reruns
    if "input_address" not in st.session_state:
        st.session_state.input_address = st.session_state.property_data.get('address', '')
    if "input_name" not in st.session_state:
        st.session_state.input_name = st.session_state.property_data.get('name', '')

    # Soft Card Wrapper for Inputs
    input_col, = st.columns(1)
    with input_col:
        project_address = st.text_input(
            "Site Address*",
            key="input_address",
            placeholder="Enter the property address (e.g., 123 Main St, Nashville, TN 37211)",
            help="This is the only required field to start analysis"
        )

        project_name = st.text_input(
            "Project Name (Optional)",
            key="input_name",
            placeholder="e.g., Nashville Storage Center",
            help="Optional - will use address if left blank"
        )

    st.markdown("---")

    # NRSF TOGGLE
    st.markdown("### 📐 Project Size")
    use_ai_size = st.toggle(
        "Use AI Recommended Size",
        value=st.session_state.use_ai_size,
        help="Let the system recommend optimal size based on market analysis, or input your own"
    )
    st.session_state.use_ai_size = use_ai_size

    if not use_ai_size:
        custom_nrsf = st.number_input(
            "Net Rentable Square Feet (NRSF)",
            min_value=10000,
            max_value=200000,
            value=60000,
            step=5000,
            help="Your proposed facility size"
        )
        custom_units = st.number_input(
            "Number of Units",
            min_value=50,
            max_value=2000,
            value=400,
            step=10,
            help="Total number of storage units"
        )
    else:
        st.info("✨ Project size will be recommended by AI based on market analysis")
        custom_nrsf = None
        custom_units = None

    st.markdown("---")

    # FINANCIAL ASSUMPTIONS TOGGLE
    st.markdown("### 💰 Financial Assumptions")
    use_default_financials = st.toggle(
        "Use Default Financial Assumptions",
        value=st.session_state.use_default_financials,
        help="Use industry-standard assumptions, or input your own financing terms"
    )
    st.session_state.use_default_financials = use_default_financials

    if not use_default_financials:
        col1, col2 = st.columns(2)
        with col1:
            # Land Cost Input (Comma-Inside-Box)
            land_cost_input = st.text_input(
                "Land Cost ($)",
                value="750,000",
                help="Purchase price of the land. Use commas."
            )
            # Backend Logic: Strip commas for calculation
            try:
                land_cost = float(land_cost_input.replace(",", "").replace("$", ""))
            except ValueError:
                land_cost = 0.0
            loan_to_cost = st.slider(
                "Loan-to-Cost Ratio (%)",
                min_value=50,
                max_value=90,
                value=75,
                step=5,
                help="Percentage of total development cost financed by debt"
            ) / 100
        with col2:
            interest_rate = st.slider(
                "Interest Rate (%)",
                min_value=3.0,
                max_value=12.0,
                value=6.5,
                step=0.25,
                help="Annual interest rate on construction/permanent loan"
            ) / 100
            loan_term_years = st.number_input(
                "Loan Term (Years)",
                min_value=5,
                max_value=30,
                value=20,
                step=1,
                help="Amortization period for the loan"
            )
    else:
        st.info("✨ Using industry-standard defaults:\n- Loan-to-Cost: 75%\n- Interest Rate: 6.5%\n- Loan Term: 20 years\n- Land cost will be estimated based on market")
        land_cost = None
        loan_to_cost = 0.75
        interest_rate = 0.065
        loan_term_years = 20

    st.markdown("---")

    # TractiQ Data Upload
    st.markdown("### 📁 TractiQ Market Data (Optional)")

    # Check if we have cached data for this address
    from src.tractiq_cache import get_cached_tractiq_data, get_market_stats

    cached_data = None
    cached_stats = None
    if project_address:
        cached_data = get_cached_tractiq_data(project_address)
        if cached_data:
            cached_stats = get_market_stats(project_address)

    # Show cached data status
    if cached_data and cached_stats:
        st.success(f"✅ Found cached TractiQ data for this address!")
        col1, col2, col3 = st.columns(3)
        col1.metric("Cached Competitors", cached_stats.get('total_competitors', 0))
        col2.metric("Data Sources", cached_stats.get('data_sources', 0))
        col3.metric("Last Updated", cached_stats.get('last_updated', 'Unknown')[:10] if cached_stats.get('last_updated') else 'Unknown')

        # Auto-set the tractiq_market_id from cached data
        if "tractiq_market_id" not in st.session_state or not st.session_state.tractiq_market_id:
            # Use the normalized market_id from the cache
            # The cache generates this by normalizing the address
            from src.tractiq_cache import TractIQCache
            cache = TractIQCache()
            market_id = cache._generate_market_id(project_address)
            st.session_state.tractiq_market_id = market_id

        st.info("You can upload additional TractiQ files below to add to the cached data, or proceed with analysis using existing data.")
    else:
        st.info("Upload TractiQ competitor reports (PDF, CSV, Excel) to enhance market analysis with detailed rate data by unit size and climate control.")

    uploaded_files = st.file_uploader(
        "Drop TractiQ Reports Here",
        type=['pdf', 'csv', 'xlsx', 'xls'],
        accept_multiple_files=True,
        help="Upload TractiQ market reports for this address. Data will be cached to build your market database.",
        key="tractiq_uploader"
    )

    # Initialize tractiq_market_id in session state
    if "tractiq_market_id" not in st.session_state:
        st.session_state.tractiq_market_id = None

    tractiq_market_id = st.session_state.tractiq_market_id

    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} file(s) uploaded")
        with st.expander("📄 View Uploaded Files"):
            for file in uploaded_files:
                st.write(f"- {file.name} ({file.size:,} bytes)")

        # Check if we need to process files (only process if not already processed)
        file_names = [f.name for f in uploaded_files]
        if "processed_tractiq_files" not in st.session_state or st.session_state.get("processed_tractiq_files") != file_names:
            # Process and cache the files
            try:
                from src.tractiq_processor import process_tractiq_files
                from src.tractiq_cache import cache_tractiq_data

                # Process uploaded files to extract data
                with st.spinner("Processing TractiQ data..."):
                    tractiq_data = process_tractiq_files(uploaded_files)

                    # Cache the data associated with this address
                    if tractiq_data:
                        # Use address as market identifier - cache will normalize it
                        market_id = cache_tractiq_data(project_address, tractiq_data)

                        # Store in session state
                        st.session_state.tractiq_market_id = market_id
                        st.session_state.processed_tractiq_files = file_names
                        tractiq_market_id = market_id

                        st.success(f"✅ TractiQ data processed and cached for this market")
                        st.rerun()
            except Exception as e:
                st.warning(f"⚠️ Could not process TractiQ files: {str(e)}")
                st.info("Analysis will proceed with scraped competitor data only")
        else:
            st.info(f"✅ TractiQ data ready (Market ID: {st.session_state.tractiq_market_id})")

    st.markdown("---")

    # BIG ANALYZE BUTTON
    st.markdown("### 🚀 Ready to Analyze?")

    analyze_disabled = not project_address
    if analyze_disabled:
        st.warning("⚠️ Please enter a site address to begin analysis")

    if st.button(
        "🚀 Analyze Market",
        disabled=analyze_disabled,
        help="Run complete market analysis and generate feasibility report",
        use_container_width=True
    ):
        with st.spinner("🔍 Running comprehensive market analysis..."):
            try:
                # Import analytics modules
                from src.report_orchestrator import ProjectInputs, run_analytics

                # Build inputs object
                inputs = ProjectInputs(
                    project_name=project_name if project_name else project_address,
                    site_address=project_address,
                    proposed_nrsf=custom_nrsf if custom_nrsf else 60000,  # Default if AI size
                    land_cost=land_cost if land_cost else 0,
                    loan_to_cost=loan_to_cost,
                    interest_rate=interest_rate,
                    tractiq_market_id=st.session_state.get("tractiq_market_id"),  # Pass TractiQ data if uploaded
                    # Will add more parameters as needed
                )

                # Run 7-step analytics pipeline
                st.info("Running 7-step analytics pipeline...")
                analytics_results = run_analytics(inputs)

                # Store results in session state
                st.session_state.analysis_results = analytics_results
                st.session_state.analysis_complete = True
                st.session_state.property_data = {
                    "name": project_name if project_name else project_address,
                    "address": project_address,
                    "lat": analytics_results.latitude if hasattr(analytics_results, 'latitude') else None,
                    "lon": analytics_results.longitude if hasattr(analytics_results, 'longitude') else None
                }

                st.success("✅ Analysis complete! Navigate to Market Intel to view results.")
                st.balloons()

            except Exception as e:
                st.error(f"❌ Analysis failed: {str(e)}")
                import traceback
                with st.expander("🔍 Error Details"):
                    st.code(traceback.format_exc())

    # Show current analysis status
    if st.session_state.analysis_complete:
        st.markdown("---")
        st.markdown("### ✅ Analysis Status")
        results = st.session_state.analysis_results
        if results:
            col1, col2, col3, col4 = st.columns(4)

            # Safely extract metrics
            site_score = "N/A"
            if hasattr(results, 'site_scorecard') and results.site_scorecard:
                site_score = f"{results.site_scorecard.total_score}/100"

            market_balance = "N/A"
            if hasattr(results, 'market_supply_demand') and results.market_supply_demand:
                market_balance = results.market_supply_demand.balance_tier_3mi

            cap_rate = "N/A"
            if hasattr(results, 'pro_forma') and results.pro_forma and hasattr(results.pro_forma, 'metrics'):
                cap_rate = f"{results.pro_forma.metrics.cap_rate*100:.2f}%"

            irr = "N/A"
            if hasattr(results, 'pro_forma') and results.pro_forma and hasattr(results.pro_forma, 'metrics'):
                irr = f"{results.pro_forma.metrics.irr_10yr:.1f}%"

            col1.metric("Site Score", site_score)
            col2.metric("Market Balance", market_balance.title())
            col3.metric("Cap Rate", cap_rate)
            col4.metric("IRR (10yr)", irr)
            st.success("✅ Data ready - navigate to other pages to view detailed analysis")

# === PAGE 2: COMMAND CENTER ===
elif page == "🎯 Command Center":
    if render_command_center is not None:
        render_command_center()
    else:
        st.error("Command Center UI module is unavailable")

# === PAGE 2: MARKET INTEL (READ-ONLY - AI DRIVEN) ===
elif page == "📊 Market Intel":
    st.header("📊 Market Intelligence & Feasibility")
    st.caption("AI-driven market analysis - all data calculated automatically")

    # Check if analysis has been run
    if not st.session_state.get("analysis_complete"):
        st.warning("⚠️ No analysis results available. Please go to Project Inputs page and run analysis first.")
        st.info("👈 Navigate to **📝 Project Inputs** to enter your site address and start analysis")
        st.stop()

    results = st.session_state.analysis_results
    if not results:
        st.error("Analysis results not found in session state")
        st.stop()

    # Display project information
    st.markdown("### 📍 Project Information")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Project Name:** {st.session_state.property_data.get('name', 'N/A')}")
        st.markdown(f"**Address:** {st.session_state.property_data.get('address', 'N/A')}")
    with col2:
        if hasattr(results, 'latitude') and hasattr(results, 'longitude'):
            st.markdown(f"**Latitude:** {results.latitude:.6f}")
            st.markdown(f"**Longitude:** {results.longitude:.6f}")

    st.markdown("---")

    # Display 100-point site score
    if hasattr(results, 'site_scorecard') and results.site_scorecard:
        scorecard = results.site_scorecard

        # Centered Hero Card for Score
        col_side, col_center, col_side2 = st.columns([1, 3, 1])
        with col_center:
            # Prepare data for the new Glassmorphism component
            score_data = {
                'score': scorecard.total_score,
                'decision': scorecard.recommendation,
                'confidence': scorecard.confidence,
                'breakdown': {
                    'Demographics': {'score': scorecard.demographics.total_score, 'max': scorecard.demographics.max_score},
                    'Supply/Demand': {'score': scorecard.supply_demand.total_score, 'max': scorecard.supply_demand.max_score},
                    'Site Attributes': {'score': scorecard.site_attributes.total_score, 'max': scorecard.site_attributes.max_score},
                    'Competitive': {'score': scorecard.competitive_positioning.total_score, 'max': scorecard.competitive_positioning.max_score},
                    'Economic': {'score': scorecard.economic_market.total_score, 'max': scorecard.economic_market.max_score}
                },
                'key_strengths': [], # Will populating this requires simple logic, leaving empty for now to match exact scope of visual refactor
                'key_risks': []
            }
            
            # Use the new component
            render_feasibility_score(score_data)

        st.markdown("---")

        # Category breakdown
        st.markdown("### 📊 Score Breakdown")

        try:
            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.metric("Demographics", f"{scorecard.demographics.total_score}/25")
            with col2:
                st.metric("Supply/Demand", f"{scorecard.supply_demand.total_score}/25")
            with col3:
                st.metric("Site Attributes", f"{scorecard.site_attributes.total_score}/25")
            with col4:
                st.metric("Competitive", f"{scorecard.competitive_positioning.total_score}/15")
            with col5:
                st.metric("Economic", f"{scorecard.economic_market.total_score}/10")
        except AttributeError as e:
            st.error(f"⚠️ Score breakdown display error: {str(e)}")
            st.info("Some score category data may be missing. The analysis may need to be re-run.")
            import traceback
            with st.expander("🔍 Full Error Details"):
                st.code(traceback.format_exc())

        # Detailed breakdown in expanders
        try:
            with st.expander("👥 Demographics Details"):
                demo = scorecard.demographics
                st.write(f"**Population (3mi):** {demo.population_3mi:,} - Score: {demo.population_3mi_score}/5 ({demo.population_3mi_tier})")
                st.write(f"**Growth Rate:** {demo.growth_rate:.2f}% - Score: {demo.growth_rate_score}/5 ({demo.growth_rate_tier})")
                st.write(f"**Median Income:** ${demo.median_income:,} - Score: {demo.median_income_score}/5 ({demo.median_income_tier})")
                st.write(f"**Renter %:** {demo.renter_occupied_pct:.1f}% - Score: {demo.renter_occupied_pct_score}/5 ({demo.renter_occupied_pct_tier})")
                st.write(f"**Median Age:** {demo.median_age:.1f} - Score: {demo.median_age_score}/5 ({demo.median_age_tier})")

            with st.expander("📦 Supply/Demand Details"):
                supply = scorecard.supply_demand
                st.write(f"**SF per Capita (3mi):** {supply.sf_per_capita:.2f} - Score: {supply.sf_per_capita_score}/5 ({supply.sf_per_capita_tier})")
                st.write(f"**Avg Occupancy:** {supply.existing_occupancy_avg:.1f}% - Score: {supply.existing_occupancy_avg_score}/5 ({supply.existing_occupancy_avg_tier})")
                st.write(f"**Distance to Nearest:** {supply.distance_to_nearest:.2f} mi - Score: {supply.distance_to_nearest_score}/5 ({supply.distance_to_nearest_tier})")
                st.write(f"**Rate Trend (12mo):** {supply.market_rate_trend:+.1f}% - Score: {supply.market_rate_trend_score}/5 ({supply.market_rate_trend_tier})")
                st.write(f"**Dev Pipeline:** {supply.development_pipeline} facilities - Score: {supply.development_pipeline_score}/5 ({supply.development_pipeline_tier})")
        except AttributeError:
            pass
    else:
        st.warning("⚠️ Site scorecard data not available")

    st.markdown("---")

    # Market supply/demand analysis
    st.markdown("### 📈 Market Supply & Demand")
    if hasattr(results, 'market_supply_demand'):
        market = results.market_supply_demand

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("SF per Capita", f"{market.sf_per_capita_3mi:.2f}",
                   delta="Undersupplied" if market.sf_per_capita_3mi < 5.5 else "Balanced" if market.sf_per_capita_3mi < 7.0 else "Oversupplied")
        col2.metric("Market Balance", market.balance_tier_3mi.title())
        col3.metric("Saturation Score", f"{market.saturation_score}/100",
                   delta="Lower is better")
        col4.metric("Supply Gap", f"{market.supply_gap_sf:,} SF" if market.supply_gap_sf < 0 else f"+{market.supply_gap_sf:,} SF",
                   delta="Undersupplied" if market.supply_gap_sf < 0 else "Oversupplied")

        if market.balance_tier_3mi == "UNDERSUPPLIED":
            st.success("✅ **Good Opportunity:** Market is Undersupplied - favorable for new development")
        elif market.balance_tier_3mi == "BALANCED":
            st.info("ℹ️ **Moderate Opportunity:** Market is balanced - carefully evaluate competitive positioning")
        else:
            st.warning("⚠️ **Challenging Market:** Oversupplied - may face headwinds")

    st.markdown("---")

    # MARKET RATES BY UNIT SIZE (MERGED DATA)
    st.markdown("### 💰 Market Rates by Unit Size")
    st.caption("Competitive rate analysis from TractiQ uploads + scraped competitor data")

    try:
        from src.rate_merger import merge_competitor_rates
        from src.tractiq_cache import get_cached_tractiq_data

        # Get TractiQ data from cache if available
        tractiq_data = {}
        if st.session_state.get("tractiq_market_id"):
            project_address = st.session_state.property_data.get('address', '')
            if project_address:
                tractiq_data = get_cached_tractiq_data(project_address)

        # Get scraper competitors
        scraper_competitors = results.scraper_competitors if hasattr(results, 'scraper_competitors') else []

        # Debug: Show raw data structure
        with st.expander("🔍 Debug: Data Sources"):
            st.write(f"**TractiQ data keys:** {list(tractiq_data.keys()) if tractiq_data else 'None'}")
            if tractiq_data:
                for key, val in tractiq_data.items():
                    st.write(f"**{key}:**")
                    comps = val.get('competitors', [])
                    st.write(f"  - Competitors count: {len(comps)}")
                    if comps:
                        st.write(f"  - First competitor keys: {list(comps[0].keys())}")
                        st.write(f"  - First competitor sample: {comps[0]}")
            st.write(f"**Scraper competitors count:** {len(scraper_competitors)}")
            if scraper_competitors:
                st.write(f"**First scraper competitor:** {scraper_competitors[0]}")

        # Merge the data
        merged_rates = merge_competitor_rates(tractiq_data, scraper_competitors)

        # Display summary
        summary = merged_rates['summary']
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Competitors", summary['total_competitors'])
        col2.metric("TractiQ Sources", summary['tractiq_count'])
        col3.metric("Scraped Sources", summary['scraper_count'])

        # Build rate table
        by_unit_size = merged_rates['by_unit_size']
        table_data = {
            "Unit Size": [],
            "Climate Min-Max": [],
            "Climate Avg": [],
            "Non-Climate Min-Max": [],
            "Non-Climate Avg": [],
            "Sample Size": []
        }

        for size in summary['unit_sizes']:
            climate_data = by_unit_size[size]['climate']
            non_climate_data = by_unit_size[size]['non_climate']

            table_data["Unit Size"].append(size)

            # Climate controlled
            if climate_data['count'] > 0:
                table_data["Climate Min-Max"].append(f"${climate_data['min']:.0f}-${climate_data['max']:.0f}")
                table_data["Climate Avg"].append(f"${climate_data['avg']:.0f}")
            else:
                table_data["Climate Min-Max"].append("No data")
                table_data["Climate Avg"].append("-")

            # Non-climate
            if non_climate_data['count'] > 0:
                table_data["Non-Climate Min-Max"].append(f"${non_climate_data['min']:.0f}-${non_climate_data['max']:.0f}")
                table_data["Non-Climate Avg"].append(f"${non_climate_data['avg']:.0f}")
            else:
                table_data["Non-Climate Min-Max"].append("No data")
                table_data["Non-Climate Avg"].append("-")

            # Sample size
            total_samples = climate_data['count'] + non_climate_data['count']
            table_data["Sample Size"].append(f"{total_samples} rates")

        # Display table
        st.table(pd.DataFrame(table_data))

        # Overall rate range
        if summary['rate_range']['min'] and summary['rate_range']['max']:
            st.caption(f"📊 **Overall Rate Range:** ${summary['rate_range']['min']:.0f} - ${summary['rate_range']['max']:.0f} | **Sources:** {summary['tractiq_count']} TractiQ + {summary['scraper_count']} Scraped")
        else:
            st.caption("📊 **Source:** TractiQ cache + Google Maps scraper data")

    except Exception as e:
        st.warning(f"⚠️ Could not merge rate data: {str(e)}")
        st.info("Showing placeholder rate data")

        # Fallback placeholder
        rate_data = {
            "Unit Size": ["5x5", "5x10", "10x10", "10x15", "10x20", "10x30"],
            "Climate Min-Max": ["$75-95", "$95-125", "$120-160", "$150-200", "$180-240", "$250-350"],
            "Non-Climate Min-Max": ["$55-75", "$70-95", "$90-120", "$115-155", "$140-190", "$190-280"],
        }
        st.table(pd.DataFrame(rate_data))

    st.markdown("---")

    # Key Findings
    st.markdown("### 🔍 Key Findings")
    if hasattr(results, 'site_scorecard'):
        findings = []

        # Demographics finding
        if scorecard.demographics.total_score >= 20:
            findings.append(f"✅ Strong demographics: {scorecard.demographics.population_3mi:,} population with ${scorecard.demographics.median_income:,} median income")
        else:
            findings.append(f"⚠️ Moderate demographics: Consider competitive advantages needed")

        # Supply/demand finding
        if market.sf_per_capita_3mi < 5.5:
            findings.append(f"✅ Undersupplied market: {market.sf_per_capita_3mi:.2f} SF/capita (target: 5-7)")
        elif market.sf_per_capita_3mi > 7.0:
            findings.append(f"⚠️ Oversupplied market: {market.sf_per_capita_3mi:.2f} SF/capita")

        # Score-based finding
        if scorecard.total_score >= 85:
            findings.append("✅ Excellent site overall - high confidence")
        elif scorecard.total_score >= 70:
            findings.append("✅ Good site - proceed with standard due diligence")
        elif scorecard.total_score >= 55:
            findings.append("⚠️ Fair site - additional risk mitigation recommended")
        else:
            findings.append("❌ Weak site - consider alternative locations")

        for finding in findings:
            st.markdown(f"- {finding}")

    st.markdown("---")
    st.info("💡 **Next Steps:** Navigate to '💰 7-Year Operating Model' to see financial projections and profitability timeline")

# === PAGE 3: 7-YEAR OPERATING MODEL (renamed from Underwriting) ===
elif page == "💰 7-Year Operating Model":
    st.header("Financial Underwriting & 7-Year Projection")
    # Pull property data from Market Intel if available
    property_address = st.session_state.property_data.get('address', '')
    # Soft Card for Inputs
    input_card, = st.columns(1)
    with input_card:
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
            # Land Cost Input (Comma-Inside-Box)
            land_cost_input = st.text_input("Land Cost ($)", value="2,500,000")
            try:
                land_cost = float(land_cost_input.replace(",", "").replace("$", ""))
            except ValueError:
                land_cost = 0.0
            
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
                # Label Consistency: Rename index to Year 1, Year 2...
                annual_summary.index = [f"Year {i}" for i in range(1, len(annual_summary) + 1)]
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
                # Chart Container (Soft Card)
                chart_col, = st.columns(1)
                with chart_col:
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
elif page == "🤖 AI Feasibility Report":
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
        # Land Cost Input (Comma-Inside-Box)
        land_cost_input = st.text_input("Land Cost ($)", value="800,000")
        try:
            land_cost = float(land_cost_input.replace(",", "").replace("$", ""))
        except ValueError:
            land_cost = 0.0

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
        st.metric("Market Balance", "Undersupplied", delta="Opportunity")
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