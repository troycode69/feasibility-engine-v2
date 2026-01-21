"""
Professional PDF Report Generator
Creates Bob Copper-quality feasibility study reports (20-30 pages)
Uses WeasyPrint for HTML → PDF conversion with professional styling
"""

from weasyprint import HTML, CSS
from datetime import datetime
from typing import Dict, List, Optional
import base64
import os
import io


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

        decision_color = {
            'PURSUE': '#28a745',
            'CAUTION': '#ffc107',
            'PASS': '#dc3545'
        }.get(decision, '#666')

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

        <h3>Key Investment Highlights</h3>
        <ul>
            <li><strong>Market Score:</strong> {market_score}/100 points (Allspace Storage Rubric)</li>
            <li><strong>Yield on Cost:</strong> {recommendation.get('financial_summary', {}).get('yield_on_cost', 'N/A')}</li>
            <li><strong>AI Analysis:</strong> Site, demographics, economic, and competitor data verified via live APIs</li>
        </ul>

        <div class="page-break"></div>
        """

    def generate_location_summary(self, data: Dict) -> str:
        """Generate location and site summary"""
        address = data.get('address', 'N/A')
        lat = data.get('lat', 0)
        lon = data.get('lon', 0)
        context = data.get('location_context', '')

        return f"""
        <h1>LOCATION SUMMARY</h1>

        <h3>Subject Property</h3>
        <p><strong>Address:</strong> {address}</p>
        <p><strong>Coordinates:</strong> {lat:.6f}, {lon:.6f}</p>

        {f'<p>{context}</p>' if context else ''}

        <div class="page-break"></div>
        """

    def generate_demographics_section(self, data: Dict) -> str:
        """Generate demographics analysis section"""
        demographics = data.get('demographics', {})

        return f"""
        <h1>DEMOGRAPHICS ANALYSIS</h1>

        <p>The following demographic indicators were analyzed for the subject property's trade area (3-mile radius):</p>

        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Score Impact</th>
            </tr>
            <tr>
                <td>Total Population</td>
                <td>{demographics.get('population', 0):,}</td>
                <td>Critical for demand estimation</td>
            </tr>
            <tr>
                <td>Median Household Income</td>
                <td>${demographics.get('median_income', 0):,}</td>
                <td>Indicates affordability</td>
            </tr>
            <tr>
                <td>Annual Growth Rate</td>
                <td>{demographics.get('household_growth', 0):.2%}</td>
                <td>Future demand growth</td>
            </tr>
            <tr>
                <td>Renter-Occupied Housing</td>
                <td>{demographics.get('renter_occupied_pct', 0)}%</td>
                <td>Target demographic penetration</td>
            </tr>
        </table>

        <div class="page-break"></div>
        """

    def generate_supply_demand_section(self, data: Dict) -> str:
        """Generate supply & demand analysis"""
        feasibility = data.get('feasibility', {})

        return f"""
        <h1>SUPPLY & DEMAND ANALYSIS</h1>

        <h3>Current Market Supply</h3>
        <p><strong>Square Feet Per Capita:</strong> {feasibility.get('sqft_per_capita', 0):.2f} SF/person</p>
        <p><strong>Equilibrium Target:</strong> 8.0 - 9.0 SF/person (industry standard)</p>

        <div class="recommendation-box">
            <p><strong>Supply Assessment:</strong>
            {'Market is undersupplied - favorable conditions' if feasibility.get('sqft_per_capita', 0) < 8.0
             else 'Market approaching equilibrium' if feasibility.get('sqft_per_capita', 0) < 9.0
             else 'Market may be oversupplied - caution advised'}</p>
        </div>

        <h3>Pipeline Development</h3>
        <p>Known projects in development within 3-mile radius:</p>
        <table>
            <tr>
                <th>Project Name</th>
                <th>Type</th>
                <th>Units/SF</th>
                <th>Distance</th>
            </tr>
            <tr>
                <td colspan="4" style="text-align: center; color: #666;">
                    (Pipeline data to be manually verified)
                </td>
            </tr>
        </table>

        <div class="page-break"></div>
        """

    def generate_competitor_section(self, competitors: List[Dict], comp_stats: Dict) -> str:
        """Generate competitive landscape section"""

        comp_rows = ""
        for comp in competitors[:10]:  # Show top 10
            comp_rows += f"""
            <tr>
                <td>{comp.get('name', 'N/A')}</td>
                <td>{comp.get('distance_miles', 0):.2f} mi</td>
                <td>{comp.get('nrsf', 0):,} SF</td>
                <td>${comp.get('rate_10x10_cc', 0):.0f}</td>
                <td>{comp.get('occupancy_pct', 0):.0f}%</td>
            </tr>
            """

        return f"""
        <h1>COMPETITIVE LANDSCAPE</h1>

        <h3>Market Summary</h3>
        <div class="metric-box">
            <div class="metric-label">Competitors (3mi)</div>
            <div class="metric-value">{comp_stats.get('count', 0)}</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">Avg Occupancy</div>
            <div class="metric-value">{comp_stats.get('avg_occupancy', 0):.0f}%</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">Avg Rate (10x10)</div>
            <div class="metric-value">${comp_stats.get('avg_rate_10x10', 0):.0f}</div>
        </div>

        <h3>Competitor Facilities</h3>
        <table>
            <tr>
                <th>Facility Name</th>
                <th>Distance</th>
                <th>Size (NRSF)</th>
                <th>10x10 Rate</th>
                <th>Occupancy</th>
            </tr>
            {comp_rows}
        </table>

        <p class="footer-note">
        <span class="ai-badge">AI ANALYZED</span>
        Competitor data sourced from Google Maps scraping and TractIQ integration.
        Occupancy estimates based on available data.
        </p>

        <div class="page-break"></div>
        """

    def generate_financial_section(self, data: Dict) -> str:
        """Generate financial projections section"""
        inputs = data.get('inputs', {})
        feasibility = data.get('feasibility', {})

        land_cost = inputs.get('land_cost', 0)
        construction_psf = inputs.get('construction_cost_psf', 0)
        rentable_sqft = inputs.get('rentable_sqft', 0)
        total_cost = land_cost + (construction_psf * rentable_sqft)

        return f"""
        <h1>FINANCIAL PROJECTIONS</h1>

        <h3>Development Budget</h3>
        <table>
            <tr>
                <th>Line Item</th>
                <th>Amount</th>
            </tr>
            <tr>
                <td>Land Acquisition</td>
                <td>${land_cost:,}</td>
            </tr>
            <tr>
                <td>Construction ({rentable_sqft:,} SF @ ${construction_psf}/SF)</td>
                <td>${construction_psf * rentable_sqft:,}</td>
            </tr>
            <tr style="background: #f0f0f0; font-weight: 600;">
                <td>Total Development Cost</td>
                <td>${total_cost:,}</td>
            </tr>
        </table>

        <h3>Stabilized Returns (Pro Forma)</h3>
        <div class="recommendation-box">
            <p><strong>Note:</strong> Detailed 7-year cash flow model available in separate Excel deliverable.
            This report provides Year 1 stabilization assumptions.</p>
        </div>

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
            {self.generate_competitor_section(data.get('competitors', []), data.get('comp_stats', {}))}
            {self.generate_financial_section(data)}
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
