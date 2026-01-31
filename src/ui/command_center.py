"""
Command Center UI Component

This module contains the UI logic for the Command Center page,
which includes CRM dashboard, lead lists, AI chat, and data ingestion.
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Import necessary dependencies
try:
    from config import Config
except ImportError:
    # Fallback Config if not available
    class Config:
        CONTACTS_TAB = "Contacts"
        PROPERTIES_TAB = "Properties"

try:
    from main import SecretaryAgent
except ImportError:
    SecretaryAgent = None

try:
    from crm_adjustor import (
        get_actionable_leads,
        get_profile_candidates,
        get_skip_trace_list,
        run_adjustor_sync
    )
except ImportError:
    get_actionable_leads = None
    get_profile_candidates = None
    get_skip_trace_list = None
    run_adjustor_sync = None


def render_command_center():
    """
    Renders the Command Center page UI.
    
    This function displays:
    - Dashboard metrics (total contacts, properties)
    - Live feasibility score gauge
    - Smart lead lists (Actionable, Profile, Skip Trace)
    - CRM Analyst AI chat interface
    - Data ingestion uploader and processor
    """
    st.header("Command Center")
    # Custom Card Style for Command Center Layout

    # Custom Card Style for Command Center Layout
    
    st.caption(f"📅 {datetime.now().strftime('%A, %B %d, %Y')}")
    
    # Hero Section (Juniper Square Style)
    st.markdown('<div class="hero-card">', unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown('<p class="hero-metric-label">Dashboard</p>', unsafe_allow_html=True)
        # Fetch Data
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
        
        # Custom Metric Display
        m1, m2 = st.columns(2)
        with m1:
            st.markdown(f'<p class="hero-metric-label">Total Contacts</p><p class="hero-metric-value">{total_contacts}</p>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<p class="hero-metric-label">Properties</p><p class="hero-metric-value">{total_props}</p>', unsafe_allow_html=True)
            
    st.markdown('</div>', unsafe_allow_html=True) # End Top Dashboard Card

    # Centered Hero Card for Feasibility Score
    if "scorer" in st.session_state:
        score = st.session_state.scorer.get_total_score()
        scorecard = st.session_state.get("analysis_results", {}).site_scorecard if hasattr(st.session_state.get("analysis_results", {}), "site_scorecard") else None
        
        col_side, col_center, col_side2 = st.columns([1, 2, 1])
        with col_center:
            score_color = "#27A745" if score >= 70 else "#FFA500" if score >= 55 else "#D0021B"
            
            # Create Plotly Gauge
            import plotly.graph_objects as go
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = score,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Live Feasibility Score", 'font': {'size': 18, 'color': "#0C2340", 'family': "Inter"}},
                gauge = {
                    'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "#0C2340"},
                    'bar': {'color': score_color},
                    'bgcolor': "white",
                    'borderwidth': 2,
                    'bordercolor': "#E2E8F0",
                    'steps': [
                        {'range': [0, 55], 'color': 'rgba(208, 2, 27, 0.1)'},
                        {'range': [55, 70], 'color': 'rgba(255, 165, 0, 0.1)'},
                        {'range': [70, 100], 'color': 'rgba(39, 167, 69, 0.1)'}
                    ],
                }
            ))
            fig.update_layout(
                height=220, 
                margin=dict(l=20, r=20, t=0, b=0), 
                paper_bgcolor="rgba(0,0,0,0)", 
                font={'color': "#0C2340", 'family': "Inter"}
            )
            
            st.markdown('<div class="hero-card">', unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True)
            if scorecard:
                 st.markdown(f"""
                <div style="text-align: center; margin-top: -30px;">
                    <h2 style="color: {score_color}; margin-bottom: 5px;">{scorecard.tier}</h2>
                    <p style="color: #64748B; font-size: 1rem;">{scorecard.recommendation}</p>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # === SMART LEAD LISTS ===
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
