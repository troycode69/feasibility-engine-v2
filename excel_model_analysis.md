# Self Storage 7 Year Financial Model - Complete Analysis

**Analysis Date:** 2026-01-20 21:18:47
**Model File:** Self Storage 7 Year Model.xlsx

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Workbook Structure](#workbook-structure)
3. [Input Parameters](#input-parameters)
4. [7 Year Projection Output Structure](#7-year-projection-output-structure)
5. [Data Flow & Calculation Logic](#data-flow--calculation-logic)
6. [Lease-Up Modeling](#lease-up-modeling)
7. [Key Formulas & Business Logic](#key-formulas--business-logic)

---

## Executive Summary

This Excel workbook is a comprehensive self-storage financial projection model that forecasts performance over a 7-year period. It includes:

- Monthly projections with annual summaries
- Detailed lease-up modeling with attrition analysis
- Revenue and expense forecasting
- Debt service and cash flow analysis
- Investment returns (NOI, Cap Rate, Cash-on-Cash, DSCR)

The model supports both new development and existing property analysis with configurable inputs for occupancy ramp-up, rental rates, operating expenses, and financing terms.

---

## Workbook Structure

The model contains **15 worksheets**:

### 1. **How to**
   - User guide and instructions (minimal content)

### 2. **Summary**
   - High-level summary dashboard
   - Dimensions: 32 rows × 14 columns

### 3. **Inputs** ⭐ PRIMARY INPUT SHEET
   - All user-configurable parameters
   - Property information, occupancy assumptions, rates, expenses
   - Dimensions: 277 rows × 32 columns
   - Sections:
     - Basic Info (Address, property details)
     - Current Property Info (SF, units, occupancy)
     - Long-term Growth Assumptions
     - Acquisition & Financing
     - Property Characteristics
     - Occupancy Inputs (lease-up curve)
     - Rate Inputs (starting rates, annual increases)
     - Revenue Assumptions (discounts, fees, ancillary income)
     - Expense Assumptions (payroll, utilities, R&M, marketing, taxes, insurance)
     - Capital Expenditures

### 4. **Projection** ⭐ MONTHLY CALCULATION ENGINE
   - Month-by-month detailed projections
   - Dimensions: 372 rows × 109 columns (9+ years of monthly data)
   - Calculates:
     - Monthly rentals and vacates
     - Occupancy progression
     - Rental rates with escalations
     - Revenue by category
     - Expenses by category
     - NOI and cash flow

### 5. **7 Year Projection** ⭐ ANNUAL SUMMARY OUTPUT
   - Annual summary of key metrics (Years 1-7)
   - Dimensions: 53 rows × 34 columns
   - Primary output for investment analysis
   - See detailed structure below

### 6. **7 Year Projection-Expanded**
   - Expanded version with additional detail
   - Dimensions: 155 rows × 36 columns
   - More granular revenue and expense breakouts

### 7. **Loan Payoff Schedule**
   - Amortization schedule
   - Dimensions: 26 rows × 254 columns
   - Monthly principal and interest calculations

### 8. **Rate Calculation**
   - Rate benchmarking and calculation logic
   - Dimensions: 48 rows × 20 columns

### 9. **Expense Comp Data**
   - Comparable property expense data
   - Dimensions: 130 rows × 16 columns
   - Used for expense assumptions if overrides not provided

### 10. **Modeling**
   - Additional modeling calculations
   - Dimensions: 250 rows × 21 columns

### 11. **Attrition Modeling** ⭐ VACANCY RATE LOOKUP
   - Seasonal vacancy rate tables
   - Dimensions: 1000 rows × 32 columns
   - Vacancy rates by rental month and vacancy month
   - Critical for lease-up modeling

### 12. **Traditional Attrition**
   - Traditional vacancy pattern analysis
   - Dimensions: 196 rows × 73 columns

### 13. **IP Attrition**
   - In-place tenant attrition modeling
   - Dimensions: 196 rows × 73 columns

### 14. **RentalsVacates**
   - Detailed rental and vacancy tracking
   - Dimensions: 205 rows × 73 columns

### 15. **Monthly**
   - Monthly detail view
   - Dimensions: 266 rows × 73 columns

---

## Input Parameters

### Basic Information
| Parameter | Value/Formula | Description |
|-----------|---------------|-------------|
| Address | 250 Dolson Avenue | Property address |
| City | Middletown | |
| State | New York | |
| Zip | 10940 | |
| New Development? | TRUE | New construction vs existing |
| Projection Start Date | 2026-01-31 | End of month start date |
| Property Age | 1 year | |

### Property Specifications
| Parameter | Value | Description |
|-----------|-------|-------------|
| Total Square Feet | 105,807 | Net rentable storage SF |
| Total Units | 684 | Number of storage units |
| Climate Controlled SF | 105,807 | All climate controlled |
| Climate Controlled % | 100% | |
| Starting Occupied SF | 0 | New development starts at 0% |
| Starting Occupied Units | 0 | |

### Acquisition & Financing
| Parameter | Value/Formula | Description |
|-----------|---------------|-------------|
| Purchase Price | $14,903,660 | Acquisition cost |
| Loan Amount | =C45*0.65 | 65% LTV |
| Interest Rate | 7.5% | Annual interest rate |
| Loan Term | 25 years | Amortization period |
| IO Period | 0 months | No interest-only period |
| Closing Costs | $50,000 | |
| Origination Fees | =C46*0.02 | 2% of loan amount |
| LTV Ratio | =C46/C45 | 65% |
| Equity Contribution | =C45-C46+C50+C51+C52 | Down payment + costs |

### Occupancy Assumptions (Lease-Up Curve)
| Year | Target Occupancy | Type |
|------|------------------|------|
| Year 1 | 33% | Average occupancy |
| Year 2 | 68% | Average occupancy |
| Year 3 | 92% | Average occupancy |
| Year 4+ | 92% | Stabilized occupancy |
| First Fully Stable Year | Year 4 | |
| Stable Average Occupancy | 92% | Long-term target |

**Note:** Years 1-3 show "Occ @ End of Year" while Year 4+ show "Average Occ"

### Rate Assumptions
| Parameter | Value/Formula | Description |
|-----------|---------------|-------------|
| Starting Rate (IP Rate) | =('Rate Calculation'!R38*12)*0+(1.55*12) | $18.60/unit/month |
| Year 1 Rate Increase | 4.0% | Annual escalation |
| Year 2 Rate Increase | 4.0% | |
| Year 3 Rate Increase | 4.0% | |
| Year 4 Rate Increase | 4.0% | |
| Year 5 Rate Increase | 4.0% | |
| Avg Rate Increases % | 12.0% | Average in-place rate increases |

### Long-Term Growth Assumptions
| Parameter | Value | Description |
|-----------|-------|-------------|
| LT Revenue Growth | 4.0% | Annual revenue escalation post-stabilization |
| Annual Expense Growth | 2.5% | Operating expense inflation |
| Annual RE Tax Growth | 1.0% | Property tax escalation |

### Revenue Assumptions

#### Net Rental Income
| Item | GL Code | Type | Override Value |
|------|---------|------|----------------|
| Discounts | 4700 | % of RI | -2.5% |
| Write-offs | WriteOffSum | % of RI | -1.0% |

#### Fee Income
| Item | GL Code | Unit | Override Value |
|------|---------|------|----------------|
| Admin Fees | 4281 | per rental | $15.00 |
| Late Fees | 4282 | % of RI | 0.1% |
| Other Fee Revenue | 4283 | % of RI | 0.1% |
| Convenience Fee | 4286 | % of RI | 0.1% |
| Fee Write Off | 7102 | % of RI | 0.1% |
| Fees Waived | 4285 | % of RI | 0.1% |
| Fees Waived - Admin | 4287 | % of RI | 0.1% |
| Fees Waived - Late Fee | 4288 | % of RI | 0.1% |
| CC Chargebacks | 4255 | % of RI | 0.1% |

#### Ancillary Income
| Item | GL Code | Unit | Override Value |
|------|---------|------|----------------|
| Max Insurance Penetration | - | - | 75% |
| Penske Truck Rental | 4940 | per month | $0 |
| Site Truck Rental | 4962 | per month | $0 |
| Merchandise | 4961 | per rental | $2.50 |

#### Non-Storage Income
| Parameter | Value | Description |
|-----------|-------|-------------|
| Modeling Methodology | Simple Annual Growth | |
| Annual Growth Rate | 3.0% | |
| Starting Non-Storage GPI | $0 | |
| Months to Stabilization | 0 | |

### Expense Assumptions

#### Payroll Expense
| Item | GL Code | Basis | Override Value |
|------|---------|-------|----------------|
| # of Full-Time Employees | - | Calculated | 0 (formula based) |
| Medical Expense | 6112 | per FTE | $822 |
| Payroll Taxes | 6130 | % of Salary | 1.0% |
| Workers Comp | 6283 | % of Salary | 1.0% |

#### Utility Expense (per SF unless noted)
| Item | GL Code | Basis | Override Value |
|------|---------|-------|----------------|
| Rubbish Removal | 6150 | psf | $0.11 |
| Exterminating | 6158 | psf | $0.05 |
| Electric | 6184 | psf | $0.28 |
| Telephone | 6185 | psf | $0.05 |
| Water/Sewer | 6186 | psf | $0.12 |
| Gas & Utilities | 6187 | psf | $0.10 |
| Security Expense | 6200 | psf | ~$0 |
| Fire Alarm Monitoring | 6205 | psf | $0.01 |

#### Repairs & Maintenance Expense (per SF unless noted)
| Item | GL Code | Basis | Override Value |
|------|---------|-------|----------------|
| R&M Roof | 6189 | psf | Modeling based |
| Repairs & Maintenance | 6192 | psf | Modeling based |
| R&M Elevator | 6193 | psf | Modeling based (if multi-story) |
| R&M Doors | 6194 | psf | Modeling based |
| R&M Gates | 6195 | psf | Modeling based |
| R&M Golf Carts | 6196 | psf | Modeling based (if golf cart) |
| R&M Parking Lot | 6197 | psf | Modeling based |
| R&M Cameras | 6198 | psf | Modeling based |
| R&M HVAC | 6199 | psf | Modeling based |
| R&M Fire Protection | 6201 | psf | Modeling based |
| R&M Lighting/Electrical | 6203 | psf | Modeling based |
| R&M Plumbing | 6204 | psf | Modeling based |
| R&M Exterior Bldg Repair | 6206 | psf | Modeling based |
| R&M Apartments | 6321 | psf | Modeling based (if apartment) |

**Note:** R&M expenses use formulas from the "Modeling" sheet that adjust based on property characteristics (multi-story, golf cart, apartment, etc.)

#### Other Operating Expense
| Item | GL Code | Basis | Override Value |
|------|---------|-------|----------------|
| Training | 6122 | per month | $15 |
| Uniforms | 6152 | per EE | $175/year |
| Supplies | 6162 | per month | $0 |
| Help Desk | 6163 | per month | $43 |
| Truck Expense | 6166 | per month | $0 |
| Dues & Subscriptions | 6168 | per month | $12 |
| Landscaping | 6170 | psf | $0.14 |
| Signs | 6174 | per month | ~$0 |
| Auto Expense | 6176 | per month | $0 |
| Fees/Licenses | 6182 | per month | $17 |
| Postage/UPS | 6190 | per month | $0 |
| Office Supplies | 6212 | per month | $0 |
| Computer Expense | 6224 | per month | $64 |
| CMS Expense | 6225 | per month | $189 |
| Bank Charges | 6226 | per month | Comp data |
| Bank Printing Fees | 6227 | per month | ~$0 |
| Visa/MC | 6232 | % of Revenue | 1.5% |
| American Express | 6233 | % of Revenue | 0.8% |
| Legal Advertising | 6261 | per month | $0 |
| Legal/Auction | 6256 | per month | $50 |
| Free Move Vouchers | 6311 | $ per rental | ~$0 |
| Truck R&M | 6320 | per month | Based on truck presence |

#### Marketing Expense
| Item | GL Code | Basis | Override Value |
|------|---------|-------|----------------|
| Marketing Expense | 6377 | Annual | $12,000 |

#### Non-Controllable Expenses
| Item | GL Code | Basis | Override Value |
|------|---------|-------|----------------|
| Real Estate Taxes | 6270 | psf | Formula based on property |
| Snow Removal | 6172 | psf | $0.11 |
| Insurance | 6280 | psf | $0.27 |
| Insurance - Flood/Pollution | - | per month | $0 |

#### Other Expenses
| Item | GL Code | Basis | Override Value |
|------|---------|-------|----------------|
| Commissions | 7500 | per month | $0 |
| Professional Fees | 7530 | per month | $0 |
| Land Lease | 7550 | per month | $0 |

### Property Characteristics (Impact Expense Calculations)
| Characteristic | Value | Impact |
|----------------|-------|--------|
| Move-In Truck? | FALSE | Truck R&M expenses |
| Climate Controlled? | TRUE (100%) | Utility costs |
| Multi-Story? | TRUE | Elevator R&M |
| Golf Cart? | FALSE | Golf cart R&M |
| Apartment? | FALSE | Apartment R&M |

### Capital Expenditures & Soft Costs
| Item | Value |
|------|-------|
| New Asphalt | $0 |
| Roof Replacement | $0 |
| Security Upgrades | $0 |
| Doors | $0 |
| CapEx Budget | $0 |

### Benchmarks (Reference Only - Calculated from Model)
| Metric | Target Range | Model Formula |
|--------|--------------|---------------|
| Opex PSF | $5.31-$6.27 | ='7 Year Projection'!S38/'7 Year Projection'!U4 |
| Payroll PSF | $0.73-$1.28 | =R8/C13 |
| Utilities/Maintenance PSF | $1.00-$1.50 | =(R18+R35+R68)/C13 |
| Property Taxes PSF | $2.09-$2.47 | ='7 Year Projection'!S34/'7 Year Projection'!U4 |
| Insurance PSF | $0.27 | ='7 Year Projection'!S35/'7 Year Projection'!U4 |
| Revenue PSF | ~$15 | ='7 Year Projection'!S26/C13 |
| Ancillary Income % | ~3% | ='7 Year Projection'!S25/'7 Year Projection'!S26 |
| Expense Ratio | 21.5%-35.0% | ='7 Year Projection'!S38/'7 Year Projection'!S26 |

---

## 7 Year Projection Output Structure

The "7 Year Projection" sheet provides annual summaries with the following structure:

### Row Structure

**Header Rows (1-8):**
- Row 3: Property address
- Row 4: Net Rentable Square Feet
- Row 5: Unit Count
- Row 6-7: (Empty)
- Row 8: Time period headers (monthly columns + annual summary columns)

**Column Layout:**
- Columns A-B: Reference codes/identifiers
- Column C: Section headers and metric labels
- Column D: Line item descriptions
- Columns E-F: (Varies)
- Columns G-R: Monthly detail (12 months)
- Column S: **Year 1 Total**
- Column T: **Year 2 Total**
- Column U: **Year 3 Total**
- Column V: **Year 4 Total**
- Column W: **Year 5 Total**
- Column X: **Year 6 Total**
- Column Y: (Likely Year 7)
- Additional columns may extend beyond for sensitivity

### Detailed Line Items

#### OCCUPANCY & ACTIVITY METRICS (Rows 10-19)

| Row | Code | Description | Formula Type |
|-----|------|-------------|--------------|
| 10 | MI | **Rentals** | Sum of monthly rentals |
| 11 | MO | **Vacates** | Sum of monthly vacates |
| 12 | Net | **Net Rentals** | Rentals - Vacates |
| 13 | RentEnd | **Rented Units (EoM)** | Ending occupied units |
| 14 | - | === Occupancy === | Section header |
| 15 | SFRent | **Sq. Feet Rented** | Average SF rented over year |
| 16 | SFOcc% | **Avg. Square Foot Occupancy** | SF Rented / Total SF |
| 17 | - | (Empty) | |
| 18 | AvgRentRate | **Avg. Rent Rate on Rentals** | Average rate for new move-ins |
| 19 | IPRPSF | **In-Place Rate** | Weighted average rate of occupied units |

#### REVENUE (Rows 21-26)

| Row | Code | Description | Formula Type |
|-----|------|-------------|--------------|
| 21 | 4100 | **Rental Income** | Occupied units × rates |
| 22 | 4700 | **Discounts** | Negative value (promotions, concessions) |
| 23 | 7101 | **Write Off** | Negative value (bad debt) |
| 24 | NetRentInc | **Net Rental Income** | Sum of rows 21-23 |
| 25 | Total Ancillary Income | **Total Ancillary Income** | Insurance, fees, merchandise, etc. |
| 26 | - | === Property Revenue === | Section header (total revenue) |

#### EXPENSES (Rows 28-37)

| Row | Code | Description | Formula Type |
|-----|------|-------------|--------------|
| 28 | Total Personnel Expense | **Payroll** | Salaries, benefits, taxes |
| 29 | Total Utility Expense | **Utilities** | Electric, water, gas, etc. |
| 30 | Total Other Operating Expense | **Operating Expenses** | Supplies, fees, credit card fees, etc. |
| 31 | 6171 | **Landscaping** | Separate line item |
| 32 | Total R&M Expense | **Repairs & Maintenance** | All R&M categories |
| 33 | Total Marketing Expense | **Marketing** | Advertising spend |
| 34 | 6270 | **Taxes** | Real estate taxes |
| 35 | 6280 | **Insurance** | Property insurance |
| 36 | 6801 | **Management Fees** | Third-party management (if applicable) |
| 37 | 7550 | **Land Lease** | Ground lease payment (if applicable) |

#### KEY METRICS (Rows 38-53)

| Row | Code | Description | Formula Type |
|-----|------|-------------|--------------|
| 38 | PropertyExp | === Property Expenses === | Sum of all expenses (rows 28-37) |
| 39 | - | (Empty) | |
| 40 | PropertyProfit | === Property NOI === | Revenue (row 26) - Expenses (row 38) |
| 41 | - | (Empty) | |
| 42 | Total Debt Service | === Total Debt Service === | Principal + Interest payments |
| 43 | - | (Empty) | |
| 44 | Levered Cash Flow | === Levered Cash Flow === | NOI - Debt Service |
| 45 | - | (Empty) | |
| 46 | Beginning Loan Balance | **Beginning Loan Balance** | Loan balance at start of period |
| 47 | Interest Payment | **Interest Payment** | Annual interest paid |
| 48 | Principal Payment | **Principal Payment** | Annual principal paid |
| 49 | Ending Loan Balance | **Ending Loan Balance** | Loan balance at end of period |
| 50 | - | === DSCR === | Debt Service Coverage Ratio = NOI / Debt Service |
| 51 | - | === Cap Rate === | Capitalization Rate = NOI / Purchase Price (or value) |
| 52 | - | === Cash on Cash Return === | Levered Cash Flow / Equity Contribution |
| 53 | - | === Yield on Cash === | (Alternative return metric) |

### Sample Year 1 Metrics (Based on Model Formulas)

The actual values are calculated dynamically, but the structure shows:

**Occupancy Progression:**
- Year 1: Average 33% occupancy (lease-up year)
- Year 2: Average 68% occupancy
- Year 3: Average 92% occupancy (approaching stabilization)
- Year 4+: Stable at 92% occupancy

**Revenue Build-Up:**
- Rental Income starts low and ramps with occupancy
- Discounts are highest in early years (lease-up promotions)
- Ancillary income (insurance, fees) grows with rental base

**Expense Structure:**
- Payroll relatively fixed
- Utilities scale with occupancy
- Marketing typically higher in lease-up
- Taxes and insurance relatively fixed
- R&M increases as property ages

**Investment Returns:**
- NOI grows significantly from Year 1 to stabilization
- DSCR improves as NOI grows
- Cap Rate calculated on stabilized performance
- Cash-on-Cash shows equity return after debt service

---

## Data Flow & Calculation Logic

### High-Level Flow Diagram

```
┌─────────────┐
│   INPUTS    │ ← User configures all assumptions
│   Sheet     │
└──────┬──────┘
       │
       ├──────→ Property characteristics
       ├──────→ Occupancy targets
       ├──────→ Rate assumptions
       ├──────→ Expense assumptions
       ├──────→ Financing terms
       │
       ↓
┌──────────────────┐
│ ATTRITION        │ ← Seasonal vacancy rate tables
│ MODELING         │
└──────┬───────────┘
       │
       ↓
┌──────────────────┐
│  PROJECTION      │ ← Monthly calculation engine
│  Sheet           │   - Calculates monthly rentals/vacates
│                  │   - Applies attrition rates
│                  │   - Escalates rates
│                  │   - Calculates revenue & expenses
└──────┬───────────┘
       │
       ├──────→ Monthly detail (84+ months)
       │
       ↓
┌──────────────────┐
│ 7 YEAR           │ ← Annual summary and rollup
│ PROJECTION       │   - Sums monthly data to annual
│                  │   - Calculates metrics (Cap Rate, DSCR, CoC)
└──────┬───────────┘
       │
       ↓
┌──────────────────┐
│ 7 YEAR           │ ← Expanded detail version
│ PROJECTION-      │
│ EXPANDED         │
└──────────────────┘

Supporting Calculations:
┌──────────────────┐
│ LOAN PAYOFF      │ ← Debt service schedule
│ SCHEDULE         │
└──────────────────┘
┌──────────────────┐
│ RATE             │ ← Market rate analysis
│ CALCULATION      │
└──────────────────┘
┌──────────────────┐
│ EXPENSE COMP     │ ← Comp property data for defaults
│ DATA             │
└──────────────────┘
```

### Detailed Calculation Sequence

#### 1. Inputs → Projection (Monthly)

**Step 1: Initialize Starting Conditions**
- Starting occupancy from Inputs!C18 (occupied SF) and C19 (occupied units)
- Starting rates from Inputs!I16
- Month 0 = Inputs!C8 (projection start date)

**Step 2: Monthly Rental Velocity**
- Target occupancy for each year from Inputs!I6:I10
- Model calculates required monthly rentals to hit target
- Applies array formulas to spread rentals across months
- Considers seasonality (if applicable)

**Step 3: Monthly Attrition (Vacates)**
- Uses "Attrition Modeling" sheet vacancy rate lookup
- Rates vary by:
  - Month of rental (how long tenant has been there)
  - Current calendar month (seasonality)
- Formula structure: Looks up based on rental cohort age

**Step 4: Occupancy Calculation**
- Beginning Occupied Units (month M) = Ending Occupied Units (month M-1)
- Rentals (month M) from velocity calculation
- Vacates (month M) from attrition calculation
- Ending Occupied Units = Beginning + Rentals - Vacates
- SF Rented = Ending Occupied Units × Avg Unit SF (Inputs!F5 in Projection)

**Step 5: Rate Escalation**
- New rental rate starts at Inputs!I16
- Escalates annually by Inputs!I19:I23 (4% per year)
- In-place rates for existing tenants increase by Inputs!I25 (12% average annual increase)
- Weighted average in-place rate = (Sum of all occupied units' rates) / Total occupied units

**Step 6: Revenue Calculation**
For each month:
- **Rental Income (4100):** SF Rented × In-Place Rate / 12
- **Discounts (4700):** Rental Income × Inputs!I36 (-2.5%)
- **Write-offs (7101):** Rental Income × Inputs!I37 (-1.0%)
- **Net Rental Income:** Rental Income + Discounts + Write-offs
- **Ancillary Income:** Calculated from various sources:
  - Admin Fees: Rentals × $15
  - Late Fees: Rental Income × 0.1%
  - Insurance: Occupied Units × Penetration Rate × Premium
  - Merchandise: Rentals × $2.50
  - Etc.

**Step 7: Expense Calculation**
For each month:

*Payroll Expenses:*
- FTE count based on formula in Inputs!O4 (related to property SF/hours)
- Medical: FTE × $822 / 12
- Payroll Taxes: Total Salaries × 1%
- Workers Comp: Total Salaries × 1%

*Utility Expenses (PSF basis):*
- Electric: Total SF × $0.28 / 12
- Water: Total SF × $0.12 / 12
- Etc. for each utility category

*R&M Expenses:*
- Conditional based on property characteristics
- If Multi-Story=TRUE, include Elevator R&M
- If Golf Cart=TRUE, include Golf Cart R&M
- Calculated from Modeling sheet formulas

*Other Operating:*
- Fixed monthly amounts (Help Desk, CMS, etc.)
- Variable with revenue (Credit card fees = Revenue × %)
- Per-rental fees (Vouchers, etc.)

*Marketing:*
- Annual budget (Inputs!P64 = $12,000) / 12

*Non-Controllable:*
- Real Estate Taxes: Formula based on purchase price or assessed value
- Insurance: Total SF × $0.27 / 12
- Escalate by Inputs!C36 (1% for taxes) and C35 (2.5% for other expenses) annually

#### 2. Projection → 7 Year Projection (Annual)

**For each annual metric:**
- Columns G:R contain months 1-12 for Year 1
- Column S (Year 1) = SUM(G:R) for summable items, or AVERAGE(G:R) for rates/percentages
- Same pattern for Years 2-7 (using different monthly column ranges)

**Occupancy Metrics:**
- Annual Rentals = Sum of monthly rentals
- Annual Vacates = Sum of monthly vacates
- Average SF Occupancy = Sum of monthly SF rented / 12 / Total SF

**Revenue Metrics:**
- Annual Rental Income = Sum of 12 months
- Apply annual discounts and write-offs
- Sum ancillary income streams

**Expense Metrics:**
- Annual totals for each category
- Validate to benchmarks (PSF metrics in Inputs rows 67-74)

**NOI Calculation:**
Row 40 formula: =SUM(S21:S25) - S38
(Total Revenue - Total Expenses)

**Debt Service:**
Row 42 pulls from "Loan Payoff Schedule" sheet
Principal + Interest for the year

**Levered Cash Flow:**
Row 44 formula: =S40 - S42
(NOI - Debt Service)

**Investment Metrics:**
- **DSCR (Row 50):** =S40 / S42 (NOI / Debt Service)
- **Cap Rate (Row 51):** =S40 / Inputs!C45 (NOI / Purchase Price) for Year 1
  - Uses current year NOI for subsequent years
- **Cash on Cash (Row 52):** =S44 / Inputs!C55 (Levered CF / Equity Contribution)
- **Yield on Cash (Row 53):** Alternative return calculation

#### 3. Loan Payoff Schedule

- Beginning Balance: Inputs!C46 (loan amount)
- Interest Only Period: Inputs!C49 (0 months in this case)
- Monthly Interest Rate: Inputs!C47 / 12 (7.5% / 12)
- Monthly P&I Payment: =PMT(rate, periods, -principal)
- Each month:
  - Interest = Beginning Balance × Monthly Rate
  - Principal = Payment - Interest
  - Ending Balance = Beginning Balance - Principal
- Annual totals roll up for 7 Year Projection Row 47 and 48

---

## Lease-Up Modeling

The model's lease-up logic is sophisticated and uses actual historical attrition data.

### Occupancy Targets

From Inputs sheet:
- **Year 1 Target:** 33% average occupancy
- **Year 2 Target:** 68% average occupancy
- **Year 3 Target:** 92% average occupancy
- **Year 4+ Target:** 92% stabilized occupancy

**Important distinction:**
- Years 1-3 show "Occ @ End of Year" (Inputs!F6:F8 labels)
- Year 4+ show "Average Occ" (Inputs!F9:F10 labels)

This means the model is trying to END Year 3 at 92% to maintain 92% average in Year 4.

### Rental Velocity Calculation

The Projection sheet uses **array formulas** to distribute rentals across months to achieve occupancy targets.

**Logic:**
1. Calculate required ending occupancy for month M
2. Required Rentals = (Target Occupied Units - Current Occupied Units) + Expected Vacates
3. Distribute rentals based on:
   - Achieving the annual target curve
   - Seasonal patterns (if seasonality is enabled)
   - Maximum absorption constraints (implicitly modeled)

**Example Year 1:**
- Start: 0 units occupied
- End Target: ~33% × 684 units = 226 units (average, so end might be higher)
- Need to overcome attrition throughout the year
- Monthly rentals start higher and may taper as occupancy builds

### Attrition (Vacancy) Modeling

The "Attrition Modeling" sheet contains a comprehensive lookup table:

**Structure:**
- Column A: Seasonality flag (1 = enabled)
- Column B: RentalMonth (month in which tenant moved in, 1-12)
- Column C: VacateMonth (month since rental, 1-12+)
- Column D: VacateRate (probability of vacating)

**Example rates from the data:**
- A tenant who rented in Month 1:
  - 2.56% chance of vacating in month 1 (same month)
  - 11.55% chance of vacating in month 2
  - 10.08% chance of vacating in month 3
  - Rates generally decrease over time as tenant tenure increases

**Application in Projection:**
For each cohort of rentals (by month), the model:
1. Tracks how long they've been there
2. Looks up the appropriate vacate rate based on:
   - Original rental month
   - Months since rental
3. Applies the rate to calculate expected vacates
4. Sums across all cohorts to get total monthly vacates

This creates a realistic attrition pattern where:
- New tenants have higher churn (move-out in first 3 months)
- Longer-tenure tenants are more stable
- Seasonal effects can be incorporated

### Stabilization Timing

**Year 1 (Months 1-12):**
- Heavy lease-up activity
- High rental velocity
- Building occupancy from 0% to ~40%+ by year-end

**Year 2 (Months 13-24):**
- Continued strong lease-up
- Occupancy climbs to ~75%+ by year-end
- Attrition from Year 1 cohorts starts to stabilize

**Year 3 (Months 25-36):**
- Final push to stabilization
- Reach 92% by year-end
- Balance of rentals and vacates approaches equilibrium

**Year 4+ (Months 37+):**
- Stable operations
- Rentals ≈ Vacates (maintaining 92% occupancy)
- Focus shifts to rate growth and expense management

### Key Assumptions Driving Lease-Up

1. **No initial occupancy:** New development starts at 0%
2. **No pre-leasing:** Rentals begin Month 1
3. **Aggressive first-year absorption:** 33% average = ~40% by year-end
4. **Two-year primary lease-up:** Reaching near-stabilization by end of Year 2
5. **Attrition stabilizes:** As cohorts age, overall vacancy rate normalizes
6. **Rate strategy:** Starting rates are conservative ($18.60/mo) with 4% annual increases

---

## Key Formulas & Business Logic

### Critical Formulas by Sheet

#### Inputs Sheet

**Loan Amount (C46):**
```excel
=C45*0.65
```
65% LTV on purchase price

**Equity Contribution (C55):**
```excel
=C45-C46+C50+C51+C52
```
Purchase Price - Loan + Closing Costs + CapEx + Origination Fees

**Starting Rate (I16):**
```excel
=(('Rate Calculation'!R38*12)*0)+(1.55*12)
```
Currently set to $18.60/year ($1.55/month) - the first part is zeroed out, suggesting flexibility to use market rate from Rate Calculation sheet

**Expense Model Override Logic (Column Q):**
```excel
=IF(P[row]=0,O[row],P[row])
```
If override (column P) is zero, use comp data (column O), else use override

#### Projection Sheet

**Ending Occupied Units (Monthly):**
```excel
=Previous_Month_Ending + This_Month_Rentals - This_Month_Vacates
```

**SF Occupancy (Monthly):**
```excel
=(Ending_Occupied_Units * Avg_Unit_SF) / Total_SF
```

**Rental Income (Monthly):**
```excel
=SF_Rented * In_Place_Rate_PSF
```

**Expense Escalation:**
```excel
Year N Expense = Year (N-1) Expense * (1 + Growth_Rate)
```
Growth rates from Inputs!C35 (2.5% for operating) and C36 (1% for taxes)

#### 7 Year Projection Sheet

**Annual Revenue Rollup (Example: Rental Income Row 21, Column S for Year 1):**
```excel
=SUMIF(Projection!$F:$F,'7 Year Projection'!$A21,Projection!BW:BW)
```
Sums all Projection sheet rows where column F matches the GL code in A21, from the appropriate year column

**Annual Occupancy (Row 16, Column S):**
```excel
=S15/$U$4
```
Average SF Rented / Total SF

**Property NOI (Row 40):**
```excel
=SUM(S21:S25) - S38
```
Total Revenue (Rental Income + Ancillary) - Total Property Expenses

**DSCR (Row 50):**
```excel
=S40 / S42
```
NOI / Debt Service

**Cap Rate (Row 51):**
```excel
=S40 / [Purchase_Price_or_Value]
```
Typically uses purchase price for Year 1, may use projected value for exit years

**Cash on Cash Return (Row 52):**
```excel
=S44 / Inputs!C55
```
Levered Cash Flow / Equity Contribution

#### Loan Payoff Schedule

**Monthly Payment:**
```excel
=PMT(Inputs!$C$47/12, Inputs!$C$48*12, -Inputs!$C$46)
```
PMT(monthly rate, total months, -loan amount)

**Monthly Interest:**
```excel
=Beginning_Balance * (Inputs!$C$47/12)
```

**Monthly Principal:**
```excel
=Payment - Interest
```

**Ending Balance:**
```excel
=Beginning_Balance - Principal
```

### Business Logic Highlights

#### 1. Tiered Occupancy Targets
The model distinguishes between lease-up (Years 1-3 end-of-period targets) and stabilized (Year 4+ average targets) to accurately model the transition.

#### 2. Expense Flexibility
Every expense line has three possible sources:
- **Comp Data (Column O):** Industry benchmarks from Expense Comp Data sheet
- **Override (Column P):** User-specified values
- **Model (Column Q):** Formula that uses override if provided, else comp data

This allows users to be as specific or general as they want.

#### 3. Property Characteristic Conditionals
Expenses adjust based on property features:
```excel
=IF(C62=FALSE, 0, [expense_formula])
```
E.g., if Multi-Story = FALSE, Elevator R&M = 0

#### 4. Attrition Sophistication
Using real historical data for vacancy rates by cohort age and seasonality creates realistic turnover patterns rather than a simple fixed annual rate.

#### 5. Rate Growth Dual Strategy
- **New Move-Ins:** Escalate by annual rate increases (4%)
- **Existing Tenants:** Escalate by average in-place increases (12%)

This models the reality that existing tenants receive higher increases than street rates for new customers.

#### 6. Revenue Waterfall
Rental Income → Apply Discounts → Apply Write-offs → Add Ancillary Income
This creates a clean revenue build-up that separates gross potential from net effective.

#### 7. Scalable Payroll
FTE count is formula-driven based on property size, allowing the model to scale payroll costs appropriately as new properties are modeled.

---

## Key Insights & Modeling Philosophy

### Model Strengths

1. **Granular Monthly Detail:** 84+ months of detailed projections allow for precise cash flow timing
2. **Realistic Attrition:** Historical vacancy rate data creates accurate turnover modeling
3. **Flexible Inputs:** Override capability for every assumption enables scenario testing
4. **Comprehensive Expenses:** Detailed GL-level expense tracking matches accounting systems
5. **Property-Specific Logic:** Conditional expenses based on property characteristics
6. **Investment Metrics:** Provides all key returns (Cap Rate, CoC, DSCR, Yield) for analysis

### Model Limitations & Considerations

1. **Attrition Data Source:** Vacancy rates appear to be historical averages - may not reflect specific market conditions
2. **Fixed Stabilization:** 92% stabilized occupancy is hardcoded - market may support higher/lower
3. **Rate Strategy:** Starting rate and escalation assumptions are critical and may need market validation
4. **Expense Benchmarks:** Comp data may not reflect current inflation or local market conditions
5. **No Seasonality Toggle Visible:** While attrition has seasonality column, unclear if easily adjustable
6. **No Unit Mix Detail:** Model appears to use average unit size - doesn't distinguish 5x5 from 10x20 pricing

### Recommended Use Cases

**Best For:**
- New development feasibility analysis
- Acquisition underwriting of lease-up properties
- Refinancing analysis (debt service coverage)
- Partnership return calculations
- Sensitivity testing (change inputs, see impact on returns)

**Less Suited For:**
- Stabilized property with complex rate matrix by unit type
- Properties with significant non-storage income (minimal modeling)
- Short-term hold analysis (model is 7-year focused)
- Properties with complicated partnership structures (simple equity calculation)

---

## Appendix: File Specifications

**File Name:** Self Storage 7 Year Model.xlsx
**File Type:** Microsoft Excel Workbook (.xlsx)
**Total Sheets:** 15
**Largest Sheet:** Loan Payoff Schedule (26 rows × 254 columns)
**Primary Input Sheet:** Inputs (277 rows × 32 columns)
**Primary Output Sheet:** 7 Year Projection (53 rows × 34 columns)
**Calculation Engine:** Projection (372 rows × 109 columns)

**Excel Features Used:**
- Array formulas (occupancy and rental calculations)
- SUMIF functions (revenue and expense rollups)
- Conditional logic (IF statements for expense toggles)
- Date functions (EOMONTH for period calculations)
- Financial functions (PMT for loan payments)
- VLOOKUP/Index-Match equivalent (attrition rate lookups)
- Named ranges (likely, though not fully explored)
- Data validation (noted in warning messages)

---

**End of Analysis**

*This document provides a comprehensive map of the Self Storage 7 Year Model. Use it as a reference for understanding inputs, outputs, and calculation logic. For specific formula details, refer to the original Excel file.*

Generated: 2026-01-20 21:18:47
