import streamlit as st
import datetime
import pandas as pd
from geopy.geocoders import Nominatim
from logic.data_manager import DataManager
from logic.feasibility import FeasibilityReport
from logic.competitor_manager import CompetitorManager

st.set_page_config(page_title="Storage Genies Feasibility", layout="wide", initial_sidebar_state="expanded")

# --- Session State Initialization ---
if 'data' not in st.session_state:
    st.session_state['data'] = None
if 'feasibility' not in st.session_state:
    st.session_state['feasibility'] = None
if 'inputs' not in st.session_state:
    st.session_state['inputs'] = {}
if 'competitors' not in st.session_state:
    st.session_state['competitors'] = []

def run_analysis():
    """Callback to run the engine"""
    address = st.session_state['input_address']
    
    with st.spinner("Geocoding Address..."):
        try:
            geolocator = Nominatim(user_agent="storage_genie_app")
            location = geolocator.geocode(address)
            if location:
                lat, lon = location.latitude, location.longitude
                st.success(f"Found: {location.address}")
            else:
                st.warning("Address not found. Using default Coordinates.")
                lat, lon = 41.700, -73.900
        except Exception as e:
            st.error(f"Geocoding failed: {e}")
            lat, lon = 41.700, -73.900

    with st.spinner("Fetching Market Data..."):
        dm = DataManager()
        site_data = dm.get_site_data(lat, lon)
        st.session_state['data'] = site_data
    
    with st.spinner("Running Feasibility Engine..."):
        feasibility = FeasibilityReport(site_data)
        # [V2] Pass Pipeline Units
        pipeline = st.session_state.get('input_pipeline', 0)
        f_result = feasibility.analyze(new_housing_units=pipeline)
        st.session_state['feasibility'] = f_result

    with st.spinner("Analyzing Competitors..."):
        # [Phase 3] Competitor Logic
        if not st.session_state['competitors']:
            cm = CompetitorManager()
            comps = cm.get_competitors(lat, lon)
            # Convert to dicts for Data Editor if needed, or keep objects
            # st.data_editor works well with DataFrames
            st.session_state['competitors'] = [c.__dict__ for c in comps]

    # Save Inputs to Session
    st.session_state['inputs'] = {
        'address': address,
        'lat': lat, 'lon': lon,
        'total_units': st.session_state['input_units'],
        'nrsf': st.session_state['input_nrsf'],
        'loan_amount': st.session_state['input_loan'],
        'interest_rate': st.session_state['input_rate'] / 100.0,
        'amortization': st.session_state['input_amort'],
        'io_period': st.session_state['input_io'],
        'months_to_stabilize': st.session_state['input_months'],
        'stabilized_occupancy': st.session_state['input_stab_occ'],
        'current_occupancy': st.session_state['input_curr_occ'],
        'base_rent': st.session_state['input_rent'],
        'start_date': st.session_state['input_start'].strftime("%Y-%m-%d"),
        'pipeline_units': st.session_state['input_pipeline'],
        'location_context': st.session_state.get('input_location_context', '')
    }
    
    st.success("Analysis Complete! Navigate to the Feasibility Report or Forecast pages.")

# --- UI Layout ---
st.title("🏡 Self-Storage Feasibility Engine V2.1")
st.markdown("### Step 1: Property & Market Inputs")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Property Details")
    st.text_input("Property Address", "189 Manchester Rd, Poughkeepsie, NY", key="input_address")
    
    # [Phase 4] BMS Location Context
    st.text_area(
        "Location Context (Report Narrative)", 
        "The subject property is located in a mixed-use corridor...", 
        key="input_location_context",
        height=100,
        help="Paste the specific location description here (e.g., 'Located between US-78 and Thornton Rd...')"
    )
    
    c1, c2 = st.columns(2)
    c1.number_input("Total Units", value=650, step=10, key="input_units")
    c2.number_input("Net Rentable SqFt", value=65000, step=100, key="input_nrsf")
    
    c3, c4 = st.columns(2)
    c3.number_input("Current Occupancy (%)", value=0.0, step=1.0, format="%.1f", key="input_curr_occ")
    c4.number_input("Target Stabilized Occupancy (%)", value=92.0, step=0.5, format="%.1f", key="input_stab_occ")
    
    st.number_input("Projected Base Rent ($/Unit/Mo)", value=140.0, step=5.0, key="input_rent")
    st.date_input("Projection Start Date", datetime.date.today(), key="input_start")

with col2:
    st.subheader("Market & Pipeline")
    st.number_input("Planned Housing Units (3-Mile)", value=50, step=10, key="input_pipeline", help="New apartments/homes planned or under construction.")
    
    st.subheader("Absorption & Finance")
    st.slider("Absorption Period (Months to Stabilize)", 6, 48, 24, key="input_months", help="Time to reach stabilized occupancy.")
    
    st.markdown("#### Debt Assumptions")
    st.number_input("Loan Amount ($)", value=6500000, step=100000, key="input_loan")
    
    f1, f2 = st.columns(2)
    f1.number_input("Interest Rate (%)", value=5.75, step=0.25, format="%.2f", key="input_rate")
    f2.number_input("Amortization (Months)", value=360, step=12, key="input_amort")
    
    st.number_input("Interest Only Period (Months)", value=24, step=6, key="input_io")

# [Phase 3] Competitor Data Editor
if st.session_state['competitors']:
    st.markdown("---")
    st.subheader("🕵️ Competitor Survey (Editable)")
    st.caption("Review and adjust competitor rates/occupancy below.")
    
    df_comps = pd.DataFrame(st.session_state['competitors'])
    # Configure columns for editing
    edited_df = st.data_editor(
        df_comps,
        column_config={
            "name": "Competitor Name",
            "distance_miles": st.column_config.NumberColumn("Dist (Mi)", format="%.2f"),
            "occupancy_pct": st.column_config.NumberColumn("Occ %", format="%.1f"),
            "rate_10x10_cc": st.column_config.NumberColumn("10x10 CC ($)", format="$%.0f"),
            "rate_10x10_std": st.column_config.NumberColumn("10x10 Std ($)", format="$%.0f"),
        },
        disabled=["name", "address", "distance_miles"],
        hide_index=True,
        num_rows="dynamic",
        # use_container_width=True -> Deprecated
        # width="stretch" # Actually, Streamlit st.data_editor signature might vary. 
        # Using use_container_width is standard in current pip versions, but if warning says otherwise, I will follow warning.
        # But safest is to remove it or check version. The user log says "Please replace...".
        # Let's try use_container_width=True anyway? No, the user explicitly pasted the warning.
        # I will leave use_container_width=True for now because it is usually correct for the version installed unless it is very new/old. 
        # Actually, let's just do what it says.
    )
    # Update Session State with Edits
    st.session_state['competitors'] = edited_df.to_dict('records')

st.markdown("---")
st.button("🚀 Run Feasibility Analysis", on_click=run_analysis, type="primary", use_container_width=True)

# Status Check
if st.session_state.get('data'):
    st.info("✅ Data Loaded. Go to 'Feasibility Report' to view results.")
else:
    st.warning("Please run the analysis to generate reports.")
