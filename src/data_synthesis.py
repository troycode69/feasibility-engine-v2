"""
Data Synthesis Engine
Merges and analyzes data from multiple sources (Google Maps, TractIQ PDFs/CSVs, Census)
to create unified, intelligent market intelligence.
"""

from typing import Dict, List
import statistics


def synthesize_competitor_data(
    google_competitors: List[Dict],
    tractiq_data: Dict[str, Dict]
) -> Dict:
    """
    Merge competitor data from Google Maps scraping and TractIQ uploads.
    Deduplicates, enriches, and provides unified competitor database.

    Returns:
        Dict with:
        - unified_competitors: Merged list with best data from each source
        - synthesis_stats: Metadata about data quality and sources
        - market_insights: AI-generated insights from the data
    """
    unified_competitors = []
    synthesis_stats = {
        "google_maps_count": len(google_competitors),
        "tractiq_count": 0,
        "enriched_count": 0,
        "total_unique": 0,
        "data_quality_score": 0
    }

    # Collect all TractIQ competitors
    tractiq_competitors = []
    for file_name, data in tractiq_data.items():
        if data.get('competitors'):
            tractiq_competitors.extend(data['competitors'])

    synthesis_stats["tractiq_count"] = len(tractiq_competitors)

    # Start with Google Maps data as base
    for gmap_comp in google_competitors:
        comp = gmap_comp.copy()
        comp["data_sources"] = ["Google Maps"]
        comp["data_quality"] = "basic"  # Google Maps provides name, location, distance

        # Try to enrich with TractIQ data (match by name similarity)
        enriched = enrich_competitor_with_tractiq(comp, tractiq_competitors)
        if enriched:
            synthesis_stats["enriched_count"] += 1
            comp.update(enriched)
            comp["data_sources"].append("TractIQ")
            comp["data_quality"] = "enhanced"

        unified_competitors.append(comp)

    # Add TractIQ competitors not found in Google Maps
    for tractiq_comp in tractiq_competitors:
        if not any(competitors_match(tractiq_comp, uc) for uc in unified_competitors):
            comp = tractiq_comp.copy()
            comp["data_sources"] = ["TractIQ"]
            comp["data_quality"] = "tractiq_only"
            unified_competitors.append(comp)

    synthesis_stats["total_unique"] = len(unified_competitors)

    # Calculate data quality score (0-100)
    competitors_with_rates = sum(1 for c in unified_competitors if 'rate_10x10' in c)
    competitors_with_occupancy = sum(1 for c in unified_competitors if 'occupancy' in c or 'occupancy_pct' in c)
    competitors_with_units = sum(1 for c in unified_competitors if 'units' in c)

    quality_metrics = [
        (competitors_with_rates / len(unified_competitors) * 100) if unified_competitors else 0,
        (competitors_with_occupancy / len(unified_competitors) * 100) if unified_competitors else 0,
        (competitors_with_units / len(unified_competitors) * 100) if unified_competitors else 0,
    ]
    synthesis_stats["data_quality_score"] = int(sum(quality_metrics) / len(quality_metrics))

    return {
        "unified_competitors": unified_competitors,
        "synthesis_stats": synthesis_stats,
        "market_insights": generate_market_insights(unified_competitors)
    }


def enrich_competitor_with_tractiq(gmap_comp: Dict, tractiq_comps: List[Dict]) -> Dict:
    """
    Find matching TractIQ data for a Google Maps competitor and return enrichment data.
    """
    gmap_name = gmap_comp.get('name', '').lower()

    for tractiq_comp in tractiq_comps:
        if competitors_match(gmap_comp, tractiq_comp):
            # Return TractIQ data that enriches Google Maps data
            enrichment = {}

            if 'rate_10x10' in tractiq_comp and 'rate_10x10_cc' not in gmap_comp:
                enrichment['rate_10x10_tractiq'] = tractiq_comp['rate_10x10']

            if 'occupancy' in tractiq_comp:
                enrichment['occupancy_tractiq'] = tractiq_comp['occupancy']

            if 'units' in tractiq_comp and 'units' not in gmap_comp:
                enrichment['units'] = tractiq_comp['units']

            if 'nrsf' in tractiq_comp:
                enrichment['nrsf_tractiq'] = tractiq_comp['nrsf']

            return enrichment if enrichment else None

    return None


def competitors_match(comp1: Dict, comp2: Dict) -> bool:
    """
    Determine if two competitor entries refer to the same facility.
    Uses fuzzy name matching and address similarity.
    """
    name1 = comp1.get('name', '').lower()
    name2 = comp2.get('name', '').lower()

    if not name1 or not name2:
        return False

    # Normalize names
    name1_clean = normalize_facility_name(name1)
    name2_clean = normalize_facility_name(name2)

    # Exact match
    if name1_clean == name2_clean:
        return True

    # Partial match (one contains the other, ignoring common suffixes)
    if name1_clean in name2_clean or name2_clean in name1_clean:
        return True

    # Check if key words match (brand names)
    brands = ['public storage', 'extra space', 'cubesmart', 'life storage', 'u-haul', 'smartstop']
    for brand in brands:
        if brand in name1_clean and brand in name2_clean:
            # Same brand - check if addresses are close
            if addresses_match(comp1.get('address', ''), comp2.get('address', '')):
                return True

    return False


def normalize_facility_name(name: str) -> str:
    """Remove common suffixes and normalize facility names for matching."""
    name = name.lower().strip()

    # Remove common suffixes
    suffixes = [
        'self storage', 'mini storage', 'storage', 'self-storage',
        'rv storage', 'boat storage', 'facilities', 'facility',
        'llc', 'inc', 'corp', 'company', 'co'
    ]

    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()

    # Remove special characters
    name = ''.join(c for c in name if c.isalnum() or c.isspace())

    return name.strip()


def addresses_match(addr1: str, addr2: str) -> bool:
    """Check if two addresses likely refer to the same location."""
    if not addr1 or not addr2:
        return False

    addr1 = addr1.lower()
    addr2 = addr2.lower()

    # Extract street numbers
    import re
    num1 = re.findall(r'^\d+', addr1)
    num2 = re.findall(r'^\d+', addr2)

    if num1 and num2:
        return num1[0] == num2[0]  # Same street number = likely same location

    return False


def synthesize_rate_data(
    google_competitors: List[Dict],
    tractiq_data: Dict[str, Dict]
) -> Dict:
    """
    Aggregate all rate data and provide market rate analysis.

    Returns:
        Dict with market rate statistics and insights
    """
    all_rates = []

    # Collect rates from Google Maps competitors
    for comp in google_competitors:
        if 'rate_10x10_cc' in comp:
            all_rates.append(comp['rate_10x10_cc'])

    # Collect rates from TractIQ data
    for file_name, data in tractiq_data.items():
        # From extracted rates
        if data.get('extracted_rates'):
            all_rates.extend(data['extracted_rates'])

        # From competitors
        if data.get('competitors'):
            for comp in data['competitors']:
                if 'rate_10x10' in comp:
                    all_rates.append(comp['rate_10x10'])

    # Remove duplicates and outliers
    all_rates = list(set(all_rates))
    all_rates = [r for r in all_rates if 40 <= r <= 600]  # Reasonable range

    if not all_rates:
        return {"available": False}

    return {
        "available": True,
        "sample_size": len(all_rates),
        "market_median_rate": int(statistics.median(all_rates)),
        "market_avg_rate": int(sum(all_rates) / len(all_rates)),
        "rate_range_low": min(all_rates),
        "rate_range_high": max(all_rates),
        "rate_std_dev": int(statistics.stdev(all_rates)) if len(all_rates) > 1 else 0,
        "all_rates_sorted": sorted(all_rates)
    }


def generate_market_insights(competitors: List[Dict]) -> List[str]:
    """
    Generate AI-style insights from competitor data.
    Returns list of insight strings to display in report.
    """
    insights = []

    if not competitors:
        return insights

    # === INSIGHT 1: Data Source Coverage ===
    tractiq_enhanced = sum(1 for c in competitors if 'TractIQ' in c.get('data_sources', []))
    if tractiq_enhanced > 0:
        pct = int(tractiq_enhanced / len(competitors) * 100)
        insights.append(f"{pct}% of identified competitors have enhanced data from TractIQ, providing verified occupancy and rate intelligence.")

    # === INSIGHT 2: Rate Distribution ===
    rates = [c.get('rate_10x10_tractiq') or c.get('rate_10x10_cc') or c.get('rate_10x10') for c in competitors if c.get('rate_10x10_tractiq') or c.get('rate_10x10_cc') or c.get('rate_10x10')]
    if len(rates) >= 3:
        avg_rate = sum(rates) / len(rates)
        min_rate = min(rates)
        max_rate = max(rates)
        spread = max_rate - min_rate

        insights.append(f"10x10 climate-controlled rates range from ${int(min_rate)} to ${int(max_rate)} (${int(spread)} spread), with market average at ${int(avg_rate)}.")

        if spread > 50:
            insights.append(f"Wide rate dispersion (${int(spread)}) suggests pricing opportunity for well-positioned, modern facilities to command premium rates.")

    # === INSIGHT 3: Occupancy Analysis ===
    occupancies = []
    for c in competitors:
        occ = c.get('occupancy_tractiq') or c.get('occupancy_pct') or c.get('occupancy')
        if occ:
            occupancies.append(occ)

    if len(occupancies) >= 3:
        avg_occ = sum(occupancies) / len(occupancies)
        high_occ_count = sum(1 for o in occupancies if o >= 90)

        if avg_occ >= 90:
            insights.append(f"Average occupancy of {avg_occ:.1f}% indicates strong demand pressure. {high_occ_count} facilities operating at/above 90% capacity.")
        elif avg_occ >= 85:
            insights.append(f"Market occupancy at {avg_occ:.1f}% signals healthy absorption with moderate lease-up risk for new supply.")
        else:
            insights.append(f"Market occupancy at {avg_occ:.1f}% below industry healthy threshold (85%+), suggesting competitive pricing environment.")

    # === INSIGHT 4: Facility Size Distribution ===
    units_data = [c.get('units') for c in competitors if c.get('units')]
    if len(units_data) >= 3:
        avg_units = int(sum(units_data) / len(units_data))
        large_facilities = sum(1 for u in units_data if u >= 500)

        if avg_units < 300:
            insights.append(f"Market dominated by smaller facilities (avg {avg_units} units), creating opportunity for large-format, institutional-grade development.")
        elif large_facilities >= 3:
            insights.append(f"{large_facilities} large facilities (500+ units) suggest professional competition requiring best-in-class execution.")

    return insights
