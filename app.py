import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
from config import Config
from main import SecretaryAgent
from src.financials import generate_pro_forma, recommend_unit_mix
from src.crm_adjustor import get_actionable_leads, get_profile_candidates, get_skip_trace_list, run_adjustor_sync
from src.scoring_logic import FeasibilityScorer
from src.intelligence import IntelligenceAgent, geocode_address, generate_pydeck_map
from src.scraper import get_competitors_realtime
from src.pdf_processor import extract_pdf_data
from src.leaseup_model import LeaseUpModel
from src.leaseup_model_v2 import EnhancedLeaseUpModel
from src.projection_display import render_7year_projection, render_feasibility_score
import re
# === TRACTIQ DATA INTEGRATION ===
def load_tractiq_data():
    """
    Scans src/data for TractiQ Export.csv and returns a list of dictionaries.
    Includes fuzzy column mapping for rates.
    """
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
st.set_page_config(page_title="STORAGE OS", page_icon="assets/logo.png", layout="wide")

# === UPDATED BRAND CSS (NEUTRAL COLORS MATCHING LOGO) ===
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    /* APPLY FONT ONLY TO MARKDOWN TEXT TO PROTECT ICONS */
    .stMarkdown, .stMarkdown div, .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
        font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
    }
    /* Shield all internal icons and specific Streamlit cache classes */
    [data-testid="stIcon"], .st-emotion-cache-1ky7m6a, [data-testid="stSidebarCollapseButton"], .st-ae {
        font-family: 'StreamlitIcons' !important;
    }
    .stApp { background-color: #F4F6F8; } /* Neutral light gray background */
    h1, h2, h3, h4, h5, h6 { color: #0C2340 !important; font-weight: 700 !important; } /* Navy for headers */
    [data-testid="stSidebar"] { background-color: #0C2340; } /* Navy sidebar */
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton>button[kind="primary"] { background-color: #4A90E2 !important; color: white !important; font-weight: 600 !important; } /* Soft blue for primary buttons */
    .stButton>button[kind="secondary"] { background-color: transparent !important; border: 2px solid #0C2340 !important; color: #0C2340 !important; }
    /* CRITICAL: FORCE READABLE METRICS */
    [data-testid="stMetricValue"] {
        font-size: 24px !important;
        color: #0C2340 !important;
        font-weight: 600 !important;
    }
    div[data-testid="metric-container"] {
        background-color: white !important;
        border: 1px solid #E0E0E0 !important; /* Neutral gray border */
        padding: 15px !important; /* More padding for breathing room */
        border-radius: 8px !important;
        border-left: 5px solid #4A90E2 !important; /* Soft blue accent */
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #E0E0E0 !important;
        padding: 15px !important;
        border-radius: 8px !important;
        color: #0C2340 !important;
    }
    div[data-testid="stMetric"] label {
        color: #666666 !important; /* Neutral gray labels */
        font-size: 14px !important;
    }
    /* Global text color scoped to main app and markdown to avoid breaking dark-background elements */
    .stApp, .stMarkdown {
        color: #0C2340 !important;
    }
    /* SCORE CARD STYLING */
    .score-card {
        background: linear-gradient(135deg, #0C2340 0%, #1A3A5C 100%); /* Navy gradient */
        color: white !important;
        padding: 25px; /* More padding */
        border-radius: 10px; /* Softer corners */
        text-align: center;
    }
    .score-card h1, .score-card p {
        color: white !important;
    }
    /* FILE UPLOADER VISIBILITY FIX */
    [data-testid="stFileUploader"] {
        background-color: white !important;
        padding: 20px !important; /* More padding */
        border-radius: 10px !important;
        border: 1px dashed #0C2340 !important;
    }
    [data-testid="stFileUploader"] * {
        color: #0C2340 !important;
    }
    /* Add more whitespace globally */
    .block-container {
        padding: 20px !important;
    }
</style>
""", unsafe_allow_html=True)

# Display the logo prominently at the top
# st.image("assets/logo.png", use_column_width=False, width=300)  # Commented out - logo file missing

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

st.title("🏢 STORAGE OS")
st.caption("Production Self-Storage Feasibility Platform")

with st.sidebar:
    st.header("Navigation")
    page = st.radio("Navigation", ["🎯 Command Center", "📊 Market Intel", "💰 Underwriting", "📋 Feasibility Report"], label_visibility="collapsed")
    # TractIQ Cache Management
    st.markdown("---")
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
            actionable = get_actionable_leads(limit=10)
            if not actionable.empty:
                st.dataframe(actionable, hide_index=True)
            else:
                st.info("No actionable leads")
        with tab2:
            st.caption("Status = New/FollowUp")
            candidates = get_profile_candidates(limit=8)
            if not candidates.empty:
                st.dataframe(candidates, hide_index=True)
            else:
                st.info("No profile candidates")
        with tab3:
            st.caption("Missing contact info")
            skip_list = get_skip_trace_list(limit=20)
            if not skip_list.empty:
                st.dataframe(skip_list, hide_index=True)
            else:
                st.info("No skip trace needed")
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
                with st.spinner("🚀 Pre-fetching 20-mile trade area data..."):
                    try:
                        scout_results = get_competitors_realtime(coords_lat, coords_lon, radius_miles=20)
                        # Enrich with TractiQ
                        enriched_results = merge_competitor_data(scout_results)
                        st.session_state.all_competitors = enriched_results
                        st.toast("✅ 20mi Scrape Cached & Enriched")
                    except Exception as e:
                        st.error(f"Pre-fetch failed: {e}")
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
    # File Upload - accepts all file types including Excel
    tractiq_files = st.file_uploader(
        "Drop TractIQ files here (PDF reports, CSV, Excel, or any data format)",
        type=None,
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
        total_competitors = 0
        total_rates = 0
        for file in tractiq_files:
            file_ext = file.name.split('.')[-1].lower()
            # Extract data based on file type
            with st.spinner(f"Analyzing {file.name}..."):
                file.seek(0) # Reset file pointer
                if file_ext == 'pdf':
                    from src.pdf_processor import extract_pdf_data
                    ext_result = extract_pdf_data(file)
                elif file_ext == 'csv':
                    from src.csv_processor import extract_csv_data
                    ext_result = extract_csv_data(file)
                elif file_ext in ['xlsx', 'xls']:
                    from src.csv_processor import extract_csv_data
                    ext_result = extract_csv_data(file)
                else:
                    st.warning(f"Unsupported file type: {file.name}. Supported: PDF, CSV, Excel (xlsx/xls)")
                    continue
            st.session_state.pdf_ext_data[file.name] = ext_result
            # Count totals
            total_competitors += len(ext_result.get('competitors', []))
            total_rates += len(ext_result.get('extracted_rates', []))
            # Show extraction summary as toasts
            if ext_result.get('competitors'):
                st.toast(f"📊 Found {len(ext_result['competitors'])} competitors in {file.name}")
            if ext_result.get('extracted_rates'):
                st.toast(f"📈 Found {len(ext_result['extracted_rates'])} rates in {file.name}")
            if ext_result.get('unit_mix'):
                st.toast(f"🏢 Found unit mix data in {file.name}")
            # Show detailed extraction results in expander
            with st.expander(f"📊 Details: {file.name}", expanded=False):
                st.json({
                    "source_type": ext_result.get('source_type', 'Unknown'),
                    "competitors_found": len(ext_result.get('competitors', [])),
                    "rates_found": len(ext_result.get('extracted_rates', [])),
                    "unit_mix_sizes": list(ext_result.get('unit_mix', {}).keys()),
                    "historical_periods": len(ext_result.get('historical_trends', [])),
                    "market_metrics": list(ext_result.get('market_metrics', {}).keys()),
                    "pipeline_risk": ext_result.get('pipeline_risk', 'Standard')
                })
                # Show sample competitors
                if ext_result.get('competitors'):
                    st.markdown("**Sample Competitors:**")
                    for comp in ext_result['competitors'][:3]:
                        st.write(comp)
        # Auto-cache the extracted data (no manual button click needed)
        if st.session_state.pdf_ext_data:
            from src.tractiq_cache import cache_tractiq_data
            cache_tractiq_data(market_name, st.session_state.pdf_ext_data)
            # Show success summary
            st.success(f"✅ Extracted data from {len(tractiq_files)} files: {total_competitors} competitors, {total_rates} rates")
            st.info(f"💾 Automatically cached for market: **{market_name}**")
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
                with st.spinner("Running AI analysis..."):
                    try:
                        from src.site_intelligence import SiteIntelligence
                        from src.economic_data import fetch_economic_data
                        from src.competitor_intelligence import get_competitor_intelligence
                        from src.demographics_data import fetch_demographics_data
                        address = st.session_state.property_data['address']
                        lat = st.session_state.property_data['lat']
                        lon = st.session_state.property_data['lon']
                        # Initialize AI status
                        if 'ai_results' not in st.session_state:
                            st.session_state.ai_results = {}
                        # 1. AI Site Analysis
                        with st.status("Analyzing site with AI vision...", expanded=True) as status:
                            st.write("📸 Fetching Street View imagery...")
                            site_analyzer = SiteIntelligence()
                            ai_site_scores = site_analyzer.analyze_complete_site(
                                address=address,
                                parcel_sqft=100000, # Default
                                proposed_nra=60000 # Default
                            )
                            st.session_state.ai_results['site'] = ai_site_scores
                            st.write("✅ Site analysis complete")
                            status.update(label="Site analysis complete", state="complete")
                        # 2. Demographics Data (Phase 2!)
                        with st.status("Fetching age demographics...", expanded=True) as status:
                            st.write("👥 Querying Census Bureau API...")
                            demographics_data = fetch_demographics_data(lat, lon)
                            st.session_state.ai_results['demographics'] = demographics_data
                            st.write(f"✅ Age 25-54: {demographics_data['age_25_54_pct']}%")
                            status.update(label="Demographics retrieved", state="complete")
                        # 3. Economic Data
                        with st.status("Fetching real-time economic data...", expanded=True) as status:
                            st.write("📊 Querying BLS API...")
                            economic_indicators = fetch_economic_data(lat, lon)
                            st.session_state.ai_results['economic'] = economic_indicators
                            st.write(f"✅ Unemployment: {economic_indicators['unemployment']}%")
                            status.update(label="Economic data retrieved", state="complete")
                        # 4. Competitor Intelligence
                        with st.status("Analyzing competitor landscape...", expanded=True) as status:
                            st.write("🏢 Processing competitor data...")
                            if filtered_comps:
                                comp_intelligence = get_competitor_intelligence(
                                    competitors=filtered_comps,
                                    your_rate_psf=1.20 # Default
                                )
                                st.session_state.ai_results['competitors'] = comp_intelligence
                                st.write(f"✅ Analyzed {comp_intelligence['count']} competitors")
                            else:
                                st.session_state.ai_results['competitors'] = {
                                    'count': 0,
                                    'quality': 'Average',
                                    'pricing': 'At Market'
                                }
                                st.write("⚠️ No competitor data available")
                            status.update(label="Competitor analysis complete", state="complete")
                        st.success("🎉 AI Analysis Complete! Results displayed below.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"AI Analysis failed: {e}")
                        import traceback
                        st.code(traceback.format_exc())
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

# === PAGE 4: FEASIBILITY REPORT ===
elif page == "📋 Feasibility Report":
    st.header("Feasibility Study Report")
    scorer = st.session_state.scorer
    breakdown = scorer.get_score_breakdown()
    recommendation = scorer.get_recommendation()
    st.markdown(f"""
    <div style="background: white; padding: 30px; border-radius: 8px; margin-bottom: 20px;">
        <h2>Executive Summary</h2>
        <p><strong>Project:</strong> {st.session_state.property_data.get('name', 'N/A')}</p>
        <p><strong>Location:</strong> {st.session_state.property_data.get('address', 'N/A')}</p>
        <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
        <hr>
        <p><strong>Feasibility Score: {scorer.get_total_score()}/100 points</strong></p>
        <p><strong>Recommendation: {recommendation['decision']}</strong></p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("## Scoring Breakdown")
    scoring_df = pd.DataFrame([
        {"Category": k, "Score": v["score"], "Max": v["max"], "Percentage": f"{(v['score']/v['max']*100):.1f}%"}
        for k, v in breakdown.items()
    ])
    st.dataframe(scoring_df, hide_index=True)
    if st.button("📄 Generate Professional PDF Report", type="primary", use_container_width=True):
        with st.spinner("Generating Bob Copper-quality PDF report..."):
            try:
                from src.pdf_report_generator import generate_feasibility_pdf
                # Gather all data for report - using real data from scorer
                all_comps = st.session_state.get('all_competitors', [])
                # Calculate real competitor stats
                avg_occ = sum(c.get('occupancy_pct', 0) for c in all_comps) / len(all_comps) if all_comps else 0
                avg_rate = sum(c.get('rate_10x10_cc', 0) for c in all_comps) / len(all_comps) if all_comps else 0
                # Get financial inputs if they exist
                fin_inputs = st.session_state.get('financial_inputs', {})
                report_data = {
                    'address': st.session_state.property_data.get('address', 'Subject Property'),
                    'lat': st.session_state.property_data.get('lat', 0),
                    'lon': st.session_state.property_data.get('lon', 0),
                    'location_context': st.session_state.get('inputs', {}).get('location_context', ''),
                    'scorer_inputs': scorer.last_inputs, # Real data from scoring inputs
                    'competitors': all_comps,
                    'comp_stats': {
                        'count': len(all_comps),
                        'avg_occupancy': avg_occ,
                        'avg_rate_10x10': avg_rate,
                        'total_nrsf': sum(c.get('nrsf', 0) for c in all_comps)
                    },
                    'recommendation': recommendation,
                    'market_score': scorer.get_total_score(),
                    'score_breakdown': scorer.get_score_breakdown(),
                    'ai_results': st.session_state.get('ai_results', {}),
                    'pdf_ext_data': st.session_state.get('pdf_ext_data', {}), # TractIQ data from uploaded PDFs
                    'inputs': fin_inputs if fin_inputs else {
                        'land_cost': 1000000,
                        'construction_cost_psf': 45,
                        'rentable_sqft': 60000
                    }
                }
                # Generate PDF
                pdf_bytes = generate_feasibility_pdf(report_data)
                # Offer download
                st.success("✅ PDF Report Generated!")
                # Create download button
                st.download_button(
                    label="📥 Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"Feasibility_Study_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    type="primary"
                )
                st.info("💡 **Pro Tip:** This report is investor-ready and can be attached to loan applications")
            except Exception as e:
                st.error(f"PDF generation failed: {e}")
                import traceback
                st.code(traceback.format_exc())