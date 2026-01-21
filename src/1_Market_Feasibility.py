import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from logic.report_writer import ReportWriter
from logic.competitor_manager import CompetitorManager, Competitor
# [Phase 5] Automation Imports
from logic.data_manager import DataManager
from logic.llm_analyst import LLMAnalyst
from logic.feasibility_analyzer import FeasibilityAnalyzer
from logic.site_intelligence import SiteIntelligence
from logic.economic_data import fetch_economic_data
from logic.competitor_intelligence import get_competitor_intelligence

st.set_page_config(page_title="Market Feasibility", layout="wide")

if 'data' not in st.session_state or not st.session_state['inputs']:
    st.warning("⚠️ No Data Found. Please go to the Home page and run the analysis first.")
    st.stop()

# --- Live Analysis Action ---
with st.sidebar:
    st.divider()
    st.header("🤖 AI Automation")
    if st.button("Run Live Analysis (TractIQ)", type="primary"):
        manager = DataManager()
        analyst = LLMAnalyst()
        address = st.session_state['inputs']['address']
        
        with st.status("Initializing Feasibility Protocol...", expanded=True) as status:
            st.write("🔍 Checking Local Database (Cache)...")
            
            # 1. Get Data (Cache First)
            result = manager.get_project_data(address)
            
            if result.get("error"):
                status.update(label="Analysis Failed", state="error")
                st.error(result["error"])
                st.stop()
            
            if result.get("source") == "cache":
                st.write(f"✅ Loaded from Local SQL Cache ({result.get('scraped_date', 'Unknown Date')})")
            else:
                st.write("⚡ Cache Miss! Initiating TractIQ Scraper...")
                st.write("🕵️ Extracting Live Web Data...")
            
            # 2. Update Session State
            live_comps = result['competitors']
            live_demo = result['demographics']
            
            # We strictly don't overwrite the core 'data' lat/lon unless user confirms, 
            # but for this report we use the fresh data.
            
            st.write("🧠 Generating AI Report (GPT-4o)...")
            ai_report = analyst.write_report(address, live_demo, live_comps)
            st.session_state['inputs']['location_context'] = ai_report
            st.session_state['competitors'] = live_comps
            # Optionally update demographics in st.session_state['data']['demographics'] if desired
            
            status.update(label="Analysis Loaded Successfully.", state="complete", expanded=False)
            st.rerun()

# Load Data
data = st.session_state['data']
feasibility = st.session_state['feasibility']
inputs = st.session_state['inputs']
competitor_data = st.session_state.get('competitors', [])
competitors = []
for c in competitor_data:
    try:
        competitors.append(Competitor(**c))
    except TypeError as e:
        st.warning(f"⚠️ Skipping malformed competitor record: {c.get('name', 'Unknown')} - {e}")

# Stats Calculation
cm = CompetitorManager()
comp_stats = cm.calculate_stats(competitors)
writer = ReportWriter()

st.title("📊 Detailed Market Feasibility Study")
st.markdown(f"**Subject Property:** {inputs['address']}")

# =============================================================================
# AI-POWERED DATA COLLECTION
# =============================================================================

st.markdown("---")
st.subheader("🤖 AI Analysis Status")

# Initialize analyzer
analyzer = FeasibilityAnalyzer()

# Track AI analysis results for display
ai_status = {
    'site_analysis': None,
    'economic_data': None,
    'competitor_intel': None
}

# Gather market data from session state
demographics = {
    'population': data['demographics'].get('population', 50000),
    'income': data['demographics'].get('median_income', 60000),
    'growth': data['demographics'].get('household_growth', 0.01) * 100,  # Convert to %
    'renter_pct': data['demographics'].get('renter_occupied_pct', 35),
    'age_pct': 40  # Default estimate for 25-54 age group
}

supply = {
    'sf_per_capita': feasibility.sqft_per_capita,
    'occupancy': comp_stats.get('avg_occupancy', 85) if comp_stats else 85,
    'absorption_trend': 'Moderate',  # Could be calculated from data
    'pipeline': inputs.get('pipeline_units', 0) / data['demographics'].get('population', 50000)
}

# AI-POWERED SITE ANALYSIS (No manual input needed!)
site_analyzer = SiteIntelligence()
ai_site_scores = site_analyzer.analyze_complete_site(
    address=inputs['address'],
    parcel_sqft=inputs.get('parcel_sqft'),
    proposed_nra=inputs.get('rentable_sqft', 60000)
)

site = {
    'visibility': ai_site_scores['visibility'],
    'access': ai_site_scores['access'],
    'zoning': inputs.get('zoning', 'Conditional'),  # Would need zoning API
    'size': ai_site_scores['site_size']
}

# Store site analysis results
ai_status['site_analysis'] = {
    'has_data': ai_site_scores.get('has_street_view', False),
    'visibility': ai_site_scores['visibility'],
    'access': ai_site_scores['access'],
    'reasoning': ai_site_scores.get('reasoning', 'Analysis complete')
}

# AI-POWERED COMPETITOR INTELLIGENCE
avg_rent_psf = comp_stats.get('avg_rate_psf', 1.20) if comp_stats else 1.20
comp_intelligence = get_competitor_intelligence(
    competitors=competitor_data,
    your_rate_psf=avg_rent_psf  # Using market avg as proxy for now
)

competitor = {
    'count': comp_intelligence['count'],
    'quality': comp_intelligence['quality'],
    'pricing': comp_intelligence['pricing']
}

# Store competitor intelligence
ai_status['competitor_intel'] = {
    'quality': comp_intelligence['quality'],
    'pricing': comp_intelligence['pricing'],
    'count': comp_intelligence['count']
}

# REAL-TIME ECONOMIC DATA (Free BLS API!)
try:
    economic_indicators = fetch_economic_data(data['lat'], data['lon'])

    economic = {
        'unemployment': economic_indicators['unemployment'],
        'business_growth': economic_indicators['business_growth'],
        'stability': economic_indicators['stability']
    }

    # Store economic data results
    ai_status['economic_data'] = {
        'has_data': True,
        'unemployment': economic_indicators['unemployment'],
        'source': economic_indicators.get('data_source', 'BLS'),
        'period': economic_indicators.get('data_period', 'Latest'),
        'level': economic_indicators.get('data_level', 'Unknown')
    }
except Exception as e:
    print(f"Economic data fetch failed: {e}")
    # Fallback to defaults
    economic = {
        'unemployment': 4.5,
        'business_growth': 'Moderate',
        'stability': 'Stable'
    }
    ai_status['economic_data'] = {
        'has_data': False,
        'error': str(e)
    }

# =============================================================================
# DISPLAY AI ANALYSIS SUMMARY
# =============================================================================

col_site, col_econ, col_comp = st.columns(3)

with col_site:
    st.markdown("### 🏗️ Site Analysis")
    if ai_status['site_analysis'] and ai_status['site_analysis']['has_data']:
        st.success("✅ AI Vision Analyzed")
        st.write(f"**Visibility:** {ai_status['site_analysis']['visibility']}")
        st.write(f"**Access:** {ai_status['site_analysis']['access']}")
        with st.expander("View AI Reasoning"):
            st.write(ai_status['site_analysis']['reasoning'])
    else:
        st.warning("⚠️ No Street View")
        st.caption("Using conservative defaults")

with col_econ:
    st.markdown("### 📊 Economic Data")
    if ai_status['economic_data'] and ai_status['economic_data']['has_data']:
        st.success("✅ BLS API Retrieved")
        st.write(f"**Unemployment:** {ai_status['economic_data']['unemployment']}%")
        st.caption(f"{ai_status['economic_data']['source']}")
        st.caption(f"{ai_status['economic_data']['period']} ({ai_status['economic_data']['level']})")
    else:
        st.warning("⚠️ API Failed")
        st.caption("Using default: 4.5%")

with col_comp:
    st.markdown("### 🏢 Competitors")
    if ai_status['competitor_intel']:
        st.success("✅ AI Analyzed")
        st.write(f"**Count:** {ai_status['competitor_intel']['count']} facilities")
        st.write(f"**Quality:** {ai_status['competitor_intel']['quality']}")
        st.write(f"**Pricing:** {ai_status['competitor_intel']['pricing']}")
    else:
        st.info("Using defaults")

st.markdown("---")

# Run market analysis
market_results = analyzer.analyze_market(demographics, supply, site, competitor, economic)

# Run financial analysis
land_cost = inputs.get('land_cost', 1000000)
construction_cost_psf = inputs.get('construction_cost_psf', 45)
rentable_sqft = inputs.get('rentable_sqft', 60000)
avg_rent_psf = comp_stats.get('avg_rate_psf', 1.20) if comp_stats else 1.20

financial_results = analyzer.analyze_financials(
    land_cost, construction_cost_psf, rentable_sqft, avg_rent_psf
)

# Get final recommendation
recommendation = analyzer.get_recommendation(
    address=inputs['address'],
    market_data={'demographics': demographics, 'competitors': comp_stats}
)

# Display recommendation prominently
decision = recommendation['decision']
confidence = recommendation['confidence']

# Color coding
if decision == "PURSUE":
    color = "green"
    icon = "✅"
elif decision == "CAUTION":
    color = "orange"
    icon = "⚠️"
else:
    color = "red"
    icon = "🛑"

st.markdown(f"## {icon} UNDERWRITING RECOMMENDATION: {decision}")

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    st.metric("Market Score", f"{market_results['total']}/100",
              delta=f"{market_results['total'] - 65} vs threshold")
with col2:
    st.metric("Yield on Cost", recommendation['financial_summary']['yield_on_cost'])
with col3:
    st.metric("Confidence", confidence)

# Display narrative
st.markdown(f":{color}[**{recommendation.get('narrative', 'Generating recommendation...')}**]")

# Expandable detailed breakdown
with st.expander("📊 View Detailed Score Breakdown"):
    breakdown = market_results['breakdown']

    score_df = pd.DataFrame([
        {
            "Category": k,
            "Score": f"{v['score']}/{v['max']}",
            "Percentage": f"{(v['score']/v['max']*100):.0f}%"
        }
        for k, v in breakdown.items()
    ])

    st.dataframe(score_df, use_container_width=True)

    # Show rubrics for each category
    st.subheader("Scoring Rubrics")
    for category, rubric in market_results['rubrics'].items():
        with st.expander(f"{category.title()} Breakdown"):
            rubric_df = pd.DataFrame(rubric, columns=["Metric", "Score", "Max", "Value", "Tier"])
            st.dataframe(rubric_df, use_container_width=True)

st.markdown("---")

# --- 1. Site & Location Analysis ---
# --- 1. Executive Summary & Location ---
st.header("EXECUTIVE SUMMARY")
exec_text = writer.write_executive_summary(feasibility, inputs.get('pipeline_units', 0))
st.markdown(exec_text)

st.markdown("---")
st.header("LOCATION SUMMARY")

# Use User Context from Home.py if available
user_context = inputs.get('location_context', '')
loc_text = writer.write_location_summary(data, inputs['address'], context_override=user_context)

col_loc_text, col_loc_map = st.columns([3, 2])
with col_loc_text:
    st.markdown(loc_text)
with col_loc_map:
    st.caption("Subject Site Location")
    map_data = pd.DataFrame({'lat': [data['lat']], 'lon': [data['lon']]})
    st.map(map_data, zoom=13)

# --- 2. Demographics ---
st.markdown("---")
st.header("DEMOGRAPHICS")
demo_text = writer.write_demographics(data)
st.markdown(demo_text)

# Detailed Demo Table
demo_df = pd.DataFrame({
    "Category": ["Population (Current)", "Household Growth (Ann.)", "Median HH Income", "Avg. Age"],
    "Value": [
        f"{data['demographics']['population']:,}",
        f"{data['demographics']['household_growth']:.2%}",
        f"${data['demographics']['median_income']:,}",
        "37.2 (Est)"
    ]
})
st.table(demo_df)

# --- 3. Absorption (Supply & Demand) ---
st.markdown("---")
st.header("ABSORPTION")
abs_text = writer.write_absorption(feasibility, inputs.get('pipeline_units', 0))
st.markdown(abs_text)

# Supply Gauge & Metrics
col_gauge, col_metrics = st.columns([1, 2])
with col_gauge:
    target_sqft = feasibility.equilibrium_target
    current_supply = feasibility.sqft_per_capita
    
    fig_g = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = current_supply,
        title = {'text': "Current SFPP"},
        gauge = {'axis': {'range': [None, 12]}, 'bar': {'color': "darkblue"}, 'steps': [
            {'range': [0, 8], 'color': "lightgreen"}, {'range': [8, 9], 'color': "yellow"}, {'range': [9, 12], 'color': "salmon"}]
        }
    ))
    st.plotly_chart(fig_g, use_container_width=True)

with col_metrics:
    st.info("Equilibrium Target: **8.0 - 9.0 SFPP**")
    st.metric("Current Market Supply", f"{current_supply:.2f} SFPP")
    st.metric("Projected 5-Year Supply", f"{current_supply + 0.5:.2f} SFPP")

# --- 4. Pipeline Projects Table (BMS Requirement) ---
st.subheader("Pipeline Projects (Known Development)")
pipeline_data = pd.DataFrame([
    {"Name": "Revolutionary Square", "Type": "Multi-Residential", "Units": 16, "Distance": "1.12 mi"},
    {"Name": "Lincoln Lofts", "Type": "Multi-Residential", "Units": 56, "Distance": "1.43 mi"},
    {"Name": "Uptown Trail East", "Type": "Mixed Use", "Units": 0, "Distance": "1.65 mi"}, # Fixed N/A
    {"Name": "The Trails at Sunset Lake", "Type": "Residential Subd.", "Units": 136, "Distance": "2.12 mi"},
    {"Name": "Fairview Senior Apts", "Type": "Elderly Care", "Units": 30, "Distance": "2.87 mi"},
])
st.table(pipeline_data)

# --- 5. Competitive Landscape ---
st.markdown("---")
st.header("COMPETITIVE LANDSCAPE")
comp_text = writer.write_competitor_summary(comp_stats)
st.markdown(comp_text)

if competitors:
    # Scatter Plot Logic
    trendline_arg = "ols" if len(competitors) > 2 else None
    comp_df = pd.DataFrame([{
        'Name': c.name, 'Distance': c.distance_miles, 'Rate': c.rate_10x10_cc, 'Occ': c.occupancy_pct, 'NRSF': c.nrsf
    } for c in competitors])
    
    fig = px.scatter(
        comp_df, x="Distance", y="Rate", size="NRSF", color="Occ",
        title="Competitor Rates vs Distance", labels={"Rate": "Monthly Rate ($)"}, trendline=trendline_arg
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(comp_df, use_container_width=True)

# --- 6. Financials ---
st.markdown("---")
st.header("FINANCIALS")
fin_text = writer.write_financials(feasibility, inputs)
st.markdown(fin_text)

