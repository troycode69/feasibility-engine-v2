"""
Executive Dashboard for Self-Storage Feasibility Analysis

McKinley-level presentation dashboard with:
- Hero metrics row (Score, IRR, Market Balance, Recommendation)
- Interactive scenario comparison (Plotly)
- Sensitivity tornado diagram (Plotly)
- Competitive positioning summary
- Key investment highlights

For use within Streamlit app.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


# ============================================================================
# STYLING CONSTANTS
# ============================================================================

NAVY = '#0C2340'
ORANGE = '#F39C12'
GREEN = '#28a745'
RED = '#dc3545'
YELLOW = '#ffc107'
LIGHT_GRAY = '#f8f9fa'


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_currency(value: float, precision: int = 0) -> str:
    """Format number as currency."""
    if abs(value) >= 1_000_000:
        return f"${value/1_000_000:.1f}M"
    elif abs(value) >= 1_000:
        return f"${value/1_000:.0f}K"
    else:
        return f"${value:.{precision}f}"


def format_percentage(value: float, precision: int = 1) -> str:
    """Format number as percentage."""
    return f"{value:.{precision}f}%"


def get_recommendation_color(recommendation: str) -> str:
    """Get color for recommendation badge."""
    rec_upper = recommendation.upper()
    if rec_upper in ['PURSUE', 'STRONG BUY', 'BUY']:
        return GREEN
    elif rec_upper in ['CAUTION', 'HOLD']:
        return YELLOW
    else:
        return RED


def get_grade_color(grade: str) -> str:
    """Get color for investment grade."""
    grades = {
        'A': '#28a745',
        'B': '#5cb85c',
        'C': '#f0ad4e',
        'D': '#d9534f',
        'F': '#c9302c'
    }
    return grades.get(grade, '#666')


# ============================================================================
# METRIC CARDS
# ============================================================================

def render_hero_metrics(
    score: int,
    irr: float,
    sf_per_capita: float,
    recommendation: str,
    grade: str = None
):
    """
    Render hero metrics row at top of dashboard.

    Args:
        score: Feasibility score (0-100)
        irr: Internal rate of return (%)
        sf_per_capita: Market SF per capita
        recommendation: Investment recommendation
        grade: Optional investment grade (A-F)
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        score_color = GREEN if score >= 70 else YELLOW if score >= 50 else RED
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, {NAVY} 0%, #1a3a5c 100%);
                    padding: 20px; border-radius: 10px; text-align: center;">
            <p style="color: #aaa; margin: 0; font-size: 12px; text-transform: uppercase;">Feasibility Score</p>
            <h1 style="color: white; margin: 5px 0; font-size: 48px;">{score}</h1>
            <p style="color: {score_color}; margin: 0; font-weight: bold;">
                {'Excellent' if score >= 80 else 'Good' if score >= 70 else 'Fair' if score >= 60 else 'Marginal'} /100
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        irr_color = GREEN if irr >= 15 else YELLOW if irr >= 10 else RED
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, {NAVY} 0%, #1a3a5c 100%);
                    padding: 20px; border-radius: 10px; text-align: center;">
            <p style="color: #aaa; margin: 0; font-size: 12px; text-transform: uppercase;">Projected IRR</p>
            <h1 style="color: white; margin: 5px 0; font-size: 48px;">{irr:.1f}%</h1>
            <p style="color: {irr_color}; margin: 0; font-weight: bold;">
                {'Above Target' if irr >= 15 else 'At Target' if irr >= 12 else 'Below Target'}
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        sf_color = GREEN if sf_per_capita <= 6.0 else YELLOW if sf_per_capita <= 8.0 else RED
        market_status = 'Undersupplied' if sf_per_capita <= 6.0 else 'Balanced' if sf_per_capita <= 8.0 else 'Oversupplied'
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, {NAVY} 0%, #1a3a5c 100%);
                    padding: 20px; border-radius: 10px; text-align: center;">
            <p style="color: #aaa; margin: 0; font-size: 12px; text-transform: uppercase;">SF Per Capita</p>
            <h1 style="color: white; margin: 5px 0; font-size: 48px;">{sf_per_capita:.1f}</h1>
            <p style="color: {sf_color}; margin: 0; font-weight: bold;">{market_status}</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        rec_color = get_recommendation_color(recommendation)
        display_grade = grade if grade else ''
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, {NAVY} 0%, #1a3a5c 100%);
                    padding: 20px; border-radius: 10px; text-align: center;">
            <p style="color: #aaa; margin: 0; font-size: 12px; text-transform: uppercase;">Recommendation</p>
            <h1 style="color: {rec_color}; margin: 5px 0; font-size: 36px;">{recommendation.upper()}</h1>
            <p style="color: white; margin: 0; font-weight: bold;">
                {f'Grade: {display_grade}' if display_grade else ''}
            </p>
        </div>
        """, unsafe_allow_html=True)


def render_secondary_metrics(
    npv: float,
    dscr: float,
    occupancy: float,
    cap_rate: float
):
    """Render secondary metrics row."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Net Present Value", format_currency(npv))
    with col2:
        st.metric("Debt Service Coverage", f"{dscr:.2f}x")
    with col3:
        st.metric("Stabilized Occupancy", f"{occupancy:.0f}%")
    with col4:
        st.metric("Exit Cap Rate", f"{cap_rate:.1f}%")


# ============================================================================
# INTERACTIVE CHARTS
# ============================================================================

def render_scenario_comparison_chart(scenario_data: Dict) -> go.Figure:
    """
    Create interactive scenario comparison chart.

    Args:
        scenario_data: Dict with 'scenarios' containing conservative/base/aggressive data

    Returns:
        Plotly figure
    """
    scenarios = scenario_data.get('scenarios', {})
    if not scenarios:
        return None

    cons = scenarios.get('conservative', {})
    base = scenarios.get('base', {})
    agg = scenarios.get('aggressive', {})

    # Create subplot with two y-axes
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    scenario_names = ['Conservative', 'Base Case', 'Aggressive']
    irrs = [cons.get('irr', 0), base.get('irr', 0), agg.get('irr', 0)]
    npvs = [cons.get('npv', 0), base.get('npv', 0), agg.get('npv', 0)]

    # IRR bars
    fig.add_trace(
        go.Bar(
            name='IRR (%)',
            x=scenario_names,
            y=irrs,
            marker_color=[YELLOW, GREEN, '#17a2b8'],
            text=[f"{v:.1f}%" for v in irrs],
            textposition='outside',
            textfont=dict(size=14, color=NAVY),
        ),
        secondary_y=False,
    )

    # NPV line
    fig.add_trace(
        go.Scatter(
            name='NPV ($)',
            x=scenario_names,
            y=npvs,
            mode='lines+markers+text',
            line=dict(color=ORANGE, width=3),
            marker=dict(size=12),
            text=[format_currency(v) for v in npvs],
            textposition='top center',
            textfont=dict(size=12, color=ORANGE),
        ),
        secondary_y=True,
    )

    # Add expected value line
    expected_irr = scenario_data.get('expected_irr', 0)
    fig.add_hline(
        y=expected_irr,
        line_dash="dash",
        line_color=NAVY,
        annotation_text=f"Expected IRR: {expected_irr:.1f}%",
        annotation_position="right",
        secondary_y=False
    )

    fig.update_layout(
        title=dict(text='Scenario Analysis: IRR and NPV', font=dict(size=18, color=NAVY)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        barmode='group',
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=400,
    )

    fig.update_yaxes(title_text="IRR (%)", secondary_y=False, gridcolor='#e0e0e0')
    fig.update_yaxes(title_text="NPV ($)", secondary_y=True, gridcolor='#e0e0e0')

    return fig


def render_sensitivity_tornado(sensitivity_data: Dict) -> go.Figure:
    """
    Create interactive tornado chart for sensitivity analysis.

    Args:
        sensitivity_data: Dict with 'results' list and 'base_irr'

    Returns:
        Plotly figure
    """
    results = sensitivity_data.get('results', [])
    base_irr = sensitivity_data.get('base_irr', 0)

    if not results:
        return None

    # Sort by impact magnitude
    results_sorted = sorted(
        results,
        key=lambda x: abs(x.get('high_irr', 0) - x.get('low_irr', 0)),
        reverse=True
    )

    variables = [r.get('variable', '') for r in results_sorted]
    low_values = [r.get('low_irr', 0) for r in results_sorted]
    high_values = [r.get('high_irr', 0) for r in results_sorted]

    fig = go.Figure()

    # Low side bars (negative impact from base)
    fig.add_trace(go.Bar(
        name='Downside',
        y=variables,
        x=[low - base_irr for low in low_values],
        orientation='h',
        marker_color=RED,
        text=[f"{v:.1f}%" for v in low_values],
        textposition='outside',
        textfont=dict(size=11),
    ))

    # High side bars (positive impact from base)
    fig.add_trace(go.Bar(
        name='Upside',
        y=variables,
        x=[high - base_irr for high in high_values],
        orientation='h',
        marker_color=GREEN,
        text=[f"{v:.1f}%" for v in high_values],
        textposition='outside',
        textfont=dict(size=11),
    ))

    # Add base case line
    fig.add_vline(x=0, line_width=2, line_color=NAVY, line_dash='dash')

    fig.update_layout(
        title=dict(
            text=f'IRR Sensitivity Analysis (Base Case: {base_irr:.1f}%)',
            font=dict(size=18, color=NAVY)
        ),
        xaxis_title="Change from Base Case IRR (%)",
        barmode='overlay',
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=300 + len(variables) * 40,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )

    fig.update_xaxes(gridcolor='#e0e0e0')

    return fig


def render_scoring_radar(score_breakdown: Dict) -> go.Figure:
    """
    Create interactive radar chart for scoring breakdown.

    Args:
        score_breakdown: Dict with category scores and max values

    Returns:
        Plotly figure
    """
    categories = ['Demographics', 'Supply/Demand', 'Site Quality', 'Competition', 'Economic']
    max_values = [25, 25, 25, 15, 10]

    scores = [
        score_breakdown.get('demographics', {}).get('score', 0),
        score_breakdown.get('supply', {}).get('score', 0),
        score_breakdown.get('site', {}).get('score', 0),
        score_breakdown.get('competitor', {}).get('score', 0),
        score_breakdown.get('economic', {}).get('score', 0)
    ]

    # Normalize to percentage
    normalized = [s / m * 100 if m > 0 else 0 for s, m in zip(scores, max_values)]

    # Close the polygon
    categories_closed = categories + [categories[0]]
    normalized_closed = normalized + [normalized[0]]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=normalized_closed,
        theta=categories_closed,
        fill='toself',
        fillcolor=f'rgba(12, 35, 64, 0.3)',
        line=dict(color=NAVY, width=2),
        name='Score',
        text=[f"{s}/{m}" for s, m in zip(scores, max_values)] + [f"{scores[0]}/{max_values[0]}"],
        hovertemplate='%{theta}: %{text}<br>(%{r:.0f}% of max)<extra></extra>',
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor='#e0e0e0',
            ),
            bgcolor='white',
        ),
        showlegend=False,
        title=dict(text='Feasibility Score Breakdown', font=dict(size=18, color=NAVY)),
        height=400,
        paper_bgcolor='white',
    )

    return fig


def render_noi_projection_chart(annual_summaries: List[Dict]) -> go.Figure:
    """
    Create NOI projection chart.

    Args:
        annual_summaries: List of annual summary dicts with 'year' and 'noi'

    Returns:
        Plotly figure
    """
    if not annual_summaries:
        return None

    years = [f"Year {s.get('year', i+1)}" for i, s in enumerate(annual_summaries)]
    noi_values = [s.get('noi', 0) for s in annual_summaries]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=years,
        y=noi_values,
        marker_color=[YELLOW if i < 2 else ORANGE if i < 3 else GREEN for i in range(len(years))],
        text=[format_currency(v) for v in noi_values],
        textposition='outside',
        textfont=dict(size=12, color=NAVY),
    ))

    fig.update_layout(
        title=dict(text='7-Year NOI Projection', font=dict(size=18, color=NAVY)),
        xaxis_title='Year',
        yaxis_title='Net Operating Income ($)',
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=350,
    )

    fig.update_yaxes(gridcolor='#e0e0e0')

    return fig


# ============================================================================
# MAIN DASHBOARD FUNCTION
# ============================================================================

def render_executive_dashboard(
    address: str,
    score: int,
    score_breakdown: Dict,
    recommendation: Dict,
    proforma_data: Dict,
    sensitivity_data: Dict = None,
    scenario_data: Dict = None,
    investment_data: Dict = None,
    market_data: Dict = None
):
    """
    Render the complete executive dashboard.

    Args:
        address: Site address
        score: Overall feasibility score (0-100)
        score_breakdown: Category scores
        recommendation: Recommendation dict
        proforma_data: Pro forma financial data
        sensitivity_data: Sensitivity analysis results
        scenario_data: Scenario analysis results
        investment_data: Investment analysis results
        market_data: Market metrics
    """
    # Header
    st.markdown(f"""
    <h1 style="color: {NAVY}; border-bottom: 3px solid {ORANGE}; padding-bottom: 10px;">
        Executive Dashboard
    </h1>
    <p style="font-size: 16px; color: #666;">
        {address}
    </p>
    """, unsafe_allow_html=True)

    # Extract key metrics
    irr = proforma_data.get('irr', 0)
    sf_per_capita = market_data.get('sf_per_capita', 7.0) if market_data else 7.0
    rec_decision = recommendation.get('decision', 'PENDING')
    grade = investment_data.get('grade', '') if investment_data else ''

    # Hero metrics row
    st.markdown("### Key Metrics")
    render_hero_metrics(
        score=score,
        irr=irr,
        sf_per_capita=sf_per_capita,
        recommendation=rec_decision,
        grade=grade
    )

    st.markdown("---")

    # Two-column layout for charts
    col1, col2 = st.columns(2)

    with col1:
        # Scoring radar
        st.markdown("### Score Breakdown")
        radar_fig = render_scoring_radar(score_breakdown)
        if radar_fig:
            st.plotly_chart(radar_fig, use_container_width=True)

    with col2:
        # Scenario comparison
        if scenario_data and scenario_data.get('scenarios'):
            st.markdown("### Scenario Analysis")
            scenario_fig = render_scenario_comparison_chart(scenario_data)
            if scenario_fig:
                st.plotly_chart(scenario_fig, use_container_width=True)
        else:
            # NOI projection fallback
            annual_summaries = proforma_data.get('annual_summaries', [])
            if annual_summaries:
                st.markdown("### NOI Projection")
                noi_fig = render_noi_projection_chart(annual_summaries)
                if noi_fig:
                    st.plotly_chart(noi_fig, use_container_width=True)

    st.markdown("---")

    # Sensitivity tornado (full width)
    if sensitivity_data and sensitivity_data.get('results'):
        st.markdown("### Sensitivity Analysis")
        tornado_fig = render_sensitivity_tornado(sensitivity_data)
        if tornado_fig:
            st.plotly_chart(tornado_fig, use_container_width=True)

    # Investment summary
    if investment_data:
        st.markdown("---")
        st.markdown("### Investment Analysis Summary")

        col1, col2, col3 = st.columns(3)

        with col1:
            breakeven = investment_data.get('breakeven', {})
            st.metric(
                "Breakeven Occupancy",
                f"{breakeven.get('occupancy_pct', 0):.1f}%",
                delta=f"{92 - breakeven.get('occupancy_pct', 0):.1f}% cushion" if breakeven.get('occupancy_pct', 0) < 92 else None
            )

        with col2:
            debt = investment_data.get('debt_sizing', {})
            st.metric(
                "DSCR",
                f"{debt.get('dscr', 0):.2f}x",
                delta="Above 1.25x min" if debt.get('dscr', 0) >= 1.25 else "Below 1.25x min"
            )

        with col3:
            grade = investment_data.get('grade', 'N/A')
            rec = investment_data.get('recommendation', '')
            grade_emoji = {'A': '', 'B': '', 'C': '', 'D': '', 'F': ''}.get(grade, '')
            st.metric("Investment Grade", f"{grade}", delta=rec)

    # Recommendation box
    st.markdown("---")
    rec_color = get_recommendation_color(rec_decision)
    confidence = recommendation.get('confidence', 'Medium')
    narrative = recommendation.get('narrative', 'Analysis pending.')

    st.markdown(f"""
    <div style="background: {LIGHT_GRAY}; border-left: 5px solid {rec_color}; padding: 20px; border-radius: 5px;">
        <h3 style="color: {rec_color}; margin-top: 0;">Recommendation: {rec_decision.upper()}</h3>
        <p><strong>Confidence:</strong> {confidence}</p>
        <p>{narrative}</p>
    </div>
    """, unsafe_allow_html=True)
