# Storage OS - 7 Year Projection Implementation Plan

**Date:** January 20, 2026
**Objective:** Replicate Excel "7 Year Projection" sheet in Streamlit app with intelligent feasibility analysis

---

## Executive Summary

### Current State
- **Excel Model:** Sophisticated 15-sheet workbook with 84-month projections, attrition modeling, and comprehensive financial analysis
- **Current App:** Basic LeaseUpModel with S-curve lease-up and simplified attrition
- **Gap:** App lacks the Excel model's layout, detail level, and business intelligence

### Target State
- **Exact Excel Layout:** Replicate the "7 Year Projection" sheet structure (53 rows × annual columns)
- **Intelligent Analysis:** AI-driven feasibility recommendations based on market data + financial projections
- **Address-to-Proforma:** User enters address → Full feasibility study + 7-year projection

---

## Excel Model Analysis Summary

### Model Strengths
1. **Monthly Granularity:** 84+ months of detailed calculations
2. **Realistic Attrition:** Historical vacancy rates by tenant cohort age (1-12+ months)
3. **Comprehensive Expenses:** 40+ expense line items with GL codes
4. **Property-Specific Logic:** Conditional expenses based on characteristics (multi-story → elevator costs)
5. **Dual Rate Strategy:** New move-ins (4% annual growth) vs existing tenants (12% increases)
6. **Investment Metrics:** NOI, DSCR, Cap Rate, Cash-on-Cash, Yield

### Key Configuration (Current Excel)
- **Property:** 105,807 SF, 684 units, 100% climate controlled
- **New Development:** Starts at 0% occupancy
- **Lease-Up:** 33% (Yr1) → 68% (Yr2) → 92% (Yr3+)
- **Starting Rate:** $18.60/mo ($1.55/SF/mo or $18.60/SF/yr)
- **Financing:** $14.9M purchase, 65% LTV, 7.5% interest, 25-year amortization

---

## "7 Year Projection" Sheet Structure

### Section 1: Occupancy & Activity Metrics (Rows 10-19)
| Row | Code | Description | Type |
|-----|------|-------------|------|
| 10 | MI | Rentals | Sum of monthly move-ins |
| 11 | MO | Vacates | Sum of monthly move-outs |
| 12 | Net | Net Rentals | Rentals - Vacates |
| 13 | RentEnd | Rented Units (EoM) | Ending occupied units |
| 14 | - | === Occupancy === | Section header |
| 15 | SFRent | Sq. Feet Rented | Average SF rented |
| 16 | SFOcc% | Avg. Square Foot Occupancy | SF Rented / Total SF |
| 18 | AvgRentRate | Avg. Rent Rate on Rentals | Rate for new move-ins |
| 19 | IPRPSF | In-Place Rate | Weighted avg of all occupied |

### Section 2: Revenue (Rows 21-26)
| Row | Code | Description | Calculation |
|-----|------|-------------|-------------|
| 21 | 4100 | Rental Income | Occupied SF × Rate |
| 22 | 4700 | Discounts | -2.5% of rental income |
| 23 | 7101 | Write Off | -1.0% of rental income |
| 24 | NetRentInc | Net Rental Income | Sum of 21-23 |
| 25 | Total Ancillary | Ancillary Income | Insurance, fees, merch |
| 26 | - | === Property Revenue === | Total revenue |

### Section 3: Expenses (Rows 28-37)
| Row | Code | Description | Basis |
|-----|------|-------------|-------|
| 28 | Total Personnel | Payroll | Salaries + benefits |
| 29 | Total Utility | Utilities | Electric, water, gas |
| 30 | Total Other Op | Operating Expenses | Supplies, fees, CC fees |
| 31 | 6171 | Landscaping | $/year |
| 32 | Total R&M | Repairs & Maintenance | All R&M categories |
| 33 | Total Marketing | Marketing | Ad spend |
| 34 | 6270 | Taxes | Real estate taxes |
| 35 | 6280 | Insurance | Property insurance |
| 36 | 6801 | Management Fees | % of revenue |
| 37 | 7550 | Land Lease | Ground lease (if any) |

### Section 4: Key Metrics (Rows 38-53)
| Row | Description | Formula |
|-----|-------------|---------|
| 38 | === Property Expenses === | Sum of rows 28-37 |
| 40 | === Property NOI === | Revenue - Expenses |
| 42 | === Total Debt Service === | P&I payments |
| 44 | === Levered Cash Flow === | NOI - Debt Service |
| 46-49 | Loan Balance Detail | Beginning, Interest, Principal, Ending |
| 50 | === DSCR === | NOI / Debt Service |
| 51 | === Cap Rate === | NOI / Purchase Price |
| 52 | === Cash on Cash Return === | Levered CF / Equity |
| 53 | === Yield on Cash === | Alternative return metric |

### Column Layout
- **Column D:** Line item descriptions
- **Columns G-R:** Months 1-12 for Year 1
- **Column S:** Year 1 Total
- **Column T:** Year 2 Total
- **Column U:** Year 3 Total
- **Column V:** Year 4 Total
- **Column W:** Year 5 Total
- **Column X:** Year 6 Total
- **Column Y:** Year 7 Total

---

## Current App Implementation

### Existing Capabilities ✅
1. **LeaseUpModel class** with cohort-based attrition
2. **S-curve lease-up** to stabilization
3. **Seasonality factors** for revenue and expenses
4. **Monthly projections** (84 months)
5. **Annual summary** aggregation
6. **Basic display** of key metrics and charts

### Gaps vs Excel Model ❌
1. **Layout:** Current display is simple table, not Excel's structured format
2. **Detail Level:** Missing detailed revenue/expense breakouts
3. **Rate Strategy:** Single rate growth vs dual strategy (new vs existing)
4. **Expense Detail:** Simplified vs 40+ GL line items
5. **Attrition Sophistication:** Basic lookup vs rental cohort age tracking
6. **Ancillary Income:** 10% flat vs detailed fee/insurance modeling
7. **Investment Metrics:** Missing Cap Rate, Yield calculations
8. **Visual Match:** No formatting to match Excel appearance

---

## Implementation Roadmap

### Phase 1: Enhanced Data Model (Week 1)
**Objective:** Match Excel's calculation engine

#### Task 1.1: Expand LeaseUpModel Calculations
- [ ] Add dual rate strategy (new move-ins vs existing tenant increases)
- [ ] Implement detailed ancillary income:
  - Admin fees ($15/rental)
  - Late fees (0.1% of RI)
  - Insurance (penetration rate × premium)
  - Merchandise ($2.50/rental)
- [ ] Add comprehensive expense detail (40+ line items with GL codes)
- [ ] Implement property characteristic conditionals:
  - Multi-story → Elevator R&M
  - Golf cart → Golf cart R&M
  - Climate controlled → Higher utilities

#### Task 1.2: Enhance Attrition Modeling
- [ ] Track rental cohorts by month of rental (not just month number)
- [ ] Apply vacancy rates based on tenant cohort age (months since move-in)
- [ ] Implement full attrition table lookup (rental_month × vacate_month)

#### Task 1.3: Add Missing Metrics
- [ ] Cap Rate calculation (NOI / Purchase Price for Yr1, then by value)
- [ ] Yield on Cash
- [ ] Cumulative cash flow
- [ ] IRR calculation (optional)

**Deliverable:** Enhanced `leaseup_model.py` with Excel-equivalent calculations

---

### Phase 2: Excel Layout Replication (Week 2)
**Objective:** Create visual match to "7 Year Projection" sheet

#### Task 2.1: Create Structured Display Component
```python
def render_7year_projection(annual_summary, property_info):
    """
    Render Excel-style 7 Year Projection sheet

    Structure:
    - Header: Property name, address, SF, units
    - Section 1: Occupancy & Activity (rows 10-19)
    - Section 2: Revenue (rows 21-26)
    - Section 3: Expenses (rows 28-37)
    - Section 4: Key Metrics (rows 38-53)

    Returns: Streamlit formatted display
    """
```

#### Task 2.2: Build Row-by-Row Display
- [ ] Create header section (rows 1-8)
- [ ] Build occupancy metrics table (rows 10-19)
- [ ] Build revenue waterfall (rows 21-26)
- [ ] Build expense breakdown (rows 28-37)
- [ ] Build metrics section (rows 38-53)
- [ ] Apply Excel-style formatting (bold headers, section breaks, etc.)

#### Task 2.3: Add Formatting & Styling
- [ ] Currency formatting ($X,XXX)
- [ ] Percentage formatting (XX.X%)
- [ ] Decimal precision (rates to 2 decimals)
- [ ] Section headers with dividers
- [ ] Highlight key metrics (NOI, DSCR, Cap Rate)

**Deliverable:** `render_7year_projection()` function in new file `src/projection_display.py`

---

### Phase 3: Intelligent Feasibility Analysis (Week 3)
**Objective:** AI-driven site evaluation and recommendations

#### Task 3.1: Design Feasibility Scoring Logic
Create comprehensive scoring system based on:

**Market Fundamentals (40 points)**
- Population density (10 pts)
- Household income levels (10 pts)
- Competitor density/saturation (10 pts)
- Market rental rates vs. projections (10 pts)

**Financial Performance (30 points)**
- Year 1 NOI vs target (10 pts)
- Stabilized DSCR (10 pts)
- Cash-on-Cash return (10 pts)

**Lease-Up Risk (20 points)**
- Months to stabilization vs market norm (10 pts)
- Year 1 occupancy achievement (10 pts)

**Location Factors (10 points)**
- Visibility/access (5 pts)
- Demographics match (5 pts)

**Total: 100 points**

#### Task 3.2: Create Recommendation Engine
```python
class FeasibilityRecommender:
    def __init__(self, market_data, financial_projection):
        self.market = market_data
        self.projection = financial_projection

    def analyze(self):
        """
        Returns:
        {
            'decision': 'PURSUE', 'CAUTION', or 'PASS',
            'score': 0-100,
            'breakdown': {...},
            'key_risks': [...],
            'key_strengths': [...],
            'recommendation_text': "..."
        }
        """
```

**Decision Matrix:**
- **90-100 pts:** STRONG PURSUE - Excellent opportunity
- **75-89 pts:** PURSUE - Solid opportunity with minor concerns
- **60-74 pts:** CAUTION - Proceed with modifications/further analysis
- **Below 60:** PASS - Fundamental issues, do not pursue

#### Task 3.3: Generate Narrative Reports
Use LLM to generate:
- Executive summary
- Detailed risk analysis
- Market positioning assessment
- Lease-up strategy recommendations
- Pricing strategy recommendations

**Deliverable:** `FeasibilityRecommender` class in `src/feasibility_recommender.py`

---

### Phase 4: Address-to-Proforma Workflow (Week 4)
**Objective:** Seamless flow from address input to full analysis

#### Task 4.1: Integrate Data Sources
Connect existing modules:
- Address input → Geocoding (`intelligence.py`)
- Geocoded location → Competitor analysis (`scraper.py`)
- Competitors → Market rate analysis
- Demographics → Population/income data (`demographics.py`)

#### Task 4.2: Auto-Populate Inputs
From market data, automatically suggest:
- Starting rental rate (based on competitor avg)
- Stabilized occupancy (based on market saturation)
- Months to stabilization (based on market strength)
- Total SF/units (user can override)

#### Task 4.3: One-Click Analysis
```
User Flow:
1. Enter address: "123 Main St, Anytown, USA"
2. Click "Analyze Site"
3. System:
   - Geocodes address
   - Pulls competitors within 5 mi
   - Analyzes demographics
   - Suggests property specs
4. User reviews/modifies inputs
5. Click "Generate Full Analysis"
6. System:
   - Runs 7-year projection
   - Calculates feasibility score
   - Generates recommendation
7. Display:
   - Feasibility score with decision
   - Excel-style 7 Year Projection
   - Detailed narrative report
   - Export to PDF
```

**Deliverable:** Updated `app.py` with integrated workflow

---

## Technical Requirements

### Data Files Needed
1. **Attrition Tables:** Full rental_month × vacate_month matrix
   - Currently: Simplified in `attrition_curves.json`
   - Needed: Extract from Excel "Attrition Modeling" sheet

2. **Expense Benchmark Data:**
   - Currently: Hardcoded in LeaseUpModel
   - Needed: Extract from Excel "Expense Comp Data" sheet
   - Store in: `data/expense_benchmarks.json`

3. **Rate Calculation Logic:**
   - Currently: Simple growth factor
   - Needed: Extract formulas from "Rate Calculation" sheet

### New Python Files
1. `src/projection_display.py` - Excel layout rendering
2. `src/feasibility_recommender.py` - Intelligent scoring and recommendations
3. `src/excel_exporter.py` - Export to Excel format
4. `src/pdf_generator.py` - PDF report generation

### Updates to Existing Files
1. `src/leaseup_model.py` - Enhanced calculations
2. `app.py` - Integrated workflow
3. `src/financials.py` - May consolidate with LeaseUpModel

---

## Success Criteria

### Must-Have (MVP)
- [ ] 7 Year Projection matches Excel layout exactly
- [ ] All 53 rows displayed with proper formatting
- [ ] Annual columns (Years 1-7) with totals
- [ ] Intelligent feasibility score (0-100)
- [ ] Clear recommendation (PURSUE/CAUTION/PASS)
- [ ] Address-to-proforma workflow functional

### Should-Have (V1.1)
- [ ] Monthly detail view (84 months)
- [ ] PDF export of full report
- [ ] Excel export of projections
- [ ] Sensitivity analysis (what-if scenarios)
- [ ] Comparison mode (multiple sites side-by-side)

### Nice-to-Have (V2.0)
- [ ] Unit mix optimization (5×5 vs 10×10 pricing)
- [ ] Real-time market rate updates (web scraping)
- [ ] Historical property performance tracking
- [ ] Portfolio view (multiple properties)
- [ ] AI chatbot for Q&A on projections

---

## Risk Mitigation

### Risk 1: Complex Attrition Logic
**Issue:** Excel uses array formulas that are hard to replicate
**Mitigation:** Extract attrition data to JSON, use pandas for lookups
**Status:** Partially done, needs enhancement

### Risk 2: Formula Dependencies
**Issue:** Excel formulas reference multiple sheets
**Mitigation:** Map all dependencies in analysis doc, implement in Python
**Status:** Analysis complete, implementation needed

### Risk 3: Performance (84 months × complex calcs)
**Issue:** May be slow for interactive use
**Mitigation:** Cache projections in session_state, only recalc on input change
**Status:** To be implemented

### Risk 4: Layout Replication
**Issue:** Streamlit tables may not match Excel appearance
**Mitigation:** Use custom HTML/CSS if needed, or use AgGrid component
**Status:** To be evaluated

---

## Next Steps

### Immediate (This Week)
1. **Extract attrition data** from Excel → JSON
2. **Extract expense benchmarks** from Excel → JSON
3. **Review and approve** this implementation plan
4. **Start Phase 1, Task 1.1** (Expand LeaseUpModel)

### Week 2
- Complete Phase 1 (Enhanced Data Model)
- Begin Phase 2 (Layout Replication)

### Week 3
- Complete Phase 2
- Begin Phase 3 (Feasibility Analysis)

### Week 4
- Complete Phase 3 & 4
- Testing and refinement
- Launch MVP

---

## Questions for Review

1. **Layout Priority:** Should we match Excel exactly, or modernize the UI while keeping the same data?
2. **Expense Detail:** Should we expose all 40+ expense lines to users, or keep simplified with "view details" option?
3. **Feasibility Weights:** Are the proposed weights (Market 40%, Financial 30%, Lease-Up 20%, Location 10%) appropriate?
4. **PDF Export:** What should the PDF report include? Full projection + feasibility analysis?
5. **Unit Mix:** Should we add unit mix detail (5×5, 10×10, 10×20 pricing) in V1 or defer to V2?

---

**Document Version:** 1.0
**Last Updated:** January 20, 2026
**Owner:** Troy Jarvis
**Next Review:** After Phase 1 completion
