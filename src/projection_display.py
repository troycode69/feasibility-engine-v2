"""
Modern UI component for displaying 7-Year Projection
Matches Excel layout with expand/collapse functionality
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def render_7year_projection(annual_summary, monthly_projection, property_info):
    """
    Render modern 7-Year Projection display

    Args:
        annual_summary: DataFrame with annual totals (from generate_annual_summary)
        monthly_projection: DataFrame with monthly detail
        property_info: Dict with property details (name, address, SF, units)
    """

    # Header Section
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px; margin-bottom: 30px;">
        <h2 style="color: white; margin: 0;">{property_info.get('name', 'Property Projection')}</h2>
        <p style="color: rgba(255,255,255,0.9); margin: 5px 0;">{property_info.get('address', '')}</p>
        <div style="display: flex; gap: 40px; margin-top: 20px;">
            <div>
                <div style="color: rgba(255,255,255,0.7); font-size: 12px;">Net Rentable SF</div>
                <div style="color: white; font-size: 24px; font-weight: bold;">{property_info.get('total_sf', 0):,.0f}</div>
            </div>
            <div>
                <div style="color: rgba(255,255,255,0.7); font-size: 12px;">Total Units</div>
                <div style="color: white; font-size: 24px; font-weight: bold;">{property_info.get('total_units', 0):,.0f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Key Metrics Dashboard
    st.markdown("### 📊 Key Performance Indicators")
    _render_kpi_dashboard(annual_summary)

    st.markdown("---")

    # Lease-Up Curve
    st.markdown("### 📈 Lease-Up Performance")
    _render_leaseup_chart(monthly_projection)

    st.markdown("---")

    # Annual Projection Table
    st.markdown("### 💰 7-Year Financial Projection")
    _render_projection_table(annual_summary)

    st.markdown("---")

    # Monthly Detail (Expandable)
    with st.expander("📅 View Monthly Detail (84 Months)", expanded=False):
        _render_monthly_detail(monthly_projection)

def _render_kpi_dashboard(annual_summary):
    """Render KPI cards for Years 1, 3, and 7"""
    col1, col2, col3 = st.columns(3)

    year1 = annual_summary[annual_summary['year'] == 1].iloc[0]
    year3 = annual_summary[annual_summary['year'] == 3].iloc[0] if len(annual_summary) >= 3 else year1
    year7 = annual_summary[annual_summary['year'] == 7].iloc[0] if len(annual_summary) >= 7 else year1

    with col1:
        st.markdown("#### Year 1 (Lease-Up)")
        st.metric("Total Revenue", f"${year1['total_revenue']:,.0f}")
        st.metric("NOI", f"${year1['noi']:,.0f}")
        st.metric("Avg Occupancy", f"{year1['occupancy_pct']:.1%}")
        st.metric("DSCR", f"{year1['dscr']:.2f}x")

    with col2:
        st.markdown("#### Year 3 (Stabilized)")
        st.metric("Total Revenue", f"${year3['total_revenue']:,.0f}",
                 delta=f"+${year3['total_revenue'] - year1['total_revenue']:,.0f}")
        st.metric("NOI", f"${year3['noi']:,.0f}",
                 delta=f"+${year3['noi'] - year1['noi']:,.0f}")
        st.metric("Avg Occupancy", f"{year3['occupancy_pct']:.1%}",
                 delta=f"+{(year3['occupancy_pct'] - year1['occupancy_pct']):.1%}")
        st.metric("Cap Rate", f"{year3['cap_rate']:.2%}")

    with col3:
        st.markdown("#### Year 7 (Mature)")
        st.metric("Total Revenue", f"${year7['total_revenue']:,.0f}",
                 delta=f"+${year7['total_revenue'] - year3['total_revenue']:,.0f}")
        st.metric("NOI", f"${year7['noi']:,.0f}",
                 delta=f"+${year7['noi'] - year3['noi']:,.0f}")
        st.metric("Cash-on-Cash", f"{year7['cash_on_cash']:.2%}")
        st.metric("Cumulative CF", f"${annual_summary['levered_cash_flow'].sum():,.0f}")

def _render_leaseup_chart(monthly_projection):
    """Render interactive lease-up curve"""
    fig = go.Figure()

    # Occupancy line
    fig.add_trace(go.Scatter(
        x=monthly_projection['date'],
        y=monthly_projection['occupancy_pct'] * 100,
        mode='lines',
        name='Actual Occupancy',
        line=dict(color='#667eea', width=3),
        fill='tozeroy',
        fillcolor='rgba(102, 126, 234, 0.1)'
    ))

    # Target line
    fig.add_trace(go.Scatter(
        x=monthly_projection['date'],
        y=monthly_projection['target_occupancy'] * 100,
        mode='lines',
        name='Target Occupancy',
        line=dict(color='#764ba2', width=2, dash='dash')
    ))

    fig.update_layout(
        title="Occupancy Ramp-Up Over 84 Months",
        xaxis_title="Date",
        yaxis_title="Occupancy %",
        hovermode='x unified',
        height=400
    )

    st.plotly_chart(fig, width='stretch')

def _render_projection_table(annual_summary):
    """Render main projection table with expand/collapse sections"""

    # Prepare display dataframe
    display_df = _prepare_projection_display(annual_summary)

    # Render with tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Summary", "💵 Revenue Detail", "💳 Expense Detail", "🏦 Debt & Returns"])

    with tab1:
        _render_summary_section(display_df)

    with tab2:
        _render_revenue_section(display_df)

    with tab3:
        _render_expense_section(display_df)

    with tab4:
        _render_debt_section(display_df)

def _prepare_projection_display(annual_summary):
    """Prepare annual summary for display with formatting"""
    df = annual_summary.copy()

    # Round and format as needed (keep as numbers for now, format in display)
    return df

def _render_summary_section(df):
    """Render summary metrics table with years as columns"""
    st.markdown("#### High-Level Performance")

    # Create transposed table: metrics as rows, years as columns
    summary_data = {
        'Metric': [
            'Total Revenue',
            'Total Expenses',
            'NOI',
            'Debt Service',
            'Levered CF',
            'DSCR',
            'Avg Occ %'
        ]
    }

    # Add each year as a column
    for _, row in df.iterrows():
        year_label = f"Year {int(row['year'])}"
        summary_data[year_label] = [
            f"${row['total_revenue']:,.0f}",
            f"${row['total_expenses']:,.0f}",
            f"${row['noi']:,.0f}",
            f"${row['debt_service']:,.0f}",
            f"${row['levered_cash_flow']:,.0f}",
            f"{row['dscr']:.2f}x",
            f"{row['occupancy_pct']:.1%}"
        ]

    st.dataframe(pd.DataFrame(summary_data), width='stretch', hide_index=True)

def _render_revenue_section(df):
    """Render detailed revenue breakdown with years as columns"""
    st.markdown("#### Revenue Breakdown")

    # Create transposed table
    revenue_data = {
        'Revenue Item': [
            'Rental Income',
            'Discounts',
            'Write-offs',
            'Net Rental Income',
            'Ancillary Income',
            'Total Revenue',
            'Avg Rate ($/SF)'
        ]
    }

    # Add each year as a column
    for _, row in df.iterrows():
        year_label = f"Year {int(row['year'])}"
        revenue_data[year_label] = [
            f"${row['rental_income']:,.0f}",
            f"${row['discounts']:,.0f}",
            f"${row['writeoffs']:,.0f}",
            f"${row['net_rental_income']:,.0f}",
            f"${row['ancillary_income']:,.0f}",
            f"${row['total_revenue']:,.0f}",
            f"${row['in_place_rate_psf_annual']:.2f}"
        ]

    st.dataframe(pd.DataFrame(revenue_data), width='stretch', hide_index=True)

    # Revenue composition chart
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Net Rental Income', x=df['year'], y=df['net_rental_income']))
    fig.add_trace(go.Bar(name='Ancillary Income', x=df['year'], y=df['ancillary_income']))
    fig.update_layout(barmode='stack', title='Revenue Composition by Year', height=300)
    st.plotly_chart(fig, width='stretch')

def _render_expense_section(df):
    """Render detailed expense breakdown with years as columns"""
    st.markdown("#### Expense Breakdown")

    # Create transposed table
    expense_data = {
        'Expense Category': [
            'Payroll',
            'Utilities',
            'Operating Expenses',
            'Repairs & Maintenance',
            'Marketing',
            'Property Taxes',
            'Insurance',
            'Management Fees',
            'Total Expenses'
        ]
    }

    # Add each year as a column
    for _, row in df.iterrows():
        year_label = f"Year {int(row['year'])}"
        expense_data[year_label] = [
            f"${row['payroll']:,.0f}",
            f"${row['utilities']:,.0f}",
            f"${row['operating_expenses']:,.0f}",
            f"${row['repairs_maintenance']:,.0f}",
            f"${row['marketing']:,.0f}",
            f"${row['property_taxes']:,.0f}",
            f"${row['insurance']:,.0f}",
            f"${row['management_fee']:,.0f}",
            f"${row['total_expenses']:,.0f}"
        ]

    st.dataframe(pd.DataFrame(expense_data), width='stretch', hide_index=True)

    # Expense composition chart
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Payroll', x=df['year'], y=df['payroll']))
    fig.add_trace(go.Bar(name='Utilities', x=df['year'], y=df['utilities']))
    fig.add_trace(go.Bar(name='Operating', x=df['year'], y=df['operating_expenses']))
    fig.add_trace(go.Bar(name='R&M', x=df['year'], y=df['repairs_maintenance']))
    fig.add_trace(go.Bar(name='Taxes', x=df['year'], y=df['property_taxes']))
    fig.add_trace(go.Bar(name='Insurance', x=df['year'], y=df['insurance']))
    fig.update_layout(barmode='stack', title='Expense Composition by Year', height=300)
    st.plotly_chart(fig, width='stretch')

def _render_debt_section(df):
    """Render debt and return metrics with years as columns"""
    st.markdown("#### Debt Service & Returns")

    # Create transposed table
    debt_data = {
        'Metric': [
            'Ending Loan Balance',
            'Interest Payment',
            'Principal Payment',
            'Total Debt Service',
            'DSCR',
            'Cap Rate',
            'Cash-on-Cash Return'
        ]
    }

    # Add each year as a column
    for _, row in df.iterrows():
        year_label = f"Year {int(row['year'])}"
        debt_data[year_label] = [
            f"${row.get('ending_loan_balance', 0):,.0f}",
            f"${row['interest_payment']:,.0f}",
            f"${row['principal_payment']:,.0f}",
            f"${row['debt_service']:,.0f}",
            f"{row['dscr']:.2f}x",
            f"{row['cap_rate']:.2%}",
            f"{row['cash_on_cash']:.2%}"
        ]

    st.dataframe(pd.DataFrame(debt_data), width='stretch', hide_index=True)

    # Returns chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(name='Cap Rate', x=df['year'], y=df['cap_rate']*100, mode='lines+markers'))
    fig.add_trace(go.Scatter(name='Cash-on-Cash', x=df['year'], y=df['cash_on_cash']*100, mode='lines+markers'))
    fig.update_layout(title='Investment Returns Over Time', yaxis_title='%', height=300)
    st.plotly_chart(fig, width='stretch')

def _render_monthly_detail(monthly_projection):
    """Render monthly detail table with dates as columns"""
    st.markdown("#### Full Monthly Projection (84 Months)")

    try:
        # Create transposed table: metrics as rows, months as columns
        monthly_data = {
            'Metric': [
                'Move-Ins',
                'Move-Outs',
                'Occupied Units',
                'Occupancy %',
                'Rental Income',
                'Total Expenses',
                'NOI',
                'Levered CF',
                'DSCR'
            ]
        }

        # Add each month as a column
        for _, row in monthly_projection.iterrows():
            month_label = pd.to_datetime(row['date']).strftime('%Y-%m')
            monthly_data[month_label] = [
                f"{float(row['rentals']):.1f}",
                f"{float(row['vacates']):.1f}",
                f"{float(row['ending_occupied_units']):.0f}",
                f"{float(row['occupancy_pct']):.1%}",
                f"${float(row['rental_income']):,.0f}",
                f"${float(row['total_expenses']):,.0f}",
                f"${float(row['noi']):,.0f}",
                f"${float(row['levered_cash_flow']):,.0f}",
                f"{float(row['dscr']):.2f}x" if float(row['dscr']) > 0 else "N/A"
            ]

        monthly_df = pd.DataFrame(monthly_data)

        # Display with horizontal scrolling enabled
        st.dataframe(monthly_df, width='stretch', hide_index=True, height=400)

        st.info("💡 Scroll horizontally to view all 84 months")

    except Exception as e:
        st.error(f"Error rendering monthly detail: {str(e)}")
        st.write("Available columns:", list(monthly_projection.columns))
        st.write("Data shape:", monthly_projection.shape)
        import traceback
        st.code(traceback.format_exc())


def render_feasibility_score(score_data):
    """
    Render feasibility score and recommendation

    Args:
        score_data: Dict with keys:
            - score: int (0-100)
            - decision: str ('PURSUE', 'CAUTION', 'PASS')
            - breakdown: dict of category scores
            - key_risks: list of str
            - key_strengths: list of str
    """
    score = score_data['score']
    decision = score_data['decision']

    # Color based on decision
    if decision == 'PURSUE':
        color = '#10b981'  # Green
        emoji = '✅'
    elif decision == 'CAUTION':
        color = '#f59e0b'  # Orange
        emoji = '⚠️'
    else:
        color = '#ef4444'  # Red
        emoji = '❌'

    st.markdown(f"""
    <div style="background: {color}; padding: 40px; border-radius: 10px; text-align: center; margin-bottom: 30px;">
        <div style="font-size: 48px; margin-bottom: 10px;">{emoji}</div>
        <h1 style="color: white; margin: 0; font-size: 48px;">{score}/100</h1>
        <h2 style="color: white; margin: 10px 0; font-weight: normal;">Recommendation: {decision}</h2>
    </div>
    """, unsafe_allow_html=True)

    # Breakdown
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 💪 Key Strengths")
        for strength in score_data.get('key_strengths', []):
            st.markdown(f"- {strength}")

    with col2:
        st.markdown("### ⚠️ Key Risks")
        for risk in score_data.get('key_risks', []):
            st.markdown(f"- {risk}")

    # Score breakdown
    st.markdown("### 📊 Score Breakdown")
    breakdown_df = pd.DataFrame([
        {'Category': k, 'Score': v['score'], 'Max': v['max'], 'Weight': f"{v['score']/v['max']*100:.0f}%"}
        for k, v in score_data.get('breakdown', {}).items()
    ])
    st.dataframe(breakdown_df, width='stretch', hide_index=True)
