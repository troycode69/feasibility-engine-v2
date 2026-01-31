"""
LLM Report Generator for Self-Storage Feasibility Analysis

This module uses Claude API to generate intelligent, narrative-driven
feasibility report sections by synthesizing all data sources:
- Site scoring (100-point system)
- Financial projections (IRR, NPV, Cap Rate)
- Market analysis (supply/demand, competitors)
- Demographics and economic indicators

Outputs professional report sections matching the StorSageHQ template.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
import json
import os
from datetime import datetime


@dataclass
class ReportData:
    """Complete data package for LLM report generation"""
    # Project basics
    project_name: str = ""
    site_address: str = ""
    analysis_date: str = ""

    # Scoring data
    site_score: Dict = field(default_factory=dict)

    # Financial data
    financial_metrics: Dict = field(default_factory=dict)

    # Market analysis
    market_analysis: Dict = field(default_factory=dict)

    # Competitor data
    competitor_analysis: Dict = field(default_factory=dict)

    # Demographics
    demographics: Dict = field(default_factory=dict)

    # Proposed project details
    proposed_nrsf: int = 0
    proposed_unit_mix: Dict = field(default_factory=dict)

    def to_json(self) -> str:
        """Convert to JSON string for LLM context"""
        return json.dumps({
            "project_name": self.project_name,
            "site_address": self.site_address,
            "analysis_date": self.analysis_date,
            "site_score": self.site_score,
            "financial_metrics": self.financial_metrics,
            "market_analysis": self.market_analysis,
            "competitor_analysis": self.competitor_analysis,
            "demographics": self.demographics,
            "proposed_nrsf": self.proposed_nrsf,
            "proposed_unit_mix": self.proposed_unit_mix
        }, indent=2)


# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

SYSTEM_PROMPT = """You are a senior self-storage feasibility consultant at StorSageHQ, a premier consulting firm trusted by institutional investors, REITs, and private developers. Write like a human expert presenting to sophisticated investors and lenders who will make multi-million dollar decisions based on your analysis.

Your Analysis Style:
- NARRATIVE-DRIVEN: Tell a compelling story about this market and opportunity. Don't just list data points - explain what they mean and why they matter. Connect the dots for the reader.
- STRATEGICALLY INSIGHTFUL: Go beyond surface metrics. Explain the implications of each finding. What does 6.2 SF/capita actually tell us about demand absorption? What does 88% occupancy signal about pricing power?
- PROFESSIONALLY AUTHORITATIVE: Use industry terminology correctly (NRSF, NOI, DSCR, cap rate, IRR, lease-up, absorption, rate compression). Your reader knows the industry - write at their level.
- BALANCED AND HONEST: Acknowledge both opportunities AND risks with equal rigor. Never oversell. Sophisticated readers respect candor over optimism.
- ACTION-ORIENTED: Every section should build toward clear recommendations. What should the investor DO with this information?

Voice and Tone:
- Confident but not arrogant. You're presenting expert analysis, not guessing.
- Direct and concise. Remove filler words and unnecessary qualifiers.
- Specific to THIS project. Avoid generic statements that could apply to any site.
- Data-forward. Lead with numbers, then explain their significance.

CRITICAL: Match the tone, depth, and professionalism of the StorSageHQ example study provided. Your output will be compared directly against that standard."""


EXECUTIVE_SUMMARY_PROMPT = """Based on the comprehensive feasibility analysis data provided, write a compelling Executive Summary for this self-storage development project.

The Executive Summary should be 2-3 paragraphs that:

1. **Opening Statement** (1 paragraph):
   - State the project scope (location, size, concept)
   - Present the overall site score and recommendation (PROCEED / PROCEED WITH CAUTION / DO NOT PROCEED)
   - Highlight 1-2 most compelling strengths

2. **Key Findings** (1 paragraph):
   - Summarize the 3-4 most critical data points across scoring categories
   - Reference specific metrics (demographics, supply/demand, financial returns)
   - Explain what makes this opportunity unique or challenging

3. **Bottom Line** (1 paragraph):
   - Restate the recommendation with confidence level
   - Identify the single biggest opportunity and the single biggest risk
   - Suggest immediate next steps if proceeding

Data Context:
{data}

Write the Executive Summary now:"""


MARKET_ANALYSIS_PROMPT = """Based on the market analysis data provided, write a comprehensive Market Analysis section that covers:

1. **Market Overview** (2-3 paragraphs):
   - Geographic market definition (1-mile, 3-mile, 5-mile radii)
   - Current supply metrics (total SF, facility count, SF per capita)
   - Market balance assessment (undersupplied / balanced / oversupplied)

2. **Demographic Profile** (2 paragraphs):
   - Population and household counts by radius
   - Income levels and renter-occupied housing percentage
   - Growth trends and what they mean for storage demand

3. **Competitive Landscape** (2-3 paragraphs):
   - Number of competitors by distance
   - Competitive density analysis
   - Rate competitiveness and market positioning
   - Quality/age assessment of existing facilities if data available

4. **Supply/Demand Dynamics** (2 paragraphs):
   - SF per capita compared to industry benchmarks (5-7 SF/capita balanced)
   - Supply gap or surplus calculation
   - Development pipeline risks
   - Market saturation score interpretation

5. **Market Scoring Summary** (1 paragraph):
   - Demographics score and key drivers
   - Supply/Demand score and key drivers
   - Overall market opportunity assessment

Use specific numbers from the data. Explain WHY the metrics matter, not just WHAT they are.

Data Context:
{data}

Write the Market Analysis section now:"""


FINANCIAL_ANALYSIS_PROMPT = """Based on the financial projections provided, write a comprehensive Financial Feasibility section that covers:

1. **Development Budget Overview** (1 paragraph):
   - Total development cost breakdown (land, hard costs, soft costs)
   - Cost per NRSF
   - How it compares to regional benchmarks

2. **Revenue Assumptions** (1 paragraph):
   - Gross Potential Revenue at stabilization
   - Average rate per SF and how it positions vs. market
   - Stabilized occupancy assumption and rationale

3. **Operating Expense Projections** (1 paragraph):
   - Total operating expenses as % of GPR
   - Major expense categories
   - How expense ratio compares to industry benchmarks by facility size

4. **Key Financial Metrics** (2 paragraphs):
   - Net Operating Income at stabilization
   - Cap Rate and interpretation (good/fair/weak for self-storage)
   - Debt Service Coverage Ratio (DSCR) and lender acceptability (1.25+ required)
   - Break-even occupancy and risk assessment
   - Cash-on-cash return in early years

5. **Investment Returns** (2 paragraphs):
   - 10-year IRR and what it means for investor returns
   - NPV and value creation
   - Equity multiple over holding period
   - Comparison to industry return benchmarks (self-storage IRR typically 12-18%)

6. **Financial Risk Assessment** (1 paragraph):
   - Key financial risks identified (e.g., high break-even, low DSCR, weak returns)
   - Sensitivity to occupancy and rate assumptions
   - Lender concerns if any

Be honest about financial strengths and weaknesses. If returns are weak, say so and explain why.

Data Context:
{data}

Write the Financial Feasibility section now:"""


SITE_SCORING_PROMPT = """Based on the 100-point site scoring data provided, write a comprehensive Site Scoring System section that covers:

1. **Introduction** (1 paragraph):
   - Explain the 100-point scoring methodology
   - State the overall score and tier (Excellent 85-100 / Good 70-84 / Fair 55-69 / Weak 40-54 / Poor 0-39)
   - Preview the five scoring categories

2. **Demographics Scoring** (1 paragraph, ___ / 25 points):
   - Overall demographics score
   - Break down the 5 sub-metrics with points earned:
     * Population (3-mile radius) - score/5 and value
     * Growth Rate - score/5 and value
     * Median Income - score/5 and value
     * Renter-Occupied % - score/5 and value
     * Age Demographics - score/5 and value
   - Explain strongest and weakest demographic factors

3. **Supply/Demand Scoring** (1 paragraph, ___ / 25 points):
   - Overall supply/demand score
   - Break down the 5 sub-metrics with points earned
   - Interpret SF per capita in context
   - Highlight competitive density findings

4. **Site Attributes Scoring** (1 paragraph, ___ / 25 points):
   - Overall site attributes score
   - Break down visibility, traffic count, access, lot size, zoning
   - Explain physical advantages or disadvantages

5. **Competitive Positioning Scoring** (1 paragraph, ___ / 15 points):
   - Rate competitiveness vs. market
   - Product differentiation opportunities
   - Brand strength assessment

6. **Economic Market Scoring** (1 paragraph, ___ / 10 points):
   - Unemployment rate
   - Job growth trends
   - GDP/economic growth

7. **Scoring Summary** (1 paragraph):
   - Total score: __ / 100
   - Overall tier and recommendation
   - Key scoring strengths (highest point categories)
   - Key scoring weaknesses (lowest point categories)

Use the exact scores from the data. Show the math clearly.

Data Context:
{data}

Write the Site Scoring System section now:"""


RECOMMENDATION_PROMPT = """Based on all the analysis data provided (scoring, financials, market analysis), write a comprehensive Conclusion & Recommendation section that covers:

1. **Overall Assessment** (1 paragraph):
   - Synthesize the complete picture: site score, financial returns, market dynamics
   - State clear recommendation: GO / GO WITH CAUTION / NO-GO
   - Provide confidence level: High / Standard / Low

2. **Key Strengths** (1 paragraph, bullet format):
   - List 3-5 most compelling positive factors
   - Be specific with data points
   - Explain why each strength matters

3. **Key Risks & Challenges** (1 paragraph, bullet format):
   - List 3-5 most significant concerns
   - Quantify risks where possible
   - Assess likelihood and impact

4. **Critical Success Factors** (1 paragraph):
   - What must go right for this project to succeed?
   - What are the most important assumptions to validate?
   - What execution risks need mitigation?

5. **Recommended Next Steps** (1 paragraph, numbered list):
   - If GO: Immediate action items (due diligence, entitlements, financing, etc.)
   - If CAUTION: Additional analysis needed before committing
   - If NO-GO: Alternative strategies or market considerations
   - Prioritize top 3-5 next steps

6. **Final Verdict** (1-2 sentences):
   - One clear statement on whether to proceed
   - Confidence percentage (e.g., "82% confidence this project will succeed")

Be direct and actionable. This is the executive decision-making section.

Data Context:
{data}

Write the Conclusion & Recommendation section now:"""


RISK_ASSESSMENT_PROMPT = """Based on all analysis data, write a comprehensive Risk Assessment & Mitigation section that covers:

1. **Market Risks** (1 paragraph):
   - Oversupply or market saturation risks
   - Competitive intensity
   - Demand uncertainty (growth, demographics)
   - Rate pressure or pricing challenges

2. **Development & Construction Risks** (1 paragraph):
   - Cost overruns or budget risks
   - Timeline delays
   - Site-specific challenges (zoning, access, etc.)
   - Regional construction cost volatility

3. **Operational Risks** (1 paragraph):
   - Lease-up speed assumptions
   - Operating expense variability
   - Management execution
   - Local market knowledge gaps

4. **Financial Risks** (1 paragraph):
   - Interest rate sensitivity (if variable rate debt)
   - Exit cap rate risk
   - Break-even occupancy concerns
   - Debt service coverage tightness

5. **Mitigation Strategies** (1 paragraph, bullet format):
   - Specific actions to reduce each major risk category
   - De-risking tactics (pre-leasing, phasing, partnerships, etc.)
   - Contingency planning

Rate each risk category: LOW / MODERATE / HIGH

Data Context:
{data}

Write the Risk Assessment & Mitigation section now:"""


# ============================================================================
# CLAUDE API INTEGRATION
# ============================================================================

def call_claude_api(prompt: str, system_prompt: str = SYSTEM_PROMPT,
                   model: str = "claude-sonnet-4-5-20250929",
                   max_tokens: int = 4000) -> str:
    """
    Call Claude API to generate report section.

    Args:
        prompt: User prompt with data and instructions
        system_prompt: System prompt defining role and style
        model: Claude model ID
        max_tokens: Maximum response tokens

    Returns:
        Generated text
    """
    try:
        import anthropic
    except ImportError:
        return "ERROR: anthropic package not installed. Run: pip install anthropic"

    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "ERROR: ANTHROPIC_API_KEY environment variable not set"

    try:
        client = anthropic.Anthropic(api_key=api_key)

        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return response.content[0].text

    except Exception as e:
        return f"ERROR calling Claude API: {str(e)}"


def generate_executive_summary(report_data: ReportData, use_examples: bool = True) -> str:
    """Generate Executive Summary section"""
    prompt = EXECUTIVE_SUMMARY_PROMPT.format(data=report_data.to_json())

    # Add example studies if available
    if use_examples:
        try:
            from src.example_study_loader import load_example_studies, format_examples_for_prompt
            examples = load_example_studies()
            if examples:
                example_context = format_examples_for_prompt(examples, max_examples=2)
                prompt = example_context + prompt
        except Exception as e:
            print(f"Could not load example studies: {e}")

    return call_claude_api(prompt)


def generate_market_analysis(report_data: ReportData, use_examples: bool = True) -> str:
    """Generate Market Analysis section"""
    prompt = MARKET_ANALYSIS_PROMPT.format(data=report_data.to_json())

    # Add example studies for richer context
    if use_examples:
        try:
            from src.example_study_loader import load_example_studies, format_examples_for_prompt
            examples = load_example_studies()
            if examples:
                example_context = format_examples_for_prompt(examples, max_examples=2)
                prompt = example_context + prompt
        except Exception as e:
            print(f"Could not load example studies: {e}")

    return call_claude_api(prompt, max_tokens=6000)


def generate_financial_analysis(report_data: ReportData, use_examples: bool = True) -> str:
    """Generate Financial Feasibility section"""
    prompt = FINANCIAL_ANALYSIS_PROMPT.format(data=report_data.to_json())

    # Add example studies for richer context
    if use_examples:
        try:
            from src.example_study_loader import load_example_studies, format_examples_for_prompt
            examples = load_example_studies()
            if examples:
                example_context = format_examples_for_prompt(examples, max_examples=2)
                prompt = example_context + prompt
        except Exception as e:
            print(f"Could not load example studies: {e}")

    return call_claude_api(prompt, max_tokens=5000)


def generate_site_scoring(report_data: ReportData, use_examples: bool = True) -> str:
    """Generate Site Scoring System section"""
    prompt = SITE_SCORING_PROMPT.format(data=report_data.to_json())

    # Add example studies for richer context
    if use_examples:
        try:
            from src.example_study_loader import load_example_studies, format_examples_for_prompt
            examples = load_example_studies()
            if examples:
                example_context = format_examples_for_prompt(examples, max_examples=2)
                prompt = example_context + prompt
        except Exception as e:
            print(f"Could not load example studies: {e}")

    return call_claude_api(prompt, max_tokens=5000)


def generate_recommendation(report_data: ReportData, use_examples: bool = True) -> str:
    """Generate Conclusion & Recommendation section"""
    prompt = RECOMMENDATION_PROMPT.format(data=report_data.to_json())

    # Add example studies for richer context
    if use_examples:
        try:
            from src.example_study_loader import load_example_studies, format_examples_for_prompt
            examples = load_example_studies()
            if examples:
                example_context = format_examples_for_prompt(examples, max_examples=2)
                prompt = example_context + prompt
        except Exception as e:
            print(f"Could not load example studies: {e}")

    return call_claude_api(prompt, max_tokens=4000)


def generate_risk_assessment(report_data: ReportData, use_examples: bool = True) -> str:
    """Generate Risk Assessment & Mitigation section"""
    prompt = RISK_ASSESSMENT_PROMPT.format(data=report_data.to_json())

    # Add example studies for richer context
    if use_examples:
        try:
            from src.example_study_loader import load_example_studies, format_examples_for_prompt
            examples = load_example_studies()
            if examples:
                example_context = format_examples_for_prompt(examples, max_examples=2)
                prompt = example_context + prompt
        except Exception as e:
            print(f"Could not load example studies: {e}")

    return call_claude_api(prompt, max_tokens=4000)


def generate_complete_report(report_data: ReportData) -> Dict[str, str]:
    """
    Generate all report sections.

    Args:
        report_data: Complete ReportData package

    Returns:
        Dict mapping section names to generated content
    """
    print("Generating feasibility report sections using Claude API...")
    print(f"Project: {report_data.project_name}")
    print(f"Site: {report_data.site_address}\n")

    sections = {}

    print("  [1/6] Generating Executive Summary...")
    sections["executive_summary"] = generate_executive_summary(report_data)

    print("  [2/6] Generating Site Scoring Analysis...")
    sections["site_scoring"] = generate_site_scoring(report_data)

    print("  [3/6] Generating Market Analysis...")
    sections["market_analysis"] = generate_market_analysis(report_data)

    print("  [4/6] Generating Financial Analysis...")
    sections["financial_analysis"] = generate_financial_analysis(report_data)

    print("  [5/6] Generating Risk Assessment...")
    sections["risk_assessment"] = generate_risk_assessment(report_data)

    print("  [6/6] Generating Recommendation...")
    sections["recommendation"] = generate_recommendation(report_data)

    print("\n✓ Report generation complete!\n")

    return sections


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=== LLM Report Generator Test ===\n")

    # Create sample report data
    sample_data = ReportData(
        project_name="Poughkeepsie Storage Center",
        site_address="123 Main Street, Poughkeepsie, NY 12601",
        analysis_date=datetime.now().strftime("%Y-%m-%d"),
        site_score={
            "total_score": 78,
            "tier": "Good",
            "recommendation": "PROCEED",
            "confidence": "Standard Confidence",
            "demographics": {
                "total_score": 20,
                "max_score": 25,
                "population_3mi": 61297,
                "population_3mi_score": 4,
                "growth_rate": 0.37,
                "growth_rate_score": 2,
                "median_income": 77883,
                "median_income_score": 4,
                "renter_occupied_pct": 46.1,
                "renter_occupied_pct_score": 5,
                "median_age": 38.6,
                "median_age_score": 5
            },
            "supply_demand": {
                "total_score": 18,
                "max_score": 25,
                "sf_per_capita": 5.8,
                "existing_occupancy_avg": 88.0,
                "distance_to_nearest": 1.2
            }
        },
        financial_metrics={
            "total_development_cost": 7932500,
            "noi_stabilized": 509760,
            "cap_rate": 6.43,
            "dscr": 1.06,
            "break_even_occupancy": 91.8,
            "irr_10yr": 3.74,
            "cash_on_cash_yr1": -14.81
        },
        proposed_nrsf=60000
    )

    # Test if API key is available
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠ ANTHROPIC_API_KEY not set - cannot test API calls")
        print("To test LLM generation, set your API key:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        print("\nPrompt templates are ready. Example prompt:")
        print("\n" + "="*70)
        print(EXECUTIVE_SUMMARY_PROMPT.format(data=sample_data.to_json())[:500] + "...")
    else:
        print("✓ API key found - testing report generation...\n")

        # Generate just the executive summary as a test
        print("Generating Executive Summary (this will cost ~$0.01)...")
        summary = generate_executive_summary(sample_data)

        print("\n" + "="*70)
        print("EXECUTIVE SUMMARY")
        print("="*70)
        print(summary)
        print("="*70)
