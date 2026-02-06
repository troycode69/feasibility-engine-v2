"""
Professional PDF Report Generator
Creates McKinley-level institutional quality feasibility study reports (20-30 pages)
Uses WeasyPrint for HTML → PDF conversion with professional styling
Integrates matplotlib charts for visual analysis
"""

from weasyprint import HTML, CSS
from datetime import datetime
from typing import Dict, List, Optional
import base64
import os
import io

# Import chart generator functions (including 6 new chart types)
try:
    from src.chart_generator import (
        # Original 8 charts
        generate_noi_waterfall,
        generate_occupancy_curve,
        generate_sensitivity_tornado,
        generate_scoring_radar,
        generate_scenario_comparison,
        generate_competitor_scatter,
        generate_sf_per_capita_comparison,
        generate_cash_flow_chart,
        # New 6 charts (premium visualizations)
        generate_market_cycle_gauge,
        generate_absorption_timeline,
        generate_rate_heatmap,
        generate_pipeline_timeline,
        generate_demand_driver_pie,
        generate_risk_return_scatter
    )
    CHARTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Chart imports failed: {e}")
    CHARTS_AVAILABLE = False
    # Define stub functions if charts not available
    generate_noi_waterfall = None
    generate_occupancy_curve = None
    generate_sensitivity_tornado = None
    generate_scoring_radar = None
    generate_scenario_comparison = None
    generate_competitor_scatter = None
    generate_sf_per_capita_comparison = None
    generate_cash_flow_chart = None
    generate_market_cycle_gauge = None
    generate_absorption_timeline = None
    generate_rate_heatmap = None
    generate_pipeline_timeline = None
    generate_demand_driver_pie = None
    generate_risk_return_scatter = None


class PDFReportGenerator:
    """
    Generates comprehensive feasibility study reports in PDF format
    """

    def __init__(self):
        self.brand_color = "#0C2340"  # STORAGE OS navy
        self.accent_color = "#F39C12"  # STORAGE OS orange

    def _get_css_styles(self) -> str:
        """Professional CSS styling for the PDF report"""
        return """
        @page {
            size: letter;
            margin: 0.75in;
            @top-center {
                content: "STORAGE OS Feasibility Study";
                font-size: 10pt;
                color: #666;
            }
            @bottom-right {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 9pt;
                color: #666;
            }
        }

        body {
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #0C2340;
        }

        h1 {
            font-size: 24pt;
            font-weight: 700;
            color: #0C2340;
            margin-top: 0;
            border-bottom: 3px solid #F39C12;
            padding-bottom: 10px;
        }

        h2 {
            font-size: 18pt;
            font-weight: 600;
            color: #0C2340;
            margin-top: 30px;
            border-left: 5px solid #F39C12;
            padding-left: 15px;
        }

        h3 {
            font-size: 14pt;
            font-weight: 600;
            color: #0C2340;
            margin-top: 20px;
        }

        .cover-page {
            text-align: center;
            padding-top: 200px;
        }

        .cover-title {
            font-size: 36pt;
            font-weight: 700;
            color: #0C2340;
            margin-bottom: 20px;
        }

        .cover-subtitle {
            font-size: 18pt;
            color: #666;
            margin-bottom: 10px;
        }

        .cover-address {
            font-size: 16pt;
            color: #0C2340;
            margin: 30px 0;
        }

        .cover-date {
            font-size: 12pt;
            color: #666;
            margin-top: 50px;
        }

        .executive-summary {
            background: linear-gradient(135deg, #0C2340 0%, #1a3a5c 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin: 20px 0;
        }

        .recommendation-box {
            background: #f8f9fa;
            border-left: 5px solid #F39C12;
            padding: 20px;
            margin: 20px 0;
        }

        .score-card {
            text-align: center;
            background: linear-gradient(135deg, #0C2340 0%, #1a3a5c 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin: 20px 0;
        }

        .score-card h1 {
            color: white;
            border: none;
            font-size: 48pt;
            margin: 0;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 10pt;
        }

        th {
            background-color: #0C2340;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }

        td {
            padding: 10px 12px;
            border-bottom: 1px solid #ddd;
        }

        tr:nth-child(even) {
            background-color: #f8f9fa;
        }

        .metric-box {
            display: inline-block;
            background: white;
            border: 1px solid #ddd;
            border-left: 5px solid #F39C12;
            padding: 15px;
            margin: 10px;
            width: 200px;
        }

        .metric-label {
            font-size: 9pt;
            color: #666;
            text-transform: uppercase;
        }

        .metric-value {
            font-size: 20pt;
            font-weight: 600;
            color: #0C2340;
        }

        .page-break {
            page-break-after: always;
        }

        .ai-badge {
            display: inline-block;
            background: #28a745;
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 9pt;
            font-weight: 600;
            margin-left: 10px;
        }

        .warning-box {
            background: #fff3cd;
            border-left: 5px solid #ffc107;
            padding: 15px;
            margin: 15px 0;
        }

        .footer-note {
            font-size: 9pt;
            color: #666;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }

        .chart-container {
            text-align: center;
            margin: 25px 0;
            page-break-inside: avoid;
        }

        .chart-container img {
            max-width: 100%;
            height: auto;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
        }

        .chart-title {
            font-size: 12pt;
            font-weight: 600;
            color: #0C2340;
            margin-bottom: 10px;
        }

        .chart-caption {
            font-size: 9pt;
            color: #666;
            margin-top: 8px;
            font-style: italic;
        }

        .chart-row {
            display: flex;
            justify-content: space-between;
            gap: 20px;
            margin: 20px 0;
        }

        .chart-half {
            width: 48%;
            text-align: center;
        }

        .chart-half img {
            max-width: 100%;
            height: auto;
        }

        .scenario-table {
            margin: 20px 0;
        }

        .scenario-table th {
            background-color: #0C2340;
            color: white;
        }

        .scenario-conservative {
            background-color: #fff3cd !important;
        }

        .scenario-base {
            background-color: #d4edda !important;
        }

        .scenario-aggressive {
            background-color: #cce5ff !important;
        }
        """

    def generate_cover_page(self, address: str, report_date: str) -> str:
        """Generate cover page HTML"""
        return f"""
        <div class="cover-page">
            <div class="cover-title">FEASIBILITY STUDY</div>
            <div class="cover-subtitle">Self-Storage Development Analysis</div>
            <div class="cover-address">{address}</div>
            <div class="cover-date">
                Report Date: {report_date}<br>
                Generated by STORAGE OS<br>
                AI-Powered Market Intelligence
            </div>
        </div>
        <div class="page-break"></div>
        """

    def generate_executive_summary(self, data: Dict) -> str:
        """Generate executive summary section"""
        recommendation = data.get('recommendation', {})
        decision = recommendation.get('decision', 'PENDING')
        confidence = recommendation.get('confidence', 'N/A')
        market_score = data.get('market_score', 0)
        score_breakdown = data.get('score_breakdown', {})

        decision_color = {
            'PURSUE': '#28a745',
            'CAUTION': '#ffc107',
            'PASS': '#dc3545'
        }.get(decision, '#666')

        # Get individual category scores
        demo_score = score_breakdown.get('demographics', {}).get('score', 0)
        supply_score = score_breakdown.get('supply', {}).get('score', 0)
        site_score = score_breakdown.get('site', {}).get('score', 0)
        comp_score = score_breakdown.get('competitor', {}).get('score', 0)
        econ_score = score_breakdown.get('economic', {}).get('score', 0)

        # Get key metrics
        demographics = data.get('scorer_inputs', {}).get('demographics', {})
        supply = data.get('scorer_inputs', {}).get('supply', {})
        comp_stats = data.get('comp_stats', {})

        population = demographics.get('population', 0)
        income = demographics.get('income', 0)
        sf_per_capita = supply.get('sf_per_capita', 0)
        occupancy = supply.get('occupancy', 0)
        comp_count = comp_stats.get('count', 0)

        return f"""
        <h1>EXECUTIVE SUMMARY</h1>

        <div class="score-card">
            <h1>{market_score}/100</h1>
            <p style="margin: 10px 0 0 0; font-size: 18pt;">FEASIBILITY SCORE</p>
        </div>

        <div class="recommendation-box" style="border-left-color: {decision_color};">
            <h2 style="border: none; margin-top: 0; color: {decision_color};">
                RECOMMENDATION: {decision}
            </h2>
            <p style="font-size: 12pt; margin: 10px 0;">
                <strong>Confidence Level:</strong> {confidence}
            </p>
            <p>{recommendation.get('narrative', 'Detailed analysis follows.')}</p>
        </div>

        <h3>Market Overview</h3>
        <p>This feasibility study evaluates the self-storage development opportunity at the subject property using the
        industry-standard Allspace Storage Feasibility Rubric. The analysis incorporates AI-powered data collection from live APIs,
        competitive intelligence, and demographic research to provide an objective, data-driven assessment.</p>

        <h3>Category Score Breakdown</h3>
        <table style="margin: 20px 0;">
            <tr>
                <th>Category</th>
                <th>Score</th>
                <th>Max</th>
                <th>Performance</th>
                <th>Key Insight</th>
            </tr>
            <tr style="background: {'#e8f5e9' if demo_score >= 20 else '#fff3cd' if demo_score >= 15 else '#ffebee'};">
                <td><strong>Demographics</strong></td>
                <td>{demo_score}</td>
                <td>25</td>
                <td>{demo_score/25*100:.0f}%</td>
                <td>{population:,} population, ${income:,} median income</td>
            </tr>
            <tr style="background: {'#e8f5e9' if supply_score >= 20 else '#fff3cd' if supply_score >= 15 else '#ffebee'};">
                <td><strong>Supply/Demand</strong></td>
                <td>{supply_score}</td>
                <td>25</td>
                <td>{supply_score/25*100:.0f}%</td>
                <td>{sf_per_capita:.2f} SF/capita, {occupancy:.0f}% avg occupancy</td>
            </tr>
            <tr style="background: {'#e8f5e9' if site_score >= 20 else '#fff3cd' if site_score >= 15 else '#ffebee'};">
                <td><strong>Site Quality</strong></td>
                <td>{site_score}</td>
                <td>25</td>
                <td>{site_score/25*100:.0f}%</td>
                <td>Visibility, access, zoning, and size evaluation</td>
            </tr>
            <tr style="background: {'#e8f5e9' if comp_score >= 12 else '#fff3cd' if comp_score >= 9 else '#ffebee'};">
                <td><strong>Competition</strong></td>
                <td>{comp_score}</td>
                <td>15</td>
                <td>{comp_score/15*100:.0f}%</td>
                <td>{comp_count} competitors within 3-mile radius</td>
            </tr>
            <tr style="background: {'#e8f5e9' if econ_score >= 8 else '#fff3cd' if econ_score >= 6 else '#ffebee'};">
                <td><strong>Economic</strong></td>
                <td>{econ_score}</td>
                <td>10</td>
                <td>{econ_score/10*100:.0f}%</td>
                <td>Employment, business growth, stability</td>
            </tr>
            <tr style="background: #0C2340; color: white; font-weight: 600;">
                <td><strong>TOTAL SCORE</strong></td>
                <td><strong>{market_score}</strong></td>
                <td><strong>100</strong></td>
                <td><strong>{market_score}%</strong></td>
                <td><strong>Overall Feasibility</strong></td>
            </tr>
        </table>

        <h3>Key Investment Highlights</h3>
        <ul>
            <li><strong>Market Score:</strong> {market_score}/100 points represents {'an excellent opportunity' if market_score >= 80 else 'a strong opportunity' if market_score >= 70 else 'a viable opportunity' if market_score >= 60 else 'marginal feasibility'}</li>
            <li><strong>Supply Dynamics:</strong> At {sf_per_capita:.2f} SF/capita, market is {'significantly undersupplied' if sf_per_capita <= 5.5 else 'balanced with room for growth' if sf_per_capita <= 7.5 else 'approaching saturation'}</li>
            <li><strong>Competitive Position:</strong> {comp_count} existing facilities with {occupancy:.0f}% average occupancy {'signals strong demand' if occupancy >= 88 else 'indicates stable market' if occupancy >= 82 else 'suggests competitive challenges'}</li>
            <li><strong>AI-Powered Analysis:</strong> Site visibility, demographics, economic indicators, and competitor data verified via live APIs for maximum accuracy</li>
        </ul>

        <h3>Critical Success Factors</h3>
        <p><strong>Strengths:</strong> {'Strong demographics and undersupplied market create favorable entry conditions.' if demo_score >= 18 and supply_score >= 18 else 'Balanced market fundamentals support careful execution.' if market_score >= 65 else 'Market presents challenges that require superior execution and positioning.'}</p>

        <p><strong>Risks:</strong> {'Primary risks include execution, lease-up timeline, and potential pipeline competition.' if market_score >= 75 else 'Competitive intensity and market saturation present material risks to absorption and pricing.' if comp_count >= 7 or sf_per_capita >= 8.5 else 'Market fundamentals require careful underwriting and conservative assumptions.'}</p>

        <div class="page-break"></div>
        """

    def generate_location_summary(self, data: Dict) -> str:
        """Generate location and site summary"""
        address = data.get('address', 'N/A')
        lat = data.get('lat', 0)
        lon = data.get('lon', 0)
        context = data.get('location_context', '')
        site = data.get('scorer_inputs', {}).get('site', {})
        score_breakdown = data.get('score_breakdown', {}).get('site', {})

        visibility = site.get('visibility', 'N/A')
        access = site.get('access', 'N/A')
        zoning = site.get('zoning', 'N/A')
        size = site.get('size', 'N/A')

        site_score = score_breakdown.get('score', 0)
        site_max = score_breakdown.get('max', 25)

        # Assessment narrative
        assessment = ""
        if site_score >= 20:
            assessment = "EXCELLENT - Superior site characteristics with optimal visibility, access, and development potential."
        elif site_score >= 15:
            assessment = "GOOD - Strong site attributes support successful self-storage operation."
        elif site_score >= 10:
            assessment = "FAIR - Acceptable site but may require additional marketing or operational considerations."
        else:
            assessment = "WEAK - Site limitations may impede visibility, access, or development efficiency."

        return f"""
        <h1>SITE & LOCATION ANALYSIS</h1>

        <div class="recommendation-box">
            <h3 style="margin-top: 0;">Score: {site_score}/{site_max} points</h3>
            <p><strong>Assessment:</strong> {assessment}</p>
        </div>

        <h3>Subject Property</h3>
        <p><strong>Address:</strong> {address}</p>
        <p><strong>Coordinates:</strong> {lat:.6f}, {lon:.6f}</p>
        {f'<p><strong>Location Context:</strong> {context}</p>' if context else ''}

        <h3>Site Characteristics</h3>
        <table>
            <tr>
                <th>Factor</th>
                <th>Rating</th>
                <th>Benchmark</th>
                <th>Impact</th>
            </tr>
            <tr>
                <td><strong>Visibility</strong></td>
                <td>{visibility}</td>
                <td>Excellent (Preferred)<br>Good (Acceptable)<br>Moderate/Poor (Challenges)</td>
                <td>{'Prime highway/arterial frontage maximizes brand exposure and walk-in traffic' if visibility == 'Excellent' else 'Good street presence supports customer acquisition' if visibility == 'Good' else 'Limited visibility requires stronger digital marketing and signage'}</td>
            </tr>
            <tr>
                <td><strong>Access</strong></td>
                <td>{access}</td>
                <td>Direct (Ideal)<br>Easy (Good)<br>Moderate/Difficult (Issues)</td>
                <td>{'Direct highway/arterial access reduces customer friction and supports premium rates' if access == 'Direct' else 'Easy ingress/egress supports customer convenience' if access == 'Easy' else 'Access challenges may deter customers, especially commercial users with large vehicles'}</td>
            </tr>
            <tr>
                <td><strong>Zoning</strong></td>
                <td>{zoning}</td>
                <td>Approved (No risk)<br>Likely (Low risk)<br>Uncertain/Prohibited (High risk)</td>
                <td>{'Pre-approved zoning eliminates entitlement risk and accelerates timeline' if zoning == 'Approved' else 'Zoning appears favorable but requires verification with local authorities' if zoning == 'Likely' else 'Zoning uncertainty creates significant development risk and potential delays'}</td>
            </tr>
            <tr>
                <td><strong>Size Adequacy</strong></td>
                <td>{size}</td>
                <td>Ideal (>3 acres)<br>Adequate (2-3 acres)<br>Marginal (<2 acres)</td>
                <td>{'Sufficient land area supports phased expansion and optimal unit mix' if size == 'Ideal' else 'Adequate size for single-phase development' if size == 'Adequate' else 'Limited size may constrain unit mix and operational efficiency'}</td>
            </tr>
        </table>

        <h3>Site Selection Best Practices</h3>
        <p><strong>Visibility:</strong> Self-storage is a convenience-driven product. High-visibility sites on major arterials
        or highways benefit from brand awareness and impulse inquiries. Poor visibility requires heavier marketing investment.</p>

        <p><strong>Access:</strong> Customers moving and businesses needing frequent access prefer easy ingress/egress.
        Sites requiring multiple turns or difficult navigation may underperform, particularly for commercial users.</p>

        <p><strong>Zoning:</strong> Self-storage typically requires commercial or industrial zoning. Conditional use permits (CUPs)
        add risk and timeline. Pre-approved sites eliminate entitlement uncertainty.</p>

        <p><strong>Size:</strong> Industry best practice suggests 2.5-3+ acres for optimal development efficiency and unit mix flexibility.
        Smaller sites may require multi-story construction (higher costs) or compromise on amenities.</p>

        <div class="page-break"></div>
        """

    def generate_demographics_section(self, data: Dict) -> str:
        """Generate demographics analysis section"""
        demographics = data.get('scorer_inputs', {}).get('demographics', {})
        score_breakdown = data.get('score_breakdown', {}).get('demographics', {})

        population = demographics.get('population', 0)
        income = demographics.get('income', 0)
        growth = demographics.get('growth', 0)
        renter_pct = demographics.get('renter_pct', 0)
        age_pct = demographics.get('age_pct', 0)

        demo_score = score_breakdown.get('score', 0)
        demo_max = score_breakdown.get('max', 25)

        # Assessment narrative
        assessment = ""
        if demo_score >= 20:
            assessment = "EXCELLENT - This market demonstrates strong demographic fundamentals with robust population density, above-average incomes, and healthy growth trends."
        elif demo_score >= 15:
            assessment = "GOOD - Demographics support self-storage demand with adequate population and income levels."
        elif demo_score >= 10:
            assessment = "FAIR - Demographics are acceptable but may present challenges for premium pricing or rapid absorption."
        else:
            assessment = "WEAK - Demographic indicators suggest limited market depth and potential demand constraints."

        return f"""
        <h1>DEMOGRAPHICS ANALYSIS</h1>

        <div class="recommendation-box">
            <h3 style="margin-top: 0;">Score: {demo_score}/{demo_max} points</h3>
            <p><strong>Assessment:</strong> {assessment}</p>
        </div>

        <h3>Trade Area Profile (3-Mile Radius)</h3>
        <p>The following demographic indicators were analyzed for the subject property's primary trade area:</p>

        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Industry Benchmark</th>
                <th>Analysis</th>
            </tr>
            <tr>
                <td><strong>Total Population</strong></td>
                <td>{population:,}</td>
                <td>≥75,000 (Ideal)<br>50,000-74,999 (Good)<br>35,000-49,999 (Fair)</td>
                <td>{'Strong market depth' if population >= 75000 else 'Adequate demand base' if population >= 50000 else 'Limited market size'}</td>
            </tr>
            <tr>
                <td><strong>Median Household Income</strong></td>
                <td>${income:,}</td>
                <td>≥$75,000 (Ideal)<br>$60,000-$74,999 (Good)<br>$50,000-$59,999 (Fair)</td>
                <td>{'Premium pricing supported' if income >= 75000 else 'Mid-market positioning' if income >= 60000 else 'Value-oriented pricing recommended'}</td>
            </tr>
            <tr>
                <td><strong>Annual Growth Rate</strong></td>
                <td>{growth:.1f}%</td>
                <td>≥3.0% (Excellent)<br>2.0-2.9% (Good)<br>1.0-1.9% (Moderate)</td>
                <td>{'High-growth market with expanding demand' if growth >= 3.0 else 'Stable growth trajectory' if growth >= 2.0 else 'Mature, stable market'}</td>
            </tr>
            <tr>
                <td><strong>Renter-Occupied Housing</strong></td>
                <td>{renter_pct:.0f}%</td>
                <td>≥50% (Excellent)<br>40-49% (Good)<br>30-39% (Fair)</td>
                <td>{'High renter concentration - prime demographic' if renter_pct >= 50 else 'Good renter penetration' if renter_pct >= 40 else 'Mixed homeowner/renter market'}</td>
            </tr>
            <tr>
                <td><strong>Age 25-54 Population</strong></td>
                <td>{age_pct:.0f}%</td>
                <td>≥45% (Excellent)<br>40-44% (Good)<br>35-39% (Fair)</td>
                <td>{'Optimal age distribution for storage demand' if age_pct >= 45 else 'Strong working-age population' if age_pct >= 40 else 'Adequate age demographics'}</td>
            </tr>
        </table>

        <h3>Market Implications</h3>
        <p><strong>Demand Drivers:</strong> Self-storage demand is driven by life events (moving, downsizing, divorce, death) and business needs.
        The 25-54 age cohort represents the prime demographic due to higher mobility, career transitions, and accumulation of possessions.</p>

        <p><strong>Income Correlation:</strong> Higher median incomes typically correlate with higher unit penetration rates (units per capita)
        and premium pricing power. This market's income profile {'supports premium positioning' if income >= 75000 else 'indicates mid-market positioning' if income >= 60000 else 'suggests value-oriented strategy'}.</p>

        <div class="page-break"></div>
        """

    def generate_supply_demand_section(self, data: Dict) -> str:
        """Generate supply & demand analysis"""
        supply = data.get('scorer_inputs', {}).get('supply', {})
        score_breakdown = data.get('score_breakdown', {}).get('supply', {})
        demographics = data.get('scorer_inputs', {}).get('demographics', {})

        sf_per_capita = supply.get('sf_per_capita', 0)
        occupancy = supply.get('occupancy', 0)
        trend = supply.get('trend', 'N/A')
        pipeline = supply.get('pipeline', 0)

        supply_score = score_breakdown.get('score', 0)
        supply_max = score_breakdown.get('max', 25)

        population = demographics.get('population', 0)
        total_supply_sf = sf_per_capita * population if sf_per_capita and population else 0

        # Assessment narrative
        assessment = ""
        if supply_score >= 20:
            assessment = "EXCELLENT - Market shows strong undersupply with high occupancy. New supply will be readily absorbed."
        elif supply_score >= 15:
            assessment = "GOOD - Supply-demand fundamentals support new development with manageable competition."
        elif supply_score >= 10:
            assessment = "FAIR - Market is balanced. New supply must be well-positioned to capture share."
        else:
            assessment = "WEAK - Oversupply concerns or weak absorption trends may impede performance."

        return f"""
        <h1>SUPPLY & DEMAND ANALYSIS</h1>

        <div class="recommendation-box">
            <h3 style="margin-top: 0;">Score: {supply_score}/{supply_max} points</h3>
            <p><strong>Assessment:</strong> {assessment}</p>
        </div>

        <h3>Current Market Supply</h3>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Industry Benchmark</th>
                <th>Analysis</th>
            </tr>
            <tr>
                <td><strong>SF Per Capita</strong></td>
                <td>{sf_per_capita:.2f} SF/person</td>
                <td>≤4.0 (Undersupplied)<br>4.1-5.5 (Tight)<br>5.6-7.0 (Balanced)<br>7.1-8.5 (Saturating)<br>>8.5 (Oversupplied)</td>
                <td>{'Severely undersupplied - excellent opportunity' if sf_per_capita <= 4.0 else 'Undersupplied - favorable entry' if sf_per_capita <= 5.5 else 'Approaching equilibrium' if sf_per_capita <= 7.0 else 'Near saturation - careful positioning required' if sf_per_capita <= 8.5 else 'Oversupplied - high risk'}</td>
            </tr>
            <tr>
                <td><strong>Estimated Total Supply</strong></td>
                <td>{total_supply_sf:,.0f} SF</td>
                <td>Varies by population</td>
                <td>Based on {sf_per_capita:.2f} SF/person × {population:,} population</td>
            </tr>
            <tr>
                <td><strong>Average Occupancy</strong></td>
                <td>{occupancy:.0f}%</td>
                <td>≥90% (Excellent)<br>85-89% (Good)<br>80-84% (Fair)<br>75-79% (Weak)</td>
                <td>{'Excellent - high demand pressure' if occupancy >= 90 else 'Strong occupancy indicates healthy demand' if occupancy >= 85 else 'Moderate occupancy - stable market' if occupancy >= 80 else 'Below-average occupancy indicates soft demand or pricing issues'}</td>
            </tr>
            <tr>
                <td><strong>Absorption Trend</strong></td>
                <td>{trend}</td>
                <td>Strong (Preferred)<br>Moderate (Acceptable)<br>Weak (Caution)</td>
                <td>{'Market actively absorbing new supply' if trend == 'Strong' else 'Stable demand conditions' if trend == 'Moderate' else 'Sluggish absorption may extend lease-up'}</td>
            </tr>
            <tr>
                <td><strong>Pipeline SF Per Capita</strong></td>
                <td>{pipeline:.2f} SF/person</td>
                <td>≤0.5 (Minimal Risk)<br>0.5-1.0 (Moderate)<br>>1.0 (High Risk)</td>
                <td>{'Minimal competitive supply in pipeline' if pipeline <= 0.5 else 'Moderate future competition expected' if pipeline <= 1.0 else 'Significant pipeline may pressure rents and absorption'}</td>
            </tr>
        </table>

        <h3>Supply-Demand Equilibrium Analysis</h3>
        <p><strong>Industry Standard:</strong> The self-storage industry generally considers 8.0-9.0 SF per capita as "equilibrium."
        Markets below 8.0 SF/capita are typically undersupplied, while markets above 9.0 SF/capita may be oversupplied.</p>

        <p><strong>This Market:</strong> At {sf_per_capita:.2f} SF/capita, this market is
        {'significantly undersupplied, presenting a compelling opportunity for new supply' if sf_per_capita <= 5.5
         else 'approaching industry equilibrium levels but still shows favorable supply-demand dynamics' if sf_per_capita <= 7.5
         else 'at or above equilibrium, requiring careful site selection and differentiation to succeed'}.</p>

        <div class="warning-box" style="display: {'block' if occupancy < 85 or sf_per_capita > 8.5 else 'none'};">
            <p><strong>⚠️ Supply Risk Factors:</strong></p>
            <ul>
                {'<li>Below-average occupancy indicates soft demand or aggressive competition</li>' if occupancy < 85 else ''}
                {'<li>High SF/capita suggests potential oversupply - new supply must offer clear competitive advantages</li>' if sf_per_capita > 8.5 else ''}
                {'<li>Significant pipeline development will increase competition during lease-up period</li>' if pipeline > 1.0 else ''}
            </ul>
        </div>

        <div class="page-break"></div>
        """

    def generate_competitor_section(self, competitors: List[Dict], comp_stats: Dict, data: Dict) -> str:
        """
        Generate competitive landscape section with intelligent data synthesis.
        Merges Google Maps + TractIQ data into unified analysis.
        """
        from src.data_synthesis import synthesize_competitor_data, synthesize_rate_data

        competitor_inputs = data.get('scorer_inputs', {}).get('competitor', {})
        score_breakdown = data.get('score_breakdown', {}).get('competitor', {})

        comp_count = competitor_inputs.get('count', comp_stats.get('count', 0))
        comp_quality = competitor_inputs.get('quality', 'N/A')
        pricing_position = competitor_inputs.get('pricing', 'N/A')

        comp_score = score_breakdown.get('score', 0)
        comp_max = score_breakdown.get('max', 15)

        # === DATA SYNTHESIS: Merge Google Maps + TractIQ ===
        tractiq_data = data.get('pdf_ext_data', {})
        synthesis_result = synthesize_competitor_data(competitors, tractiq_data)

        unified_competitors = synthesis_result['unified_competitors']
        synthesis_stats = synthesis_result['synthesis_stats']
        market_insights = synthesis_result['market_insights']

        # Synthesize rate data from all sources
        rate_synthesis = synthesize_rate_data(competitors, tractiq_data)

        # Use synthesized metrics or fall back to original
        avg_occ = comp_stats.get('avg_occupancy', 0)
        avg_rate = rate_synthesis.get('market_avg_rate', comp_stats.get('avg_rate_10x10', 0))
        total_nrsf = comp_stats.get('total_nrsf', 0)

        # Assessment narrative
        assessment = ""
        if comp_score >= 12:
            assessment = "EXCELLENT - Limited competition with aging facilities presents clear opportunity for modern product."
        elif comp_score >= 9:
            assessment = "GOOD - Competitive environment is manageable with proper positioning and execution."
        elif comp_score >= 6:
            assessment = "FAIR - Moderate competition requires differentiation and competitive pricing."
        else:
            assessment = "CHALLENGING - Saturated market with strong competitors may limit pricing power and absorption."

        # Generate competitor rows from UNIFIED data (enriched with TractIQ)
        comp_rows = ""
        for i, comp in enumerate(unified_competitors[:20], 1):  # Show top 20 (more with TractIQ)
            # Get rate from multiple sources (prioritize TractIQ)
            rate = (comp.get('rate_10x10_tractiq') or
                    comp.get('rate_10x10_cc') or
                    comp.get('rate_10x10') or 0)

            # Get occupancy from multiple sources
            occupancy = (comp.get('occupancy_tractiq') or
                        comp.get('occupancy_pct') or
                        comp.get('occupancy') or 0)

            # Get NRSF
            nrsf = comp.get('nrsf_tractiq') or comp.get('nrsf', 0)

            # Data quality indicator
            data_sources = ', '.join(comp.get('data_sources', ['Unknown']))
            data_quality_icon = '✓✓' if 'TractIQ' in data_sources else '✓'

            comp_rows += f"""
            <tr style="background: {'#f0f9ff' if 'TractIQ' in data_sources else 'white'};">
                <td>{i}</td>
                <td>{comp.get('name', 'N/A')} <span style="color: #0066cc; font-size: 9pt;">{data_quality_icon}</span></td>
                <td>{comp.get('distance_miles', 0):.2f} mi</td>
                <td>{nrsf:,} SF</td>
                <td>${rate:.0f}</td>
                <td>{occupancy:.0f}%</td>
            </tr>
            """

        # Build data quality statement
        data_quality_statement = ""
        if synthesis_stats['tractiq_count'] > 0:
            data_quality_statement = f"""
            <div class="recommendation-box" style="background-color: #E3F2FD;">
                <h4 style="margin-top: 0; color: #1565C0;">📊 Data Synthesis Summary</h4>
                <p><strong>Multi-Source Intelligence:</strong> This analysis combines {synthesis_stats['google_maps_count']} competitors from Google Maps with {synthesis_stats['tractiq_count']} facilities from TractIQ data, resulting in {synthesis_stats['total_unique']} unique competitors. {synthesis_stats['enriched_count']} facilities have enhanced data from multiple sources.</p>
                <p><strong>Data Quality Score:</strong> {synthesis_stats['data_quality_score']}/100 (based on rate, occupancy, and unit count coverage)</p>
            </div>
            """

        # Build AI insights section
        insights_html = ""
        if market_insights:
            insights_html = "<h3>Market Intelligence Insights</h3><ul>"
            for insight in market_insights:
                insights_html += f"<li>{insight}</li>"
            insights_html += "</ul>"

        # Build rate analysis section
        rate_analysis_html = ""
        if rate_synthesis.get('available'):
            rate_range_low = rate_synthesis['rate_range_low']
            rate_range_high = rate_synthesis['rate_range_high']
            rate_median = rate_synthesis['market_median_rate']
            rate_spread = rate_range_high - rate_range_low

            rate_analysis_html = f"""
            <div class="recommendation-box">
                <h4 style="margin-top: 0;">💰 Market Rate Analysis (from {rate_synthesis['sample_size']} data points)</h4>
                <p><strong>Median Market Rate:</strong> ${rate_median}/month | <strong>Range:</strong> ${rate_range_low} - ${rate_range_high} (${rate_spread} spread)</p>
                <p><strong>Interpretation:</strong> {'Wide rate dispersion suggests opportunity for well-positioned facilities to command premium pricing.' if rate_spread > 50 else 'Tight rate clustering indicates competitive pricing pressure and limited pricing power.' if rate_spread < 25 else 'Moderate rate variation allows differentiation through location and amenities.'}</p>
            </div>
            """

        return f"""
        <h1>COMPETITIVE LANDSCAPE</h1>

        <div class="recommendation-box">
            <h3 style="margin-top: 0;">Score: {comp_score}/{comp_max} points</h3>
            <p><strong>Assessment:</strong> {assessment}</p>
        </div>

        {data_quality_statement}

        {insights_html}

        {rate_analysis_html}

        <h3>Competitive Market Summary</h3>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Industry Benchmark</th>
                <th>Analysis</th>
            </tr>
            <tr>
                <td><strong>Competitors (3mi)</strong></td>
                <td>{len(unified_competitors)}</td>
                <td>≤2 (Excellent)<br>3-4 (Good)<br>5-6 (Moderate)<br>≥7 (Saturated)</td>
                <td>{'Limited competition provides pricing power and market share opportunity' if len(unified_competitors) <= 2 else 'Healthy competitive balance' if len(unified_competitors) <= 4 else 'Moderate competition requires differentiation' if len(unified_competitors) <= 6 else 'Saturated market - superior product and marketing critical'}</td>
            </tr>
            <tr>
                <td><strong>Total Competitive Supply</strong></td>
                <td>{total_nrsf:,.0f} SF</td>
                <td>Varies by population</td>
                <td>Aggregate NRSF of identified competitors</td>
            </tr>
            <tr>
                <td><strong>Average Occupancy</strong></td>
                <td>{avg_occ:.0f}%</td>
                <td>≥90% (Strong Demand)<br>85-89% (Healthy)<br>80-84% (Moderate)<br><80% (Soft)</td>
                <td>{'Competitors are full - strong demand signal' if avg_occ >= 90 else 'Healthy occupancy indicates stable demand' if avg_occ >= 85 else 'Moderate occupancy - market is balanced' if avg_occ >= 80 else 'Below-average occupancy suggests pricing pressure or weak demand'}</td>
            </tr>
            <tr>
                <td><strong>Market Rate (10x10)</strong></td>
                <td>${avg_rate:.0f}/month</td>
                <td>Varies by market</td>
                <td>{'Synthesized from ' + str(rate_synthesis['sample_size']) + ' data points across all sources' if rate_synthesis.get('available') else 'Market street rate for benchmark 10x10 climate-controlled unit'}</td>
            </tr>
            <tr>
                <td><strong>Competitor Quality</strong></td>
                <td>{comp_quality}</td>
                <td>Aging/Poor (Opportunity)<br>Average (Neutral)<br>Modern/Strong (Challenge)</td>
                <td>{'Existing facilities show age/wear - opportunity for modern product to capture premium' if comp_quality == 'Aging/Poor' else 'Standard competitive set - differentiation through amenities and service' if comp_quality == 'Average' else 'High-quality competition requires best-in-class execution and positioning'}</td>
            </tr>
            <tr>
                <td><strong>Pricing Position</strong></td>
                <td>{pricing_position}</td>
                <td>Above Market (Preferred)<br>At Market (Neutral)<br>Below Market (Value play)</td>
                <td>{'Subject site can support premium pricing due to superior location or amenities' if pricing_position == 'Above Market' else 'Competitive pricing expected - focus on operational efficiency' if pricing_position == 'At Market' else 'Aggressive pricing required - maximize absorption but pressure margins'}</td>
            </tr>
        </table>

        <h3>Unified Competitive Database ({len(unified_competitors)} Facilities)</h3>
        <p style="font-size: 10pt; color: #666; margin-bottom: 10px;">
        Blue-highlighted rows indicate facilities with enhanced TractIQ data. <span style="color: #0066cc;">✓✓</span> = Multi-source verified | ✓ = Single source
        </p>
        <table>
            <tr>
                <th>#</th>
                <th>Facility Name</th>
                <th>Distance</th>
                <th>Size (NRSF)</th>
                <th>10x10 Rate</th>
                <th>Occupancy</th>
            </tr>
            {comp_rows if comp_rows else '<tr><td colspan="6" style="text-align: center;">No competitors identified within 3-mile radius</td></tr>'}
        </table>

        <h3>Competitive Strategy Recommendations</h3>
        <p><strong>Market Positioning:</strong> {'With limited competition and aging facilities, position as the premium modern alternative with superior technology, climate control, and security features.' if len(unified_competitors) <= 3 and comp_quality == 'Aging/Poor' else 'Differentiate through customer service, technology (mobile app, contactless access), and strategic pricing to capture market share.' if len(unified_competitors) <= 6 else 'In a saturated market, focus on niche segments (wine storage, business users, vehicle storage) and aggressive digital marketing to stand out.'}</p>

        <p><strong>Pricing Strategy:</strong> {'High occupancy (' + f'{avg_occ:.0f}' + '%) indicates pricing power. Consider premium positioning with strategic discounts for move-ins.' if avg_occ >= 90 else 'Balanced market conditions support at-market pricing with move-in promotions to accelerate absorption.' if avg_occ >= 85 else 'Moderate occupancy suggests competitive pricing environment. Focus on value proposition and service differentiation.'}</p>

        <p class="footer-note">
        <span class="ai-badge">DATA SYNTHESIS</span>
        Intelligence synthesized from {synthesis_stats['google_maps_count']} Google Maps competitors + {synthesis_stats['tractiq_count']} TractIQ facilities. {synthesis_stats['enriched_count']} facilities cross-verified across multiple sources.
        </p>

        <div class="page-break"></div>
        """

    def generate_tractiq_insights_section(self, data: Dict) -> str:
        """
        Generate enhanced competitive intelligence from TractIQ PDF extractions
        Only shown if TractIQ data is available
        """
        pdf_ext_data = data.get('pdf_ext_data', {})

        if not pdf_ext_data:
            return ""  # No TractIQ data available

        # Aggregate data from all uploaded PDFs
        all_competitors = []
        all_rates = []
        all_trends = []
        unit_mix_data = {}
        market_metrics = {}

        for pdf_name, ext_data in pdf_ext_data.items():
            # Collect competitors
            if ext_data.get('competitors'):
                for comp in ext_data['competitors']:
                    comp['source_pdf'] = pdf_name
                    all_competitors.append(comp)

            # Collect rates
            if ext_data.get('extracted_rates'):
                all_rates.extend(ext_data['extracted_rates'])

            # Collect trends
            if ext_data.get('historical_trends'):
                all_trends.extend(ext_data['historical_trends'])

            # Collect unit mix
            if ext_data.get('unit_mix'):
                unit_mix_data.update(ext_data['unit_mix'])

            # Collect market metrics
            if ext_data.get('market_metrics'):
                market_metrics.update(ext_data['market_metrics'])

        if not any([all_competitors, all_rates, all_trends, unit_mix_data, market_metrics]):
            return ""  # No meaningful data extracted

        html = """
        <h1>TRACTIQ MARKET INTELLIGENCE</h1>

        <div class="recommendation-box" style="background-color: #E8F5E9;">
            <h3 style="margin-top: 0; color: #2E7D32;">📊 Enhanced Competitive Intelligence</h3>
            <p>The following insights are derived from uploaded TractIQ market reports, providing detailed competitive intelligence beyond standard web scraping.</p>
        </div>
        """

        # === SECTION 1: TractIQ Competitors ===
        if all_competitors:
            avg_tractiq_occ = sum(c.get('occupancy', 0) for c in all_competitors if c.get('occupancy', 0) > 0) / len([c for c in all_competitors if c.get('occupancy', 0) > 0]) if any(c.get('occupancy', 0) > 0 for c in all_competitors) else 0
            avg_tractiq_rate = sum(c.get('rate_10x10', 0) for c in all_competitors if c.get('rate_10x10', 0) > 0) / len([c for c in all_competitors if c.get('rate_10x10', 0) > 0]) if any(c.get('rate_10x10', 0) > 0 for c in all_competitors) else 0
            total_tractiq_units = sum(c.get('units', 0) for c in all_competitors)

            comp_rows = ""
            for i, comp in enumerate(all_competitors[:20], 1):  # Show top 20 from TractIQ
                comp_rows += f"""
                <tr>
                    <td>{i}</td>
                    <td>{comp.get('name', 'N/A')}</td>
                    <td>{comp.get('units', 'N/A')}</td>
                    <td>{f"{comp.get('occupancy', 0):.1f}%" if comp.get('occupancy') else 'N/A'}</td>
                    <td>{f"${comp.get('rate_10x10', 0):.0f}" if comp.get('rate_10x10') else 'N/A'}</td>
                    <td style="font-size: 9pt; color: #666;">{comp.get('source_pdf', 'Unknown')}</td>
                </tr>
                """

            html += f"""
            <h3>TractIQ Competitor Database ({len(all_competitors)} Facilities)</h3>
            <p><strong>Key Findings:</strong></p>
            <ul>
                <li><strong>Average Occupancy:</strong> {avg_tractiq_occ:.1f}% {'(Strong demand - competitors are full)' if avg_tractiq_occ >= 90 else '(Healthy demand environment)' if avg_tractiq_occ >= 85 else '(Moderate market conditions)' if avg_tractiq_occ >= 80 else '(Soft demand signals)'}</li>
                <li><strong>Average 10x10 Rate:</strong> ${avg_tractiq_rate:.0f}/month (from facilities reporting rates)</li>
                <li><strong>Total Competitive Units:</strong> {total_tractiq_units:,} units across {len(all_competitors)} facilities</li>
            </ul>

            <table>
                <tr>
                    <th>#</th>
                    <th>Facility Name</th>
                    <th>Units</th>
                    <th>Occupancy</th>
                    <th>10x10 Rate</th>
                    <th>Source</th>
                </tr>
                {comp_rows}
            </table>
            """

        # === SECTION 2: Unit Mix Analysis ===
        if unit_mix_data:
            total_units_mix = sum(unit_mix_data.values())

            mix_rows = ""
            for size, count in sorted(unit_mix_data.items(), key=lambda x: x[1], reverse=True):
                pct = (count / total_units_mix * 100) if total_units_mix > 0 else 0
                mix_rows += f"""
                <tr>
                    <td>{size}</td>
                    <td>{count}</td>
                    <td>{pct:.1f}%</td>
                    <td style="background: linear-gradient(to right, #2196F3 {pct}%, #E3F2FD {pct}%);">&nbsp;</td>
                </tr>
                """

            # Find dominant size
            dominant_size = max(unit_mix_data.items(), key=lambda x: x[1])[0] if unit_mix_data else "10x10"

            html += f"""
            <h3>Competitive Unit Mix Analysis</h3>
            <p><strong>Market Composition:</strong> Analysis of {total_units_mix:,} units across competitive facilities reveals the optimal unit mix for this market.</p>

            <table>
                <tr>
                    <th>Unit Size</th>
                    <th>Unit Count</th>
                    <th>% of Mix</th>
                    <th>Distribution</th>
                </tr>
                {mix_rows}
            </table>

            <div class="recommendation-box">
                <h4 style="margin-top: 0;">Unit Mix Recommendations</h4>
                <p><strong>Dominant Size:</strong> {dominant_size} units represent the largest segment of competitive supply, indicating strong market demand for this size category.</p>
                <p><strong>Optimization Strategy:</strong> {"Match competitive mix to minimize market risk, with modest over-indexing on high-demand sizes to capture premium." if len(unit_mix_data) >= 5 else "Limited unit mix data - recommend balanced approach with emphasis on 10x10 and 10x15 climate-controlled units."}</p>
            </div>
            """

        # === SECTION 3: Historical Rate Trends ===
        if all_trends:
            # Sort trends chronologically
            sorted_trends = sorted(all_trends, key=lambda x: x.get('period', ''))

            trend_rows = ""
            for trend in sorted_trends[-10:]:  # Show last 10 periods
                period = trend.get('period', 'N/A')
                rate = trend.get('rate')
                occ = trend.get('occupancy')

                trend_rows += f"""
                <tr>
                    <td>{period}</td>
                    <td>{f"${rate}" if rate else 'N/A'}</td>
                    <td>{f"{occ:.1f}%" if occ else 'N/A'}</td>
                    <td>{'Rate trend data' if rate else ''}{'Occupancy trend data' if occ else ''}</td>
                </tr>
                """

            # Calculate rate growth if we have enough data
            rate_trends = [t for t in sorted_trends if t.get('rate')]
            rate_growth = ""
            if len(rate_trends) >= 2:
                first_rate = rate_trends[0]['rate']
                last_rate = rate_trends[-1]['rate']
                growth_pct = ((last_rate - first_rate) / first_rate * 100) if first_rate > 0 else 0
                periods = len(rate_trends)
                rate_growth = f"""
                <p><strong>Rate Growth Analysis:</strong> From {rate_trends[0]['period']} to {rate_trends[-1]['period']},
                market rates {'increased' if growth_pct > 0 else 'decreased'} by {abs(growth_pct):.1f}%
                (from ${first_rate} to ${last_rate}), indicating {'strong pricing power and healthy market fundamentals' if growth_pct > 3 else 'stable market conditions with modest pricing flexibility' if growth_pct >= 0 else 'pricing pressure and potential oversupply concerns'}.</p>
                """

            html += f"""
            <h3>Historical Market Trends</h3>
            <p>Time-series analysis of market rates and occupancy provides insight into market trajectory and future pricing potential.</p>

            <table>
                <tr>
                    <th>Period</th>
                    <th>Market Rate</th>
                    <th>Occupancy</th>
                    <th>Notes</th>
                </tr>
                {trend_rows}
            </table>

            {rate_growth}
            """

        # === SECTION 4: Market-Level Metrics ===
        if market_metrics:
            metrics_rows = ""

            if market_metrics.get('market_occupancy'):
                metrics_rows += f"""
                <tr>
                    <td>Market Occupancy</td>
                    <td>{market_metrics['market_occupancy']:.1f}%</td>
                    <td>{'Excellent - Market operating at peak capacity' if market_metrics['market_occupancy'] >= 90 else 'Good - Healthy demand environment' if market_metrics['market_occupancy'] >= 85 else 'Fair - Moderate market conditions' if market_metrics['market_occupancy'] >= 80 else 'Caution - Below-average occupancy signals soft demand'}</td>
                </tr>
                """

            if market_metrics.get('market_avg_rate'):
                metrics_rows += f"""
                <tr>
                    <td>Market Average Rate (10x10)</td>
                    <td>${market_metrics['market_avg_rate']:.0f}/month</td>
                    <td>Benchmark rate for pro forma modeling and competitive positioning</td>
                </tr>
                """

            if market_metrics.get('total_supply'):
                metrics_rows += f"""
                <tr>
                    <td>Total Market Supply</td>
                    <td>{market_metrics['total_supply']:,} units</td>
                    <td>Aggregate competitive inventory in the market area</td>
                </tr>
                """

            if metrics_rows:
                html += f"""
                <h3>Market-Level Metrics</h3>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                        <th>Interpretation</th>
                    </tr>
                    {metrics_rows}
                </table>
                """

        html += """
        <p class="footer-note">
        <span class="ai-badge">TRACTIQ DATA</span>
        Market intelligence extracted from uploaded TractIQ reports. Data accuracy depends on report recency and coverage area.
        </p>

        <div class="page-break"></div>
        """

        return html

    def generate_economic_section(self, data: Dict) -> str:
        """Generate economic indicators section"""
        economic = data.get('scorer_inputs', {}).get('economic', {})
        score_breakdown = data.get('score_breakdown', {}).get('economic', {})

        unemployment = economic.get('unemployment', 0)
        biz_growth = economic.get('business_growth', 'N/A')
        stability = economic.get('stability', 'N/A')

        econ_score = score_breakdown.get('score', 0)
        econ_max = score_breakdown.get('max', 10)

        assessment = ""
        if econ_score >= 8:
            assessment = "EXCELLENT - Strong economic fundamentals support sustained self-storage demand."
        elif econ_score >= 6:
            assessment = "GOOD - Stable economic conditions favorable for self-storage investment."
        elif econ_score >= 4:
            assessment = "FAIR - Economic indicators are mixed but acceptable."
        else:
            assessment = "WEAK - Economic headwinds may constrain demand growth."

        return f"""
        <h1>ECONOMIC INDICATORS</h1>

        <div class="recommendation-box">
            <h3 style="margin-top: 0;">Score: {econ_score}/{econ_max} points</h3>
            <p><strong>Assessment:</strong> {assessment}</p>
        </div>

        <h3>Local Economic Health</h3>
        <table>
            <tr>
                <th>Indicator</th>
                <th>Value</th>
                <th>Benchmark</th>
                <th>Impact on Self-Storage</th>
            </tr>
            <tr>
                <td><strong>Unemployment Rate</strong></td>
                <td>{unemployment:.1f}%</td>
                <td>≤4.0% (Excellent)<br>4.1-5.5% (Good)<br>5.6-7.0% (Fair)<br>>7.0% (Weak)</td>
                <td>{'Low unemployment indicates strong job market and economic vitality, supporting consumer spending and storage demand.' if unemployment <= 4.0 else 'Healthy employment supports stable demand.' if unemployment <= 5.5 else 'Moderate unemployment - economic conditions are acceptable but not robust.' if unemployment <= 7.0 else 'High unemployment may constrain demand and pricing power.'}</td>
            </tr>
            <tr>
                <td><strong>Business Growth</strong></td>
                <td>{biz_growth}</td>
                <td>Growing (Preferred)<br>Stable (Acceptable)<br>Declining (Risk)</td>
                <td>{'Business formation and expansion drives commercial storage demand (inventory, equipment, documents).' if biz_growth == 'Growing' else 'Stable business environment supports consistent demand.' if biz_growth == 'Stable' else 'Declining business activity may limit commercial storage opportunities.'}</td>
            </tr>
            <tr>
                <td><strong>Economic Stability</strong></td>
                <td>{stability}</td>
                <td>Stable (Preferred)<br>Moderate (Acceptable)<br>Volatile (Risk)</td>
                <td>{'Diversified economy reduces recession risk and supports long-term demand stability.' if stability == 'Stable' else 'Some economic concentration but manageable.' if stability == 'Moderate' else 'Single-industry dependence creates volatility risk during downturns.'}</td>
            </tr>
        </table>

        <h3>Economic Impact on Self-Storage Demand</h3>
        <p><strong>Counter-Cyclical Elements:</strong> Self-storage has historically demonstrated recession-resistant characteristics.
        During economic downturns, downsizing (home and business), foreclosures, and life disruptions can actually increase demand
        for temporary storage solutions.</p>

        <p><strong>Pro-Cyclical Elements:</strong> Strong economic growth supports business expansion (commercial units), household
        formation (residential moves), and discretionary spending on lifestyle storage (RVs, boats, seasonal items).</p>

        <p><strong>Employment Correlation:</strong> Low unemployment correlates with higher mobility (job changes trigger moves),
        business formation (inventory storage needs), and affordability (consumers can pay storage bills).</p>

        <div class="page-break"></div>
        """

    def generate_financial_section(self, data: Dict) -> str:
        """Generate financial projections section"""
        inputs = data.get('inputs', {})
        comp_stats = data.get('comp_stats', {})
        recommendation = data.get('recommendation', {})

        land_cost = inputs.get('land_cost', 0)
        construction_psf = inputs.get('construction_cost_psf', 0)
        rentable_sqft = inputs.get('rentable_sqft', 0)

        # Calculate development costs
        hard_cost = construction_psf * rentable_sqft
        soft_costs = hard_cost * 0.15  # 15% soft costs typical
        total_cost = land_cost + hard_cost + soft_costs

        # Revenue projections (if we have market rate data)
        avg_rate = comp_stats.get('avg_rate_10x10', 120)
        stabilized_occ = 0.90  # Industry standard stabilized occupancy

        # Rough revenue estimate (assuming $1.20/SF/month at stabilization)
        monthly_revenue_psf = 1.20
        annual_gross_revenue = rentable_sqft * monthly_revenue_psf * 12 * stabilized_occ

        # Operating expenses (typically 35-40% of revenues)
        opex_ratio = 0.37
        noi = annual_gross_revenue * (1 - opex_ratio)

        # Yield on cost
        yoc = (noi / total_cost * 100) if total_cost > 0 else 0

        # Pre-compute values for table display
        land_psf = (land_cost / rentable_sqft) if rentable_sqft > 0 else 0
        land_pct = (land_cost / total_cost * 100) if total_cost > 0 else 0
        hard_pct = (hard_cost / total_cost * 100) if total_cost > 0 else 0
        soft_psf = (soft_costs / rentable_sqft) if rentable_sqft > 0 else 0
        soft_pct = (soft_costs / total_cost * 100) if total_cost > 0 else 0
        total_psf = (total_cost / rentable_sqft) if rentable_sqft > 0 else 0
        noi_psf_month = (noi / rentable_sqft / 12) if rentable_sqft > 0 else 0

        return f"""
        <h1>FINANCIAL PROJECTIONS</h1>

        <div class="warning-box">
            <p><strong>Disclaimer:</strong> The following projections are preliminary estimates for feasibility assessment.
            Detailed underwriting requires site-specific pricing studies, construction bids, and pro forma modeling.</p>
        </div>

        <h3>Development Budget (Estimated)</h3>
        <table>
            <tr>
                <th>Line Item</th>
                <th>Amount</th>
                <th>$/SF</th>
                <th>% of Total</th>
            </tr>
            <tr>
                <td>Land Acquisition</td>
                <td>${land_cost:,}</td>
                <td>${land_psf:.2f}</td>
                <td>{land_pct:.1f}%</td>
            </tr>
            <tr>
                <td>Hard Costs ({rentable_sqft:,} NRSF @ ${construction_psf}/SF)</td>
                <td>${hard_cost:,}</td>
                <td>${construction_psf:.2f}</td>
                <td>{hard_pct:.1f}%</td>
            </tr>
            <tr>
                <td>Soft Costs (Architecture, Engineering, Permits, etc.)</td>
                <td>${soft_costs:,}</td>
                <td>${soft_psf:.2f}</td>
                <td>{soft_pct:.1f}%</td>
            </tr>
            <tr style="background: #f0f0f0; font-weight: 600;">
                <td><strong>Total Development Cost</strong></td>
                <td><strong>${total_cost:,}</strong></td>
                <td><strong>${total_psf:.2f}</strong></td>
                <td><strong>100.0%</strong></td>
            </tr>
        </table>

        <h3>Stabilized Operating Pro Forma (Year 3+)</h3>
        <table>
            <tr>
                <th>Item</th>
                <th>Annual Amount</th>
                <th>$/SF/Month</th>
                <th>Notes</th>
            </tr>
            <tr style="background: #e8f5e9;">
                <td>Gross Potential Revenue</td>
                <td>${rentable_sqft * monthly_revenue_psf * 12:,.0f}</td>
                <td>${monthly_revenue_psf:.2f}</td>
                <td>Market rate estimate</td>
            </tr>
            <tr>
                <td>Less: Vacancy Loss (10%)</td>
                <td>-${rentable_sqft * monthly_revenue_psf * 12 * 0.10:,.0f}</td>
                <td>-${monthly_revenue_psf * 0.10:.2f}</td>
                <td>90% stabilized occupancy</td>
            </tr>
            <tr style="background: #fff3cd; font-weight: 600;">
                <td>Effective Gross Income</td>
                <td>${annual_gross_revenue:,.0f}</td>
                <td>${monthly_revenue_psf * 0.90:.2f}</td>
                <td></td>
            </tr>
            <tr>
                <td>Operating Expenses (37% of EGI)</td>
                <td>-${annual_gross_revenue * opex_ratio:,.0f}</td>
                <td>-${monthly_revenue_psf * 0.90 * opex_ratio:.2f}</td>
                <td>Property tax, insurance, utilities, mgmt</td>
            </tr>
            <tr style="background: #0C2340; color: white; font-weight: 600;">
                <td><strong>Net Operating Income (NOI)</strong></td>
                <td><strong>${noi:,.0f}</strong></td>
                <td><strong>${noi_psf_month:.2f}</strong></td>
                <td></td>
            </tr>
        </table>

        <h3>Investment Returns</h3>
        <div class="metric-box">
            <div class="metric-label">Yield on Cost</div>
            <div class="metric-value">{yoc:.1f}%</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">Stabilized NOI</div>
            <div class="metric-value">${noi/1000:.0f}K</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">Cost per SF</div>
            <div class="metric-value">${total_psf:.0f}</div>
        </div>

        <p><strong>Yield on Cost Analysis:</strong> {'Strong YOC above 8% indicates attractive development returns that exceed typical cap rate compression risk.' if yoc >= 8.0 else 'Moderate YOC of 7-8% is acceptable for stabilized markets with low lease-up risk.' if yoc >= 7.0 else 'YOC below 7% may be challenged to generate adequate risk-adjusted returns unless significant appreciation expected.' if yoc > 0 else 'Insufficient data for yield calculation.'}</p>

        <h3>Key Assumptions & Sensitivities</h3>
        <ul>
            <li><strong>Construction Cost:</strong> ${construction_psf}/SF assumed. Actual costs vary by market, building type (single vs. multi-story), and site conditions.</li>
            <li><strong>Revenue:</strong> ${monthly_revenue_psf:.2f}/SF/month blended rate. Verify with local market pricing study.</li>
            <li><strong>Stabilized Occupancy:</strong> 90% assumed (industry standard). Actual performance depends on competition and execution.</li>
            <li><strong>Operating Expenses:</strong> 37% of EGI typical for professional management. Owner-operated facilities may run lower.</li>
            <li><strong>Lease-Up Period:</strong> Not reflected in stabilized pro forma. Typically 24-36 months to reach 90% occupancy.</li>
        </ul>

        <div class="recommendation-box">
            <p><strong>Next Steps:</strong> Commission detailed feasibility study including competitive pricing survey, civil engineering review,
            final construction estimates, and 10-year discounted cash flow model before final investment decision.</p>
        </div>

        <div class="page-break"></div>
        """

    def generate_charts_section(self, data: Dict) -> str:
        """
        Generate visual analytics section with embedded charts.
        Uses the FeasibilityChartGenerator to create matplotlib charts.
        """
        if not CHARTS_AVAILABLE:
            return """
            <h1>VISUAL ANALYTICS</h1>
            <div class="warning-box">
                <p>Charts unavailable - matplotlib not installed.</p>
            </div>
            <div class="page-break"></div>
            """

        # Chart functions are imported at module level
        charts_html = """
        <h1>VISUAL ANALYTICS</h1>
        <p>The following charts provide visual representation of key metrics and projections.</p>
        """

        # Get enhanced pro forma data if available
        enhanced_proforma = data.get('enhanced_proforma')
        sensitivity_data = data.get('sensitivity_analysis')
        scenario_data = data.get('scenario_analysis')
        score_breakdown = data.get('score_breakdown', {})

        # 1. Scoring Radar Chart
        if score_breakdown:
            # Build lists for radar chart (function expects lists, not dicts)
            categories = ['Demographics', 'Supply/Demand', 'Site Quality', 'Competition', 'Economic']
            scores = [
                score_breakdown.get('demographics', {}).get('score', 0),
                score_breakdown.get('supply', {}).get('score', 0),
                score_breakdown.get('site', {}).get('score', 0),
                score_breakdown.get('competitor', {}).get('score', 0),
                score_breakdown.get('economic', {}).get('score', 0)
            ]
            max_scores = [25, 25, 25, 15, 10]
            try:
                radar_b64 = generate_scoring_radar(categories, scores, max_scores)
                charts_html += f"""
                <div class="chart-container">
                    <div class="chart-title">Feasibility Score Breakdown</div>
                    <img src="data:image/png;base64,{radar_b64}" alt="Scoring Radar Chart">
                    <div class="chart-caption">
                        Performance across 5 key feasibility categories normalized to percentage of maximum score.
                    </div>
                </div>
                """
            except Exception as e:
                charts_html += f"<!-- Radar chart error: {e} -->"

        # 2. NOI Waterfall Chart (if enhanced proforma available)
        if enhanced_proforma:
            try:
                # Extract annual summaries for NOI progression
                annual_summaries = enhanced_proforma.get('annual_summaries', [])
                if annual_summaries:
                    years = list(range(1, len(annual_summaries[:7]) + 1))
                    noi_values = [s.get('noi', 0) for s in annual_summaries[:7]]
                    noi_b64 = generate_noi_waterfall(years, noi_values)
                    charts_html += f"""
                    <div class="chart-container">
                        <div class="chart-title">7-Year NOI Progression</div>
                        <img src="data:image/png;base64,{noi_b64}" alt="NOI Waterfall Chart">
                        <div class="chart-caption">
                            Net Operating Income growth from lease-up through stabilization. Shows NOI evolution over 7-year projection period.
                        </div>
                    </div>
                    """
            except Exception as e:
                charts_html += f"<!-- NOI chart error: {e} -->"

        # 3. Occupancy Curve (if enhanced proforma available)
        if enhanced_proforma:
            try:
                monthly_cashflows = enhanced_proforma.get('monthly_cashflows', [])
                if monthly_cashflows:
                    months = list(range(1, len(monthly_cashflows[:84]) + 1))
                    occupancy_pcts = [cf.get('occupancy_pct', 0) * 100 for cf in monthly_cashflows[:84]]
                    occ_b64 = generate_occupancy_curve(months, occupancy_pcts)
                    charts_html += f"""
                    <div class="chart-container">
                        <div class="chart-title">Occupancy Ramp-Up Curve</div>
                        <img src="data:image/png;base64,{occ_b64}" alt="Occupancy Curve">
                        <div class="chart-caption">
                            Monthly occupancy projection showing lease-up trajectory to stabilized occupancy.
                        </div>
                    </div>
                    """
            except Exception as e:
                charts_html += f"<!-- Occupancy chart error: {e} -->"

        charts_html += '<div class="page-break"></div>'

        # 4. Sensitivity Tornado (if sensitivity analysis available)
        if sensitivity_data:
            try:
                tornado_results = sensitivity_data.get('results', [])
                if tornado_results:
                    # Extract data for tornado chart
                    variables = [r.get('variable', '') for r in tornado_results]
                    low_values = [r.get('low_irr', 0) for r in tornado_results]
                    high_values = [r.get('high_irr', 0) for r in tornado_results]
                    base_irr = sensitivity_data.get('base_irr', 0)
                    tornado_b64 = generate_sensitivity_tornado(variables, low_values, high_values, base_irr)
                    charts_html += f"""
                    <h1>SENSITIVITY ANALYSIS</h1>
                    <p>The tornado diagram below shows how changes in key variables impact the project's Internal Rate of Return (IRR).</p>
                    <div class="chart-container">
                        <div class="chart-title">IRR Sensitivity to Key Variables</div>
                        <img src="data:image/png;base64,{tornado_b64}" alt="Sensitivity Tornado">
                        <div class="chart-caption">
                            Variables sorted by impact magnitude. Longer bars indicate higher sensitivity to that variable.
                        </div>
                    </div>
                    """
            except Exception as e:
                charts_html += f"<!-- Tornado chart error: {e} -->"

        # 5. Scenario Comparison (if scenario analysis available)
        if scenario_data:
            try:
                scenarios_dict = scenario_data.get('scenarios', {})
                if scenarios_dict:
                    # Extract data for scenario chart
                    scenario_names = ['Conservative', 'Base Case', 'Aggressive']
                    irrs = [
                        scenarios_dict.get('conservative', {}).get('irr', 0),
                        scenarios_dict.get('base', {}).get('irr', 0),
                        scenarios_dict.get('aggressive', {}).get('irr', 0)
                    ]
                    npvs = [
                        scenarios_dict.get('conservative', {}).get('npv', 0),
                        scenarios_dict.get('base', {}).get('npv', 0),
                        scenarios_dict.get('aggressive', {}).get('npv', 0)
                    ]
                    scenario_b64 = generate_scenario_comparison(scenario_names, irrs, npvs)
                    charts_html += f"""
                    <h2>Scenario Analysis</h2>
                    <p>Three-case scenario modeling provides a probability-weighted view of potential outcomes.</p>
                    <div class="chart-container">
                        <div class="chart-title">Scenario Comparison: IRR and NPV</div>
                        <img src="data:image/png;base64,{scenario_b64}" alt="Scenario Comparison">
                        <div class="chart-caption">
                            Conservative (25% weight), Base Case (50% weight), and Aggressive (25% weight) scenarios.
                        </div>
                    </div>
                    """

                    # Add scenario summary table
                    cons = scenarios_dict.get('conservative', {})
                    base = scenarios_dict.get('base', {})
                    agg = scenarios_dict.get('aggressive', {})

                    charts_html += f"""
                    <h3>Scenario Summary</h3>
                    <table class="scenario-table">
                        <tr>
                            <th>Metric</th>
                            <th class="scenario-conservative">Conservative</th>
                            <th class="scenario-base">Base Case</th>
                            <th class="scenario-aggressive">Aggressive</th>
                        </tr>
                        <tr>
                            <td><strong>IRR</strong></td>
                            <td class="scenario-conservative">{cons.get('irr', 0):.1f}%</td>
                            <td class="scenario-base">{base.get('irr', 0):.1f}%</td>
                            <td class="scenario-aggressive">{agg.get('irr', 0):.1f}%</td>
                        </tr>
                        <tr>
                            <td><strong>NPV</strong></td>
                            <td class="scenario-conservative">${cons.get('npv', 0):,.0f}</td>
                            <td class="scenario-base">${base.get('npv', 0):,.0f}</td>
                            <td class="scenario-aggressive">${agg.get('npv', 0):,.0f}</td>
                        </tr>
                        <tr>
                            <td><strong>Probability</strong></td>
                            <td class="scenario-conservative">25%</td>
                            <td class="scenario-base">50%</td>
                            <td class="scenario-aggressive">25%</td>
                        </tr>
                    </table>

                    <div class="recommendation-box">
                        <h4 style="margin-top: 0;">Expected Returns (Probability-Weighted)</h4>
                        <p><strong>Expected IRR:</strong> {scenario_data.get('expected_irr', 0):.1f}%</p>
                        <p><strong>Expected NPV:</strong> ${scenario_data.get('expected_npv', 0):,.0f}</p>
                    </div>
                    """
            except Exception as e:
                charts_html += f"<!-- Scenario chart error: {e} -->"

        charts_html += '<div class="page-break"></div>'
        return charts_html

    def generate_investment_analysis_section(self, data: Dict) -> str:
        """Generate investment analysis section with breakeven and sizing analysis."""
        investment_data = data.get('investment_analysis')

        if not investment_data:
            return ""

        breakeven = investment_data.get('breakeven', {})
        land_analysis = investment_data.get('land_analysis', {})
        debt_sizing = investment_data.get('debt_sizing', {})
        grade = investment_data.get('grade', 'N/A')
        recommendation = investment_data.get('recommendation', 'N/A')

        grade_color = {
            'A': '#28a745',
            'B': '#5cb85c',
            'C': '#f0ad4e',
            'D': '#d9534f',
            'F': '#c9302c'
        }.get(grade, '#666')

        return f"""
        <h1>INVESTMENT ANALYSIS</h1>

        <div class="score-card" style="background: {grade_color};">
            <h1 style="font-size: 72pt;">{grade}</h1>
            <p style="margin: 10px 0 0 0; font-size: 18pt;">INVESTMENT GRADE</p>
            <p style="font-size: 14pt; margin-top: 10px;">{recommendation}</p>
        </div>

        <h3>Breakeven Analysis</h3>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Interpretation</th>
            </tr>
            <tr>
                <td><strong>Breakeven Occupancy</strong></td>
                <td>{breakeven.get('occupancy_pct', 0):.1f}%</td>
                <td>{'Favorable - Low breakeven provides cushion against underperformance' if breakeven.get('occupancy_pct', 100) < 70 else 'Moderate - Standard risk profile' if breakeven.get('occupancy_pct', 100) < 80 else 'Elevated - Limited margin for error'}</td>
            </tr>
            <tr>
                <td><strong>Breakeven Rate ($/SF)</strong></td>
                <td>${breakeven.get('rate_psf', 0):.2f}</td>
                <td>Minimum rental rate required to cover all operating expenses and debt service</td>
            </tr>
        </table>

        <h3>Land Cost Sensitivity</h3>
        <table>
            <tr>
                <th>Target IRR</th>
                <th>Maximum Land Cost</th>
                <th>Land $/SF</th>
            </tr>
            <tr>
                <td>12%</td>
                <td>${land_analysis.get('max_land_12_irr', 0):,.0f}</td>
                <td>${land_analysis.get('land_psf_12_irr', 0):.2f}</td>
            </tr>
            <tr>
                <td>15%</td>
                <td>${land_analysis.get('max_land_15_irr', 0):,.0f}</td>
                <td>${land_analysis.get('land_psf_15_irr', 0):.2f}</td>
            </tr>
            <tr>
                <td>18%</td>
                <td>${land_analysis.get('max_land_18_irr', 0):,.0f}</td>
                <td>${land_analysis.get('land_psf_18_irr', 0):.2f}</td>
            </tr>
        </table>

        <h3>Debt Capacity Analysis</h3>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Notes</th>
            </tr>
            <tr>
                <td><strong>Maximum Loan Amount</strong></td>
                <td>${debt_sizing.get('max_loan', 0):,.0f}</td>
                <td>Based on {debt_sizing.get('ltc_pct', 0):.0f}% LTC constraint</td>
            </tr>
            <tr>
                <td><strong>Required Equity</strong></td>
                <td>${debt_sizing.get('equity_required', 0):,.0f}</td>
                <td>Minimum equity contribution</td>
            </tr>
            <tr>
                <td><strong>Projected DSCR</strong></td>
                <td>{debt_sizing.get('dscr', 0):.2f}x</td>
                <td>{'Above 1.25x minimum - favorable' if debt_sizing.get('dscr', 0) >= 1.25 else 'Below 1.25x minimum - lender may require additional equity'}</td>
            </tr>
        </table>

        <div class="page-break"></div>
        """

    def generate_appendix(self, data: Dict) -> str:
        """Generate appendix with data sources and methodology"""

        ai_results = data.get('ai_results', {})

        site_source = "Google Street View + Claude Vision AI" if ai_results.get('site', {}).get('has_street_view') else "Default estimates"
        econ_source = ai_results.get('economic', {}).get('data_source', 'Default')
        demo_source = ai_results.get('demographics', {}).get('data_source', 'Default')

        return f"""
        <h1>APPENDIX: DATA SOURCES & METHODOLOGY</h1>

        <h3>AI-Powered Data Collection</h3>
        <p>This feasibility study leverages artificial intelligence and real-time APIs to eliminate manual estimation:</p>

        <table>
            <tr>
                <th>Data Category</th>
                <th>Source</th>
                <th>Method</th>
            </tr>
            <tr>
                <td>Site Analysis (Visibility/Access)</td>
                <td>{site_source}</td>
                <td>Computer vision analysis of Street View imagery</td>
            </tr>
            <tr>
                <td>Demographics (Age 25-54%)</td>
                <td>{demo_source}</td>
                <td>Census Bureau ACS 5-Year Estimates API</td>
            </tr>
            <tr>
                <td>Economic Indicators</td>
                <td>{econ_source}</td>
                <td>Bureau of Labor Statistics (BLS) API</td>
            </tr>
            <tr>
                <td>Competitor Intelligence</td>
                <td>Google Maps + TractIQ</td>
                <td>Real-time web scraping + proprietary database</td>
            </tr>
        </table>

        <h3>Scoring Methodology</h3>
        <p>The Allspace Storage Feasibility Rubric (100-point system) evaluates:</p>
        <ul>
            <li><strong>Demographics (25 pts):</strong> Population, income, growth, renters, age distribution</li>
            <li><strong>Supply (25 pts):</strong> SF/capita, occupancy, absorption trends, pipeline</li>
            <li><strong>Site (25 pts):</strong> Visibility, access, zoning, size adequacy</li>
            <li><strong>Competitor (15 pts):</strong> Count, quality, pricing position</li>
            <li><strong>Economic (10 pts):</strong> Unemployment, business growth, stability</li>
        </ul>

        <p class="footer-note">
            <strong>Disclaimer:</strong> This report is for informational purposes only and should not be construed as investment advice.
            All projections are estimates based on current market conditions and are subject to change.
            Consult with qualified professionals before making investment decisions.
        </p>
        """

    def generate_full_report(self, data: Dict) -> bytes:
        """
        Generate complete PDF report

        Args:
            data: Dict containing all report data
                - address: str
                - lat, lon: float
                - demographics: Dict
                - feasibility: Dict
                - competitors: List[Dict]
                - comp_stats: Dict
                - recommendation: Dict
                - ai_results: Dict
                - inputs: Dict

        Returns:
            PDF file as bytes
        """

        report_date = datetime.now().strftime("%B %d, %Y")
        address = data.get('address', 'Subject Property')

        # Generate optional sections based on available data
        charts_section = self.generate_charts_section(data) if CHARTS_AVAILABLE else ""
        investment_section = self.generate_investment_analysis_section(data) if data.get('investment_analysis') else ""

        # Build HTML report
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Feasibility Study - {address}</title>
        </head>
        <body>
            {self.generate_cover_page(address, report_date)}
            {self.generate_executive_summary(data)}
            {self.generate_location_summary(data)}
            {self.generate_demographics_section(data)}
            {self.generate_supply_demand_section(data)}
            {self.generate_competitor_section(data.get('competitors', []), data.get('comp_stats', {}), data)}
            {self.generate_tractiq_insights_section(data)}
            {self.generate_economic_section(data)}
            {self.generate_financial_section(data)}
            {investment_section}
            {charts_section}
            {self.generate_appendix(data)}
        </body>
        </html>
        """

        # Generate PDF
        pdf_file = HTML(string=html_content).write_pdf(
            stylesheets=[CSS(string=self._get_css_styles())]
        )

        return pdf_file


# Convenience function
def generate_feasibility_pdf(data: Dict, output_path: Optional[str] = None) -> bytes:
    """
    Generate a feasibility study PDF report

    Usage:
        pdf_bytes = generate_feasibility_pdf(report_data)
        with open('report.pdf', 'wb') as f:
            f.write(pdf_bytes)
    """

    generator = PDFReportGenerator()
    pdf_bytes = generator.generate_full_report(data)

    if output_path:
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)

    return pdf_bytes


def generate_ai_report_pdf(
    address: str,
    ai_sections: Dict[str, str],
    report_date: str = None,
    output_path: Optional[str] = None
) -> bytes:
    """
    Generate PDF from AI-generated narrative sections.

    Args:
        address: Site address for cover page
        ai_sections: Dict with keys like 'executive_summary', 'market_analysis', etc.
        report_date: Optional date string
        output_path: Optional path to save PDF

    Returns:
        PDF bytes
    """
    import markdown

    if report_date is None:
        report_date = datetime.now().strftime("%B %d, %Y")

    # Convert markdown sections to HTML and process chart markers
    def md_to_html(md_text: str) -> str:
        if not md_text or md_text.startswith("ERROR"):
            return "<p><em>Section not available</em></p>"

        # Convert markdown to HTML
        html = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])

        # Process chart markers and embed actual charts
        html = process_chart_markers(html)

        return html

    def process_chart_markers(html: str) -> str:
        """Replace chart markers with embedded chart images."""
        import re

        if not CHARTS_AVAILABLE:
            return html

        # Chart marker patterns and their generators
        chart_configs = {
            'SF_PER_CAPITA_COMPARISON': lambda: generate_sf_per_capita_comparison(
                [1, 3, 5],
                [7.5, 6.2, 5.8],  # Example values - would be replaced with actual data
                target_sf=6.5
            ) if generate_sf_per_capita_comparison else None,
            'COMPETITOR_SCATTER': lambda: generate_competitor_scatter(
                [0.5, 1.2, 2.1, 2.8, 3.5],
                [1.25, 1.18, 1.32, 1.45, 1.28],
                ['Site A', 'Site B', 'Site C', 'Site D', 'Site E'],
                subject_rate=1.35
            ) if generate_competitor_scatter else None,
            'MARKET_CYCLE_GAUGE': lambda: generate_market_cycle_gauge(
                'Expansion', 65
            ) if generate_market_cycle_gauge else None,
            'NOI_WATERFALL': lambda: generate_noi_waterfall(
                [1, 2, 3, 4, 5, 6, 7],
                [50000, 280000, 520000, 615000, 630000, 645000, 660000]
            ) if generate_noi_waterfall else None,
            'CASH_FLOW_TIMELINE': lambda: generate_cash_flow_chart(
                [1, 2, 3, 4, 5, 6, 7],
                [500000, 550000, 600000, 620000, 640000, 660000, 680000],
                [400000, 400000, 400000, 400000, 400000, 400000, 400000]
            ) if generate_cash_flow_chart else None,
            'SENSITIVITY_TORNADO': lambda: generate_sensitivity_tornado(
                ['Rental Rates', 'Construction Cost', 'Occupancy', 'Exit Cap Rate', 'Interest Rate'],
                [4.3, 8.7, 9.0, 10.7, 12.2],
                [20.5, 18.9, 16.0, 16.8, 15.0],
                13.6
            ) if generate_sensitivity_tornado else None,
            'SCENARIO_COMPARISON': lambda: generate_scenario_comparison(
                ['Conservative', 'Base Case', 'Aggressive'],
                [5.2, 13.6, 21.8],
                [-500000, 644000, 1800000]
            ) if generate_scenario_comparison else None,
            'SCORING_RADAR': lambda: generate_scoring_radar(
                ['Demographics', 'Supply/Demand', 'Site Quality', 'Competition', 'Economics'],
                [20, 18, 22, 12, 8],
                [25, 25, 25, 15, 10]
            ) if generate_scoring_radar else None,
            'DEMAND_DRIVER_PIE': lambda: generate_demand_driver_pie({
                'Residential': 35,
                'Commercial': 25,
                'Life Events': 20,
                'Student': 10,
                'Military': 10
            }) if generate_demand_driver_pie else None,
        }

        # Find and replace chart markers
        for marker, generator in chart_configs.items():
            pattern = rf'\[CHART:\s*{marker}\]'
            if re.search(pattern, html):
                try:
                    chart_base64 = generator()
                    if chart_base64:
                        img_html = f'<div class="chart-container"><img src="data:image/png;base64,{chart_base64}" style="max-width:100%; margin: 15px 0;" /></div>'
                        html = re.sub(pattern, img_html, html)
                except Exception as e:
                    print(f"Warning: Could not generate chart {marker}: {e}")
                    html = re.sub(pattern, f'<p><em>[Chart: {marker} - Generation failed]</em></p>', html)

        return html

    # Section titles mapping
    section_titles = {
        'executive_summary': 'Executive Summary',
        'market_analysis': 'Market Analysis',
        'financial_analysis': 'Financial Analysis',
        'site_scoring': 'Site Scoring & Evaluation',
        'risk_assessment': 'Risk Assessment',
        'recommendation': 'Investment Recommendation'
    }

    # Build sections HTML
    sections_html = ""
    for section_key, title in section_titles.items():
        content = ai_sections.get(section_key, '')
        if content and not content.startswith("ERROR"):
            sections_html += f"""
            <h2>{title}</h2>
            <div class="section-content">
                {md_to_html(content)}
            </div>
            """

    # Professional CSS for AI report
    css = """
    @page {
        size: letter;
        margin: 0.75in;
        @top-center {
            content: "STORAGE OS Feasibility Study";
            font-size: 10pt;
            color: #666;
        }
        @bottom-right {
            content: "Page " counter(page);
            font-size: 9pt;
            color: #666;
        }
    }

    body {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 11pt;
        line-height: 1.6;
        color: #1a1a1a;
    }

    .cover-page {
        text-align: center;
        padding-top: 180px;
        page-break-after: always;
    }

    .cover-title {
        font-size: 36pt;
        font-weight: 700;
        color: #0C2340;
        margin-bottom: 15px;
    }

    .cover-subtitle {
        font-size: 18pt;
        color: #666;
        margin-bottom: 40px;
    }

    .cover-address {
        font-size: 16pt;
        color: #0C2340;
        margin: 30px 0;
        font-weight: 500;
    }

    .cover-date {
        font-size: 12pt;
        color: #666;
        margin-top: 60px;
    }

    h2 {
        font-size: 18pt;
        font-weight: 600;
        color: #0C2340;
        margin-top: 35px;
        margin-bottom: 15px;
        border-left: 4px solid #F39C12;
        padding-left: 15px;
        page-break-after: avoid;
    }

    h3 {
        font-size: 14pt;
        font-weight: 600;
        color: #0C2340;
        margin-top: 20px;
        margin-bottom: 10px;
    }

    h4 {
        font-size: 12pt;
        font-weight: 600;
        color: #333;
        margin-top: 15px;
        margin-bottom: 8px;
    }

    p {
        margin-bottom: 12px;
        text-align: justify;
    }

    ul, ol {
        margin-bottom: 12px;
        padding-left: 25px;
    }

    li {
        margin-bottom: 6px;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
        font-size: 10pt;
    }

    th {
        background-color: #0C2340;
        color: white;
        padding: 10px;
        text-align: left;
        font-weight: 600;
    }

    td {
        padding: 8px 10px;
        border-bottom: 1px solid #ddd;
    }

    tr:nth-child(even) {
        background-color: #f8f9fa;
    }

    .section-content {
        margin-bottom: 25px;
    }

    strong {
        color: #0C2340;
    }

    .footer-note {
        font-size: 9pt;
        color: #666;
        margin-top: 40px;
        padding-top: 15px;
        border-top: 1px solid #ddd;
        text-align: center;
    }
    """

    # Build full HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Feasibility Study - {address}</title>
    </head>
    <body>
        <div class="cover-page">
            <div class="cover-title">FEASIBILITY STUDY</div>
            <div class="cover-subtitle">Self-Storage Development Analysis</div>
            <div class="cover-address">{address}</div>
            <div class="cover-date">
                Report Date: {report_date}<br><br>
                Generated by STORAGE OS<br>
                AI-Powered Market Intelligence
            </div>
        </div>

        {sections_html}

        <div class="footer-note">
            This report was generated using AI-powered analysis. All data should be independently verified.
            <br>© {datetime.now().year} STORAGE OS
        </div>
    </body>
    </html>
    """

    # Generate PDF
    pdf_bytes = HTML(string=html_content).write_pdf(
        stylesheets=[CSS(string=css)]
    )

    if output_path:
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)

    return pdf_bytes
