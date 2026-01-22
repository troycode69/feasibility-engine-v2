# TractIQ Data Integration Guide

## Overview

The Feasibility Engine now integrates TractIQ market data exports to provide **deep competitive intelligence** that goes far beyond basic web scraping. This transforms feasibility reports from generic analysis into substantive, data-driven market studies.

## What Gets Extracted from TractIQ PDFs

The system automatically extracts from uploaded TractIQ reports:

### 1. **Competitor Profiles**
- Facility names and locations
- Unit counts
- Occupancy rates (%)
- 10x10 climate-controlled rates
- NRSF (Net Rentable Square Feet)

### 2. **Unit Mix Analysis**
- Distribution of unit sizes (5x5, 10x10, 10x15, etc.)
- Unit counts by size
- Market composition percentages

### 3. **Historical Rate Trends**
- Time-series pricing data (by year or quarter)
- Occupancy trends over time
- Rate growth analysis

### 4. **Market-Level Metrics**
- Market average occupancy
- Market average rates
- Total supply (units/SF)

### 5. **Pipeline Risk**
- Facilities under construction
- Proposed developments
- Permit status

## TractIQ Report Types Supported

You can export and upload these TractIQ report types:

| Report Type | What It Contains | Recommended |
|-------------|------------------|-------------|
| **Executive Summary** | High-level market overview, key metrics | ✅ Yes |
| **Demographics** | Population, income, age distribution | ✅ Yes |
| **Opportunity** | Supply/demand analysis, SF per capita | ✅ Yes |
| **Rate Trends** | Historical pricing, occupancy trends | ✅ Yes |
| **Rental Comps** | Competitor facilities with detailed data | ✅✅ CRITICAL |
| **Operating Performance** | Only for CMBS loans - rarely available | ⚠️ If available |

**Pro Tip:** The **Rental Comps** report is the most valuable - it contains detailed competitor profiles that dramatically enhance your feasibility analysis.

## How the Cache System Works

### The Problem It Solves
Until you have live API access to TractIQ, you need a way to:
- **Reuse** market data across multiple site analyses in the same metro
- **Build up** a competitive intelligence database over time
- **Avoid re-uploading** the same PDFs for every feasibility study

### The Solution: Persistent Market Cache

The cache system stores TractIQ data by **market area** (e.g., "Phoenix Metro", "Austin TX") so you can:

1. Upload TractIQ PDFs once
2. Use the data for multiple sites in that market
3. Add new PDFs to existing markets as you gather more intelligence
4. Track data freshness and sources

## Using the TractIQ Cache (Step-by-Step)

### Initial Setup: First Market

1. **Navigate to Feasibility Report page**
2. **TractIQ Market Data Management section** (below property details)
3. **Select "+ Create New Market"** from dropdown
4. **Enter market name** (e.g., "Dallas Fort Worth Metro")
5. **Upload TractIQ PDFs** (up to 4 at once)
   - The system extracts data automatically
   - You'll see toast notifications for competitors, rates, unit mix found
6. **Click "💾 Save to TractIQ Cache"**
   - Data is now permanently stored
   - Can be reused for any site in this market

### Reusing Cached Data for New Sites

1. **Select your market** from the dropdown (e.g., "Dallas Fort Worth Metro")
2. **Cached data loads automatically** ✅
3. You'll see: "Loaded X cached TractIQ reports for [Market]"
4. **Generate your feasibility report** - it now includes TractIQ intelligence!

### Adding New PDFs to Existing Market

1. **Select existing market** from dropdown
2. **Upload new TractIQ PDFs**
3. **Click "💾 Save to TractIQ Cache"**
   - New data **merges** with existing cache
   - Competitor lists combine
   - Trends update
   - Unit mix aggregates

### Viewing Cached Markets

**Sidebar → TractIQ Cache section**
- Shows all cached markets
- Competitor counts
- Number of source PDFs
- Last update date

## How It Enhances Your Reports

### Before TractIQ Integration
- 10-15 competitors from Google Maps scraping
- Estimated occupancy from limited sources
- Generic unit mix recommendations
- No historical pricing context

### After TractIQ Integration
- **20+ competitor profiles** with verified data
- **Actual occupancy rates** from TractIQ database
- **Data-driven unit mix analysis** showing market composition
- **Historical rate trends** proving pricing power
- **Market-level benchmarks** (avg occupancy, supply, rates)

### New Report Section: "TRACTIQ MARKET INTELLIGENCE"

Your PDF reports now include a dedicated section showing:

1. **TractIQ Competitor Database**
   - Table with up to 20 facilities
   - Units, occupancy, rates, source PDF
   - Average market metrics

2. **Competitive Unit Mix Analysis**
   - Visual distribution of unit sizes
   - Dominant size identification
   - Optimization recommendations

3. **Historical Market Trends**
   - Time-series rate and occupancy data
   - Rate growth percentage calculation
   - Market trajectory analysis

4. **Market-Level Metrics**
   - Benchmarks for occupancy, rates, supply
   - Interpretation and recommendations

## Data Structure

### Cache Directory Structure
```
src/data/tractiq_cache/
├── cache_index.json              # Master index of all markets
├── phoenix_metro.json            # Phoenix market data
├── austin_tx.json                # Austin market data
└── dallas_fort_worth_metro.json  # DFW market data
```

### Market Data File Format
```json
{
  "market_id": "phoenix_metro",
  "market_name": "Phoenix Metro",
  "last_updated": "2026-01-21T10:30:00",
  "pdf_count": 3,
  "pdf_sources": {
    "Phoenix_Executive_Summary.pdf": { /* extracted data */ },
    "Phoenix_Rental_Comps.pdf": { /* extracted data */ },
    "Phoenix_Rate_Trends.pdf": { /* extracted data */ }
  },
  "aggregated_data": {
    "competitors": [ /* 45 facilities */ ],
    "unit_mix": { "5x5": 120, "10x10": 450, ... },
    "historical_trends": [ /* quarterly data */ ],
    "market_metrics": { "market_occupancy": 89.5, ... }
  }
}
```

## Best Practices

### 1. **Name Markets Consistently**
- ✅ Good: "Phoenix Metro", "Austin TX", "DFW Metroplex"
- ❌ Bad: "phx", "austin area", "Dallas"

### 2. **Upload Complete Report Sets**
- Get Executive Summary + Rental Comps at minimum
- Add Rate Trends for historical context
- Include Demographics for market validation

### 3. **Update Cache Regularly**
- TractIQ data changes quarterly
- Re-upload reports every 3-6 months
- System merges new data with existing

### 4. **Use Market Boundaries Thoughtfully**
- Don't mix Phoenix and Scottsdale into one cache
- Do combine if TractIQ report covers entire metro
- Match TractIQ's market definitions

### 5. **Verify Extraction Quality**
- Check toast notifications after upload
- Review "Cached Competitors" count
- Spot-check rates in generated reports

## Troubleshooting

### "No competitors found in PDF"
- **Cause:** PDF might be Executive Summary without competitor tables
- **Solution:** Upload the Rental Comps report instead

### "Market dropdown is empty"
- **Cause:** No markets cached yet
- **Solution:** Create your first market and upload PDFs

### "Cached data not appearing in report"
- **Cause:** Cache loaded but report not regenerated
- **Solution:** Click "Generate PDF Report" again after loading cache

### "Duplicate competitors in report"
- **Cause:** Same facility appears in multiple PDFs with slight name variations
- **Solution:** Normal - aggregation includes all sources for completeness

## Technical Details

### Extraction Technology
- **pdfplumber**: Extracts text and tables from PDFs
- **Regex patterns**: Identify competitor names, rates, occupancy
- **Table parsing**: Extracts structured data from TractIQ tables

### Data Persistence
- **JSON storage**: Human-readable cache files
- **Merge logic**: Combines new uploads with existing data
- **Deduplication**: Trends deduplicated by period, rates by value

### Integration Points
1. **Upload** → `src/pdf_processor.py::extract_pdf_data()`
2. **Cache** → `src/tractiq_cache.py::TractIQCache.store_market_data()`
3. **Retrieve** → `src/tractiq_cache.py::get_cached_tractiq_data()`
4. **Report** → `src/pdf_report_generator.py::generate_tractiq_insights_section()`

## Future Enhancements (When API Available)

Once you have TractIQ API access, the cache system provides:
- **Fallback data** when API is down
- **Historical snapshots** to track market changes
- **Offline capability** for field work

The cache architecture is designed to work alongside live API data, not replace it.

## Getting Started Checklist

- [ ] Navigate to **Feasibility Report** page
- [ ] Go to **TractIQ Market Data Management** section
- [ ] Select **"+ Create New Market"**
- [ ] Enter your first market name (e.g., your primary metro)
- [ ] Export **Rental Comps** report from TractIQ
- [ ] Upload the PDF
- [ ] Watch extraction notifications
- [ ] Click **"💾 Save to TractIQ Cache"**
- [ ] Generate a test feasibility report
- [ ] Find the new **"TRACTIQ MARKET INTELLIGENCE"** section
- [ ] Celebrate - you now have real competitive intelligence! 🎉

## Support

Questions or issues with TractIQ integration?
- Check cache status in sidebar
- Verify PDF upload notifications
- Review market stats in dropdown
- Examine generated reports for data quality

---

**Remember:** This system transforms your feasibility reports from "AI slop" into substantive market analysis backed by real competitive data. Use it consistently and build up your intelligence database over time.
