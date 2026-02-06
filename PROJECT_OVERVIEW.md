# Feasibility Engine - Self-Storage Market Analysis Platform

## Overview

The **Feasibility Engine** is a comprehensive self-storage feasibility analysis platform built with Streamlit. It combines real-time market intelligence, financial modeling, AI-powered report generation, and professional PDF export capabilities to help developers, investors, and consultants evaluate self-storage development opportunities.

### Vision
Build a **world-class, AI-agent powered feasibility study generator** that produces institutional-quality reports that "blow the socks off users" - rivaling the quality of reports from top consulting firms.

---

## Architecture

### Tech Stack
- **Frontend**: Streamlit (Python web framework)
- **AI/LLM**: Anthropic Claude API (Sonnet model for report generation)
- **Data Sources**: TractiQ market data (PDF extraction), Census API, Google Maps scraper
- **PDF Generation**: WeasyPrint (HTML to PDF)
- **Charts**: Matplotlib, Plotly
- **Database**: SQLite (for caching)

### Core Modules

```
Feasibility_Engine/
├── app.py                      # Main Streamlit application (6 pages)
├── src/
│   ├── data_layer.py          # Centralized data access (single source of truth)
│   ├── tractiq_cache.py       # TractiQ PDF parsing and caching
│   ├── llm_report_generator.py # Claude AI report generation
│   ├── pdf_report_generator.py # PDF export with charts
│   ├── report_orchestrator.py  # Coordinates all analytics modules
│   ├── chart_generator.py      # 14 chart types for reports
│   ├── scoring_system.py       # 100-point site scoring
│   ├── financial_model.py      # Pro forma and IRR calculations
│   ├── market_analysis.py      # Supply/demand analysis
│   ├── benchmarks.py           # Industry benchmarks by state
│   ├── sensitivity_analysis.py # Tornado charts and sensitivity
│   ├── scenario_engine.py      # Bear/Base/Bull scenarios
│   ├── market_cycle.py         # Market cycle assessment
│   └── ui/
│       └── executive_dashboard.py  # Dashboard visualizations
└── src/data/
    ├── tractiq_cache/         # Cached market data by address
    └── example_studies/       # Reference studies for AI learning
```

---

## Key Features

### 1. Multi-Page Application (6 Pages)

| Page | Description |
|------|-------------|
| 📝 Project Inputs | Enter site address, upload TractiQ PDFs, configure analysis |
| 📊 Market Intel | View competitor data, demographics, SF per capita analysis |
| 💰 7-Year Operating Model | Financial projections, construction costs, lease-up model |
| 📈 Executive Dashboard | Visual scorecards, NOI projections, key metrics |
| 🤖 AI Feasibility Report | Generate full narrative report with Claude AI |
| 🎯 Command Center | Batch operations and system status |

### 2. 100-Point Site Scoring System

```
Demographics (25 points)
├── Population (3-mile)         5 pts
├── Growth Rate                 5 pts
├── Median Income               5 pts
├── Renter-Occupied %           5 pts
└── Median Age                  5 pts

Supply/Demand (25 points)
├── SF Per Capita               5 pts
├── Existing Occupancy          5 pts
├── Distance to Nearest         5 pts
├── Market Rate Trend           5 pts
└── Development Pipeline        5 pts

Site Attributes (25 points)
├── Visibility                  5 pts
├── Traffic Count               5 pts
├── Access Quality              5 pts
├── Lot Size Ratio              5 pts
└── Zoning Status               5 pts

Competitive Positioning (15 points)
├── Rate Competitiveness        5 pts
├── Product Differentiation     5 pts
└── Brand Strength              5 pts

Economic Market (10 points)
├── Unemployment Rate           3 pts
├── Job Growth                  4 pts
└── GDP Growth                  3 pts
```

### 3. AI Report Generation

The system generates 6 professional narrative sections using Claude:
1. Executive Summary
2. Site Scoring System Analysis
3. Market Analysis
4. Financial Feasibility
5. Risk Assessment
6. Conclusion & Recommendation

**Style Calibration**: The AI learns from uploaded example studies to match professional writing patterns.

### 4. Chart Types (14 Total)

**Original Charts:**
- SF Per Capita Comparison (bar)
- Competitor Scatter Plot
- NOI Waterfall
- Cash Flow Timeline
- Sensitivity Tornado
- Scenario Comparison
- Rate Positioning Bar
- Site Score Radar

**New Charts (Added):**
- Market Cycle Gauge
- Absorption Timeline
- Rate Heatmap
- Pipeline Timeline (Gantt)
- Demand Driver Pie
- Risk-Return Scatter

---

## Data Flow

```
1. User Input (Address, TractiQ PDFs)
         ↓
2. TractiQ Parser → Cache (JSON)
         ↓
3. FeasibilityDataLayer (Single Source of Truth)
         ↓
4. Analytics Modules (Scoring, Financials, Market)
         ↓
5. ReportData Object (All metrics compiled)
         ↓
6. Claude API → 6 Report Sections
         ↓
7. PDF Generator (HTML + Charts → PDF)
```

---

## Recent Bug Fixes (Current Session)

### 1. Competitor Count Discrepancy ✅
**Problem**: App showed 32 competitors for 5-mile, TractiQ showed 31.
**Root Cause**: Subject site (0.00mi distance) was being counted.
**Fix**:
- Added `MIN_COMPETITOR_DISTANCE = 0.05` to exclude subject site
- Adjusted `DISTANCE_TOLERANCE = 0.35` across all files

### 2. 7-Year Projection NoneType Error ✅
**Problem**: Executive dashboard crashed with `TypeError: 'NoneType' object is not callable`
**Fix**: Added guard check and fallback display when projection module unavailable

### 3. Session State Data Loss ✅
**Problem**: Data disappeared when downloading report or switching pages
**Fix**: Added persistent session state variables for report sections, PDF bytes, chart data

### 4. Construction Cost Display ✅
**Added**: Detailed construction cost breakdown on 7-Year Operating Model page

### 5. 7-Year Projection in AI Report ✅
**Added**: `seven_year_projection` and `construction_costs` fields to ReportData for AI context

---

## Configuration

### Environment Variables (.env)
```bash
ANTHROPIC_API_KEY=your_claude_api_key_here
GOOGLE_MAPS_API_KEY=optional_for_scraper
```

### Key Constants
```python
# src/data_layer.py, app.py, tractiq_cache.py
DISTANCE_TOLERANCE = 0.35      # Mile buffer for competitor counting
MIN_COMPETITOR_DISTANCE = 0.05  # Exclude subject site
```

---

## Next Steps / Roadmap

### Priority 1: Production Readiness
- [ ] Add comprehensive error handling throughout
- [ ] Implement rate limiting for API calls
- [ ] Add user authentication (for multi-tenant)
- [ ] Create backup/restore for TractiQ cache

### Priority 2: Enhanced AI Reports
- [ ] Add more chart types dynamically based on data
- [ ] Implement iterative report refinement (user feedback → AI revision)
- [ ] Add competitor-specific analysis sections
- [ ] Support for multi-site portfolio analysis

### Priority 3: Data Integrations
- [ ] Direct Census API integration (replace fallback data)
- [ ] CoStar data integration
- [ ] Yardi/RealPage market data
- [ ] Automated TractiQ PDF fetching (if API available)

### Priority 4: Business Features
- [ ] White-label PDF templates (custom branding)
- [ ] Report versioning and comparison
- [ ] Client portal for report delivery
- [ ] Subscription/usage tracking

### Priority 5: AI Agent Evolution
- [ ] Self-improving AI (learns from user edits)
- [ ] Automated market monitoring alerts
- [ ] Natural language queries ("How does Nashville compare to Memphis?")
- [ ] Multi-modal analysis (satellite imagery, photos)

---

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY="your_key_here"

# Run the app
streamlit run app.py
```

---

## Deploying to Streamlit Cloud

1. Push to GitHub repository
2. Connect repository to Streamlit Cloud
3. Add secrets in Streamlit Cloud dashboard:
   - `ANTHROPIC_API_KEY`
4. Deploy

---

## Key Files for AI Understanding

| File | Purpose |
|------|---------|
| `app.py` | Main application, all 6 pages, UI logic |
| `src/data_layer.py` | **CRITICAL** - Single source of truth for all data |
| `src/tractiq_cache.py` | TractiQ PDF parsing, competitor extraction |
| `src/llm_report_generator.py` | Claude prompts, report section generation |
| `src/report_orchestrator.py` | Coordinates analytics → LLM data flow |
| `src/scoring_system.py` | 100-point scoring logic and thresholds |
| `src/financial_model.py` | Pro forma, IRR, NPV calculations |

---

## Contact

This project is maintained for StorSageHQ consulting services.

---

*Last Updated: February 2025*
