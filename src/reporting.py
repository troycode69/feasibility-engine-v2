from xhtml2pdf import pisa
from jinja2 import Template
from typing import Tuple
import pandas as pd
from datetime import datetime
import io

# --- CSS / HTML TEMPLATE ---
REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        @page {
            size: letter portrait;
            margin: 1.5cm;
            @frame footer_frame {
                -pdf-frame-content: footerContent;
                bottom: 1cm;
                margin-left: 1.5cm;
                margin-right: 1.5cm;
                height: 1cm;
            }
        }
        
        body {
            font-family: Helvetica, Arial, sans-serif;
            color: #333333;
            font-size: 11pt;
            line-height: 1.4;
        }

        h1, h2, h3 {
            color: #002b5c; /* StorSageHQ Navy */
        }
        
        .header-bar {
            background-color: #002b5c;
            color: white;
            padding: 10px;
            font-size: 14pt;
            font-weight: bold;
            margin-bottom: 15px;
            border-bottom: 3px solid #b38f00; /* Gold accent */
        }
        
        .title-page {
            text-align: center;
            padding-top: 200px;
        }
        
        .title-main {
            font-size: 28pt;
            color: #002b5c;
            font-weight: bold;
            margin-bottom: 20px;
        }
        
        .title-sub {
            font-size: 16pt;
            color: #555;
            margin-bottom: 50px;
        }
        
        .card {
            background-color: #f8f9fa;
            border: 1px solid #ddd;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        
        th {
            background-color: #002b5c;
            color: white;
            padding: 8px;
            text-align: left;
            font-size: 10pt;
        }
        
        td {
            border-bottom: 1px solid #ddd;
            padding: 8px;
            font-size: 10pt;
            vertical-align: middle;
        }
        
        .score-bar-container {
            width: 100%;
            background-color: #e9ecef;
            height: 10px;
            border-radius: 5px;
        }
        
        .score-bar-fill {
            height: 100%;
            border-radius: 5px;
        }
        
        .metric-box {
            text-align: center;
            padding: 10px;
            background: #eee;
            border-top: 4px solid #002b5c;
        }

        .metric-val { font-size: 16pt; font-weight: bold; color: #002b5c; }
        .metric-label { font-size: 9pt; text-transform: uppercase; color: #555; }

        .footer {
             color: #7f8c8d;
             font-size: 9pt;
             text-align: center;
        }
    </style>
</head>
<body>

    <!-- TITLE PAGE -->
    <div class="title-page">
        <div style="font-size: 50px; margin-bottom: 20px;">🏢</div>
        <div class="title-main">Self-Storage Feasibility Study</div>
        <div class="title-sub">PREPARED FOR: {{ lat }}, {{ lon }}</div>
        <div style="margin-top: 100px;">
            <strong>Date:</strong> {{ report_date }}<br>
            <strong>Version:</strong> 1.0 (StorSageHQ Standard)
        </div>
    </div>
    
    <pdf:nextpage />

    <!-- EXECUTIVE SUMMARY -->
    <div class="header-bar">Executive Summary & Recommendation</div>
    
    <p>{{ exec_summary }}</p>
    
    <div class="card" style="margin-top: 20px;">
        <table style="border: none;">
            <tr>
                <td style="border: none;"><strong>Strategic Recommendation:</strong></td>
                <td style="border: none; text-align: right;">
                    <span style="background-color: {{ rec_color }}; color: white; padding: 5px 15px; border-radius: 4px; font-weight: bold;">
                        {{ recommendation }}
                    </span>
                </td>
            </tr>
        </table>
    </div>

    <h3>Key Financial Indicators</h3>
    <table style="border: none;">
        <tr>
            <td style="border: none; width: 33%;">
                <div class="metric-box">
                    <div class="metric-val">{{ yield_on_cost }}%</div>
                    <div class="metric-label">Yield on Cost</div>
                </div>
            </td>
            <td style="border: none; width: 33%;">
                <div class="metric-box">
                    <div class="metric-val">${{ equity_created }}</div>
                    <div class="metric-label">Equity Created</div>
                </div>
            </td>
            <td style="border: none; width: 33%;">
                 <div class="metric-box">
                    <div class="metric-val">${{ stabilize_value }}</div>
                    <div class="metric-label">Stabilized Value</div>
                </div>
            </td>
        </tr>
    </table>
    
    <div style="height: 20px;"></div>

    <!-- MARKET DEMOGRAPHICS -->
    <div class="header-bar">Market Demographics</div>
    
    <table>
        <thead>
            <tr>
                <th>Traffic Metric</th>
                <th>Value</th>
                <th>Impact</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Trade Area Population</td>
                <td><strong>{{ pop }}</strong></td>
                <td>Primary demand driver</td>
            </tr>
            <tr>
                <td>Annual Growth Rate</td>
                <td><strong>{{ growth }}</strong></td>
                <td>Future demand indicator</td>
            </tr>
            <tr>
                <td>Median Household Income</td>
                <td><strong>{{ income }}</strong></td>
                <td>Affordability index</td>
            </tr>
            <tr>
                <td>Renter Occupied</td>
                <td><strong>{{ renter }}</strong></td>
                <td>Correlation to storage use</td>
            </tr>
            <tr>
                <td>Median Age</td>
                <td><strong>{{ age }}</strong></td>
                <td>Life cycle stage indicator</td>
            </tr>
        </tbody>
    </table>

    <div style="height: 20px;"></div>

    <!-- SITE SCORING -->
    <div class="header-bar">Site Scoring System</div>
    <p>The site has been evaluated against our proprietary viability index (0-25 Scale).</p>
    
    <table>
        <thead>
            <tr>
                <th style="width: 30%;">Category</th>
                <th style="width: 15%;">Score</th>
                <th style="width: 55%;">Rating Visualization</th>
            </tr>
        </thead>
        <tbody>
            {% for cat, score in scores.items() if cat != 'Total' %}
            <tr>
                <td>{{ cat }}</td>
                <td><strong>{{ score }} / 5</strong></td>
                <td>
                    {{ score_bar(score * 5) }} <!-- Convert 0-5 to 0-25 scale roughly for bar width logic reuse if needed, or update logic -->
                </td>
            </tr>
            {% endfor %}
            <tr style="background-color: #f0f8ff;">
                <td><strong>TOTAL SCORE</strong></td>
                <td><strong>{{ scores.get('Total', 0) }} / 25</strong></td>
                <td>
                    {{ score_bar(scores.get('Total', 0)) }}
                </td>
            </tr>
        </tbody>
    </table>

    <pdf:nextpage />

    <!-- UNIT MIX -->
    <div class="header-bar">Proposed Unit Mix</div>
    <p>Optimized mix based on local demographic profile: <strong>{{ market_profile }}</strong></p>
    
    <table>
        <thead>
            <tr>
                <th>Unit Size</th>
                <th>Type</th>
                <th style="text-align: center;">Count</th>
                <th style="text-align: center;">SqFt / Unit</th>
                <th style="text-align: center;">Total SqFt</th>
                <th style="text-align: center;">% of NRSF</th>
            </tr>
        </thead>
        <tbody>
            {% for row in unit_mix_rows %}
            <tr>
                <td>{{ row.size }}</td>
                <td>{{ row.type }}</td>
                <td style="text-align: center;">{{ row.count }}</td>
                <td style="text-align: center;">{{ row.sqft_per }}</td>
                <td style="text-align: center;">{{ row.total_sqft }}</td>
                <td style="text-align: center;">{{ row.pct_nrsf }}%</td>
            </tr>
            {% endfor %}
            <tr style="background-color: #e0e0e0; font-weight: bold;">
                <td>TOTALS</td>
                <td>-</td>
                <td style="text-align: center;">{{ total_units }}</td>
                <td>-</td>
                <td style="text-align: center;">{{ total_sqft }}</td>
                <td style="text-align: center;">100%</td>
            </tr>
        </tbody>
    </table>

    <div id="footerContent" class="footer">
        Generated by StorSageHQ Intelligence Engine | Page <pdf:pagenumber>
    </div>

</body>
</html>
"""

def generate_pdf_report(financial_metrics, market_data, competitors, lat, lon, unit_mix_data=None, image_paths=None):
    """
    Generates a PDF report using xhtml2pdf and Jinja2.
    """
    
    # 1. HELPER: Score Bar Logic
    def render_score_bar(score_val):
        """Returns HTML string for a colored progress bar (input 0-25)."""
        # Normalize to percentage width (max score 25)
        width_pct = min(100, (score_val / 25) * 100)
        
        # Color Logic
        if score_val >= 20: color = "#28a745" # Green
        elif score_val >= 15: color = "#17a2b8" # Teal
        elif score_val >= 10: color = "#ffc107" # Yellow
        else: color = "#dc3545" # Red
        
        return f"""
        <div style="width: 100%; background-color: #e9ecef; border-radius: 4px; height: 12px;">
            <div style="width: {width_pct}%; background-color: {color}; height: 100%; border-radius: 4px;"></div>
        </div>
        """

    # 2. PREPARE UNIT MIX DATA
    unit_sqft_map = {
        "5x5": 25, "10x10": 100, "10x20": 200, 
        "Climate": 100, "Boat_RV": 360
    }
    
    mix_rows = []
    total_sqft = 0
    total_units = 0
    market_profile = "Standard"

    if unit_mix_data and 'recommended_units' in unit_mix_data:
        rec_units = unit_mix_data['recommended_units']
        market_profile = unit_mix_data.get('market_profile', 'Standard')
        
        # First Pass: Calculate Total SqFt for % CALC
        temp_rows = []
        current_total_sqft = 0
        
        for u_type, count in rec_units.items():
            sqft_per = unit_sqft_map.get(u_type, 100)
            row_sqft = count * sqft_per
            current_total_sqft += row_sqft
            
            # Determine Display Name & Category
            is_cc = "Yes" if u_type == "Climate" else "No"
            # Format clean name (e.g. 5x5 -> 5' x 5')
            clean_name = u_type
            if 'x' in u_type:
                clean_name = u_type.replace('x', "' x ") + "'"
            
            temp_rows.append({
                "size": clean_name,
                "type": "Climate" if u_type == "Climate" else "Std",
                "count": count,
                "sqft_per": sqft_per,
                "total_sqft": row_sqft
            })
            total_units += count
        
        total_sqft = current_total_sqft
        
        # Second Pass: Add % and Format
        for r in temp_rows:
            pct = (r['total_sqft'] / total_sqft) * 100 if total_sqft > 0 else 0
            mix_rows.append({
                **r,
                "pct_nrsf": f"{pct:.1f}",
                "total_sqft": f"{r['total_sqft']:,}"
            })

    # 3. RECOMMENDATION LOGIC
    yoc = financial_metrics.get('Yield on Cost', 0)
    if yoc >= 8.0:
        rec = "PROCEED"
        rec_color = "#28a745"
    elif yoc >= 6.5:
        rec = "HOLD / MARGINAL"
        rec_color = "#ffc107"
    else:
        rec = "KILL DEAL"
        rec_color = "#dc3545"

    # 4. CONTEXT / EXEC SUMMARY
    pop = market_data.get("total_population", 0)
    exec_summary = (
        f"This feasibility study analyzes a potential self-storage development at ({lat}, {lon}). "
        f"The trade area features a population of {pop:,} with a calculated demand profile "
        f"supporting a project of this scale. The financial analysis indicates a Yield on Cost of {yoc}%, "
        f"resulting in a '{rec}' recommendation."
    )

    # 5. RENDER TEMPLATE
    context = {
        "lat": lat,
        "lon": lon,
        "report_date": datetime.now().strftime("%B %d, %Y"),
        "exec_summary": exec_summary,
        "recommendation": rec,
        "rec_color": rec_color,
        "yield_on_cost": yoc,
        "equity_created": f"{financial_metrics.get('Equity Created', 0):,.0f}",
        "stabilize_value": f"{financial_metrics.get('Stabilized Value', 0):,.0f}",
        
        # Demographics
        "market_data": market_data,
        "pop": f"{pop:,}",
        "growth": f"{market_data.get('growth_rate_annual', 0):.2%}",
        "income": f"${market_data.get('median_household_income', 0):,}",
        "renter": f"{market_data.get('renter_pct', 0):.1%}",
        "age": f"{market_data.get('median_age', 0)}",
        
        "scores": market_data.get('scores', {}),
        "score_bar": render_score_bar, # Pass function
        "unit_mix_rows": mix_rows,
        "total_units": total_units,
        "total_sqft": f"{total_sqft:,.0f}",
        "market_profile": market_profile
    }
    
    template = Template(REPORT_TEMPLATE)
    html_out = template.render(context)
    
    # 6. GENERATE PDF
    pdf_file = io.BytesIO()
    pisa_status = pisa.CreatePDF(
        src=io.BytesIO(html_out.encode("utf-8")),
        dest=pdf_file
    )
    
    if pisa_status.err:
        print(f"PDF Error: {pisa_status.err}")
        return None
        
    return pdf_file.getvalue()
