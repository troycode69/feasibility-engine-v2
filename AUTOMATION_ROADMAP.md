# 🚀 Feasibility Engine Automation Roadmap

**Vision**: Input address → Generate Bob Copper-quality feasibility study → Recommend unit mix → Build 7-year pro forma

**Goal**: Make developers trust our AI-generated studies as much as $15K+ human-written reports

---

## ✅ Phase 1: AI Site & Economic Intelligence (COMPLETED)

### What Was Built
- **AI Site Scoring** (`site_intelligence.py`)
  - Google Street View + Claude Vision automatically scores visibility/access
  - No manual "Good/Fair/Poor" inputs needed
  - AI provides reasoning for transparency

- **Real-Time Economic Data** (`economic_data.py`)
  - BLS API fetches current unemployment by MSA
  - Infers business growth and economic stability
  - 100% free government data

- **Competitor Intelligence** (`competitor_intelligence.py`)
  - Automatically infers quality from facility features
  - Calculates pricing position from rate data
  - Data-driven, no human opinion

### Limitations Addressed
- **No paid APIs** - Using free Google Maps, BLS, Census
- **No occupancy data yet** - Will add TractIQ PDF parsing later
- **Graceful fallbacks** - Defaults if APIs unavailable

---

## 🔄 Phase 2: Age Demographics Enhancement (NEXT)

### Problem
Currently using default 40% for age 25-54 population

### Solution
**Census Bureau American Community Survey (ACS) API** (FREE)
- Table B01001: Sex by Age
- Get exact % population aged 25-54 by census tract
- API: `https://api.census.gov/data/2021/acs/acs5`

### Implementation
```python
def get_age_demographics(lat, lon):
    # Geocode to census tract
    # Query ACS API for B01001
    # Calculate % aged 25-54
    # Return exact percentage
```

**Effort**: 2-3 hours
**Value**: Eliminates last demographic default

---

## 📈 Phase 3: Absorption Trend Calculation

### Problem
Currently hardcoded "Moderate" absorption trend

### Solutions (Pick One Based on Data Availability)

#### Option A: TractIQ Historical Scraping
- **If**: We can scrape TractIQ quarterly for 12+ months
- **Then**: Build time-series database
  - Track occupancy changes month-over-month
  - Calculate absorption rate: `(Current Occ - Prior Occ) * Total Market SF / Months`
  - Classify: Strong (>1.5% monthly), Moderate (0.5-1.5%), Weak (<0.5%)

#### Option B: Inference from Current Occupancy
- **If**: Only current snapshot available
- **Then**: Use occupancy as proxy:
  - 90%+ occupancy → "Strong" (tight market)
  - 80-89% → "Moderate"
  - <80% → "Weak"
- Less accurate but better than hardcoded

#### Option C: External Market Reports (Manual)
- Download quarterly STR/Yardi reports
- Manually input absorption rates per market
- Store in database for reuse

**Recommended**: Start with Option B (inference), upgrade to Option A when possible

**Effort**: 4-6 hours
**Value**: Critical for lease-up modeling accuracy

---

## 🏗️ Phase 4: Intelligent Unit Mix Optimizer

### Current State
`financials.py` has basic logic:
- Urban vs Tertiary market type
- Undersupplied → More climate control
- Oversupplied → More drive-up

### Enhancements Needed

#### 1. Competitor Unit Mix Analysis
```python
def analyze_competitor_unit_mixes(competitors):
    # Scrape unit mixes from websites/PDFs
    # Calculate what sizes are saturated vs underserved
    # Example: "Market has 15% 10x10 but only 8% 10x20"
    # Recommend: "Increase 10x20 allocation to 15%"
```

#### 2. Demographic-Driven Sizing
```python
def recommend_sizes_from_demographics(demographics):
    # High income + renters → More small units (downsizing, storage)
    # Suburban + homeowners → Larger units (garage overflow)
    # Young professionals → 5x10, 10x10
    # Families → 10x15, 10x20
```

#### 3. Climate Control Ratio Optimization
- Use weather data (average temp/humidity)
- Hot/humid climates → 70%+ climate control
- Mild climates → 40-50%

**Deliverable**: `unit_mix_optimizer.py`
**Effort**: 8-10 hours
**Value**: Differentiated recommendation vs cookie-cutter mixes

---

## 📊 Phase 5: Predictive Pro Forma Model

### Current State
Excel-based lease-up curve:
- Linear ramp: Month 1 = 7.5%, Month 12 = 90%
- 2% annual growth hardcoded
- No seasonality

### Upgrade Path

#### Stage 1: Enhanced Excel Logic
Improvements to existing model:
- **Seasonality adjustments**: Summer boost, winter slowdown
- **Market-adjusted ramp**: Strong markets stabilize faster
- **Competitive pressure**: Reduce ramp if oversupplied

#### Stage 2: Time-Series Forecasting
**If** we get historical occupancy data:
```python
from prophet import Prophet  # Facebook's forecasting library

def forecast_leaseup(historical_data, market_features):
    # Train Prophet model on similar facility lease-ups
    # Features: Demographics, supply/demand, seasonality
    # Output: Month-by-month probability distribution
    # Include confidence intervals: "70% chance of 85-92% by Month 12"
```

#### Stage 3: Monte Carlo Simulation
```python
def run_monte_carlo(base_assumptions, n_simulations=1000):
    # Vary: Lease-up speed, rent growth, opex %
    # Generate 1000 possible outcomes
    # Output: P10/P50/P90 NOI scenarios
    # Visualize: Tornado chart of key drivers
```

**Effort**:
- Stage 1: 6-8 hours
- Stage 2: 20+ hours (requires data collection)
- Stage 3: 10-12 hours

**Value**: Matches sophistication of institutional underwriting

---

## 📄 Phase 6: Bob Copper-Level Report Generator

### Target Output
20-30 page PDF with:

#### Executive Summary (2 pages)
- Investment highlights
- PURSUE/CAUTION/PASS recommendation
- Key risk factors

#### Market Overview (4-6 pages)
- Location map with demographics overlay
- Population heat map
- Income distribution charts
- Growth trajectory graphs

#### Supply & Demand Analysis (4-6 pages)
- Competitive map (facilities within 5 miles)
- Supply/demand balance chart
- Absorption analysis
- Pipeline projects table

#### Site Analysis (3-4 pages)
- Aerial imagery with proposed layout
- Street View photos (4 angles)
- Traffic counts / visibility analysis
- Zoning & entitlements summary

#### Financial Projections (6-8 pages)
- Unit mix table with square footage allocation
- Lease-up schedule (monthly Year 1, annual Years 2-7)
- Sources & uses table
- Returns summary (YOC, IRR, equity multiple)
- Sensitivity analysis

#### Appendices (4-6 pages)
- Detailed competitor profiles
- Census data tables
- Economic indicators
- Assumptions schedule

### Implementation

#### Option A: HTML → PDF (Easier)
```python
from weasyprint import HTML

def generate_pdf_report(data):
    # Render Jinja2 template with data
    # Convert to PDF via WeasyPrint
    # Add page numbers, headers, footers
```

**Pros**: Easy to style with CSS, good for charts
**Cons**: Some layout limitations

#### Option B: ReportLab (More Control)
```python
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table

def build_report(data):
    # Programmatically build PDF with precise control
    # Custom styling, professional typography
```

**Pros**: Pixel-perfect control
**Cons**: Steeper learning curve

**Recommended**: Start with Option A (HTML), upgrade if needed

**Effort**: 20-30 hours
**Value**: Makes product SELLABLE - this is what clients pay for

---

## 🎯 Immediate Next Steps (Priorities)

### This Week
1. **Test Phase 1** - Run analysis on 5 real addresses, validate AI scores
2. **Add Age Demographics** (Phase 2) - Quick win, eliminates last default

### Next Sprint
3. **Absorption Trend Inference** (Phase 3B) - Use occupancy as proxy
4. **Document API requirements** - Which need keys, rate limits, etc.

### Month 2
5. **Unit Mix Optimizer** (Phase 4) - High value, moderate effort
6. **Pro Forma Stage 1 Enhancements** - Seasonality, market adjustments

### Month 3
7. **PDF Report Generator** (Phase 6) - This makes it SELLABLE

---

## 🔧 Technical Requirements

### APIs Needed
- ✅ Google Maps API (FREE tier: 28K requests/month)
- ✅ Anthropic Claude API (you have access)
- ✅ Census Bureau ACS (FREE, unlimited)
- ✅ BLS API (FREE, unlimited)
- ⏳ Google Street View API (paid at scale, but free tier sufficient for testing)

### Optional/Future
- Zoning data APIs (varies by jurisdiction)
- Weather data for climate control optimization
- Traffic count APIs

### Database Needs
- **SQLite** (current) → Fine for prototype
- **PostgreSQL** (future) → When adding time-series tracking

---

## 💰 Monetization Implications

### Current State (Basic)
- Manual inputs → Not sellable as premium product
- Generic recommendations → Commodity

### After Phase 6 (Professional)
- Fully automated → Scalable
- AI-generated reports → Indistinguishable from $15K studies
- Pricing potential: **$2,500-5,000 per report**

### Competitive Moat
- Bob Copper: 4-6 weeks, $15K-25K
- **Us**: 24 hours, $2,500
- **Advantage**: 90% cost savings, instant delivery

---

## 📊 Success Metrics

### Quality Benchmarks
- [ ] AI site scores match human expert >85% of time
- [ ] Economic data always current (≤30 days old)
- [ ] Unit mix recommendations backed by competitor analysis
- [ ] Pro forma accuracy within ±10% of stabilized performance

### User Trust Indicators
- [ ] Developers request modifications (shows engagement)
- [ ] Reports used in actual loan applications
- [ ] Repeat customers (validation of quality)

---

## 🚧 Known Limitations & Workarounds

### Occupancy Data Gap
**Problem**: No real-time occupancy feed
**Workaround**: TractIQ PDF parsing + quarterly updates
**Long-term**: Partner with STR/Yardi for data feed (once we have revenue)

### Zoning Data
**Problem**: No national zoning API
**Workaround**: Manual input for now, build database over time
**Long-term**: Web scraper for common jurisdictions

### Construction Costs
**Problem**: Vary by market, outdated quickly
**Workaround**: User input with market average suggestions
**Long-term**: Partner with cost estimator (RS Means API)

---

## 📝 Documentation Needs

### For Users
- [ ] "How AI Scores Work" explainer
- [ ] "Data Sources & Freshness" transparency page
- [ ] "Understanding Your Report" guide

### For Developers (Future Team)
- [ ] API integration guides
- [ ] Database schema documentation
- [ ] Deployment/scaling procedures

---

**Last Updated**: January 21, 2026
**Next Review**: After Phase 2 completion
