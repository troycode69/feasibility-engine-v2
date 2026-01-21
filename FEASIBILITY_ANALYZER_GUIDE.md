# Intelligent Feasibility Analyzer Guide

## Overview

The **FeasibilityAnalyzer** is an intelligent underwriting tool that combines market feasibility scoring with financial projections to produce clear **PURSUE / CAUTION / PASS** recommendations for self-storage acquisition opportunities.

## How It Works

### 1. Market Scoring (100 Points)

The analyzer uses a strict rubric across 5 categories:

| Category | Max Points | Key Metrics |
|----------|------------|-------------|
| **Demographics** | 25 | Population, income, growth, renters, age |
| **Supply Analysis** | 25 | SF/capita, occupancy, absorption, pipeline |
| **Site Attributes** | 25 | Visibility, access, zoning, site size |
| **Competitor Analysis** | 15 | Count, quality, pricing power |
| **Economic Indicators** | 10 | Unemployment, business growth, stability |

### 2. Financial Overlay

The analyzer also evaluates financial metrics:

- **Yield on Cost (YOC)**: Target 7-9%+
- **Equity Multiple**: Target 1.8-2.5x+
- **Stabilized Value**
- **Equity Created**

### 3. Decision Logic

#### Base Recommendation (Market Score)
- **80+ points** → PURSUE (High Confidence)
- **65-79 points** → CAUTION (Moderate Confidence)
- **<65 points** → PASS (Low Confidence)

#### Financial Adjustments
- **Strong financials** (YOC ≥8.5%, Equity ≥2.0x) can upgrade CAUTION → PURSUE
- **Weak financials** (YOC <6.5%, Equity <1.5x) can downgrade CAUTION → PASS

### 4. AI Narrative (Optional)

If `ANTHROPIC_API_KEY` is set, the analyzer generates an intelligent narrative explaining:
- Why this decision was made
- Critical factors driving the recommendation
- Specific risks or opportunities to monitor
- Concrete next steps

## Usage

### In Code

```python
from feasibility_analyzer import FeasibilityAnalyzer

# Initialize
analyzer = FeasibilityAnalyzer()

# Market analysis
demographics = {
    'population': 75000,
    'income': 65000,
    'growth': 2.5,      # % annual growth
    'renter_pct': 45,
    'age_pct': 42       # % aged 25-54
}

supply = {
    'sf_per_capita': 5.2,
    'occupancy': 88,
    'absorption_trend': 'Strong',  # Strong/Moderate/Weak/Declining
    'pipeline': 0.8    # Pipeline SF per capita
}

site = {
    'visibility': 'Good',           # Excellent/Good/Fair/Poor
    'access': 'Excellent',
    'zoning': 'Permitted',          # Permitted/Conditional/Requires Variance
    'size': 'Ideal'                 # Ideal/Adequate/Marginal/Insufficient
}

competitor = {
    'count': 4,                     # Within 3 miles
    'quality': 'Average',           # Aging/Poor, Average, Modern/Strong
    'pricing': 'At Market'          # Above Market/At Market/Below Market
}

economic = {
    'unemployment': 4.2,            # %
    'business_growth': 'Moderate',  # Strong/Moderate/Weak
    'stability': 'Stable'           # Stable/Moderate/Volatile
}

# Run market analysis
market_results = analyzer.analyze_market(demographics, supply, site, competitor, economic)

# Run financial analysis
financial_results = analyzer.analyze_financials(
    land_cost=1_000_000,
    construction_cost_psf=45,
    rentable_sqft=60000,
    avg_rent_psf=1.25
)

# Get final recommendation
recommendation = analyzer.get_recommendation(
    address="123 Main St, Dallas, TX",
    market_data={'demographics': demographics}
)

print(f"Decision: {recommendation['decision']}")
print(f"Confidence: {recommendation['confidence']}")
print(f"Market Score: {recommendation['market_score']}/100")
print(f"\nNarrative:\n{recommendation['narrative']}")
```

### In Streamlit App

The analyzer is automatically integrated into the **Market Feasibility** page. When you run an analysis:

1. Navigate to **1_Market_Feasibility** page
2. The recommendation appears prominently at the top
3. View the decision, market score, and yield on cost
4. Expand "View Detailed Score Breakdown" to see category-by-category scoring

## Testing

Run the test suite to see example scenarios:

```bash
python test_analyzer.py
```

This runs three test cases:
- **Strong Market** (100/100 score) → PURSUE
- **Moderate Market** (60/100 score) → CAUTION or PASS based on financials
- **Weak Market** (21/100 score) → PASS

## Output Example

```
🎯 UNDERWRITING RECOMMENDATION: PURSUE

Market Score: 85/100 (+20 vs threshold)
Yield on Cost: 9.2%
Confidence: High

RECOMMENDATION NARRATIVE:

Based on comprehensive market and financial analysis, we recommend PURSUING
this self-storage acquisition opportunity at 123 Main St, Dallas, TX.

Market Fundamentals (85/100):
The market demonstrates strong demographic tailwinds with a population of 75,000
within 3 miles, median household income of $65,000, and healthy 2.5% annual growth.
Supply metrics are favorable with 5.2 SF/capita and 88% average occupancy, indicating
balanced market conditions without oversaturation.

Financial Performance:
The pro forma projects a 9.2% yield on cost and 2.3x equity multiple at stabilization,
well above institutional return thresholds. With $3.2M in projected equity creation
on a $4.7M total development cost, the risk-adjusted returns justify capital deployment.

Key Risks to Monitor:
- Pipeline supply: 0.8 SF/capita could pressure rents if multiple projects deliver simultaneously
- 4 existing competitors within 3 miles require aggressive pre-leasing strategy

Next Steps:
1. Submit LOI at $1.0M land basis (contingent on zoning/entitlements)
2. Commission Phase I ESA and ALTA survey within 30 days
3. Engage architect for preliminary site plan to validate 60,000 NRA assumption
4. Begin due diligence on local zoning and SUP requirements
```

## Configuration

### Environment Variables

- `ANTHROPIC_API_KEY` (optional): Enables AI narrative generation via Claude API

### Customization

To adjust decision thresholds, modify `get_recommendation()` in `feasibility_analyzer.py`:

```python
# Market Score Thresholds
if self.market_score >= 80:      # PURSUE threshold
    decision = "PURSUE"
elif self.market_score >= 65:    # CAUTION threshold
    decision = "CAUTION"
else:
    decision = "PASS"

# Financial Thresholds
if yoc >= 8.5 and equity_mult >= 2.0:  # Strong returns
    # Upgrade CAUTION → PURSUE
```

## Architecture

```
FeasibilityAnalyzer
├── Market Scoring (scoring_logic.py)
│   ├── Demographics (25 pts)
│   ├── Supply (25 pts)
│   ├── Site (25 pts)
│   ├── Competitor (15 pts)
│   └── Economic (10 pts)
│
├── Financial Analysis (financials.py)
│   ├── Yield on Cost
│   ├── Equity Multiple
│   ├── Pro Forma (7-year)
│   └── Stabilized Value
│
└── Recommendation Engine
    ├── Decision Logic (PURSUE/CAUTION/PASS)
    ├── Confidence Level
    ├── Key Reasons
    └── AI Narrative (optional)
```

## Files

- **`src/feasibility_analyzer.py`** - Main analyzer class
- **`src/scoring_logic.py`** - Market scoring rubric (100-point system)
- **`src/financials.py`** - Financial modeling and pro forma
- **`src/1_Market_Feasibility.py`** - Streamlit integration
- **`test_analyzer.py`** - Test suite with example scenarios

## Next Steps

Potential enhancements:
- [ ] Add sensitivity analysis (stress testing)
- [ ] Export recommendation as PDF report
- [ ] Historical tracking of recommendations vs actual performance
- [ ] Machine learning overlay for scoring calibration
- [ ] Integration with acquisition pipeline CRM
