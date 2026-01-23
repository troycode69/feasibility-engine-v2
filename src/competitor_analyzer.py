"""
Competitor Pricing Analyzer for Self-Storage Feasibility Analysis

This module analyzes competitor data from:
- Google Maps scraper results
- TractiQ market intelligence cache
- Historical rate trends

Outputs:
- Average market rates by unit size
- Rate competitiveness analysis
- Occupancy benchmarks
- Market positioning recommendations
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import statistics
import json
from pathlib import Path


@dataclass
class CompetitorFacility:
    """Represents a single competitor facility"""
    name: str
    address: str
    distance_miles: float = 0.0
    latitude: float = 0.0
    longitude: float = 0.0
    source: str = ""  # "scraper" or "tractiq"

    # Pricing data
    rates: Dict[str, float] = field(default_factory=dict)  # {"5x5": 75.0, "10x10": 120.0}

    # Occupancy data (if available)
    occupancy_pct: Optional[float] = None
    unit_mix: Dict[str, int] = field(default_factory=dict)  # {"5x5": 50, "10x10": 80}


@dataclass
class MarketRateAnalysis:
    """Market rate analysis for a specific unit size"""
    unit_size: str
    competitor_count: int
    rates: List[float]

    # Statistics
    min_rate: float = 0.0
    max_rate: float = 0.0
    avg_rate: float = 0.0
    median_rate: float = 0.0
    std_dev: float = 0.0

    # Per SF metrics
    unit_sf: int = 0
    avg_rate_psf: float = 0.0
    median_rate_psf: float = 0.0

    def calculate_statistics(self):
        """Calculate all statistical metrics"""
        if not self.rates:
            return

        self.competitor_count = len(self.rates)
        self.min_rate = min(self.rates)
        self.max_rate = max(self.rates)
        self.avg_rate = statistics.mean(self.rates)
        self.median_rate = statistics.median(self.rates)

        if len(self.rates) > 1:
            self.std_dev = statistics.stdev(self.rates)
        else:
            self.std_dev = 0.0

        # Calculate per SF metrics if unit_sf is set
        if self.unit_sf > 0:
            self.avg_rate_psf = self.avg_rate / self.unit_sf
            self.median_rate_psf = self.median_rate / self.unit_sf


@dataclass
class MarketAnalysisReport:
    """Complete competitive market analysis"""
    market_name: str
    analysis_date: str
    competitor_count: int
    competitors: List[CompetitorFacility] = field(default_factory=list)

    # Rate analysis by unit size
    rate_analysis: Dict[str, MarketRateAnalysis] = field(default_factory=dict)

    # Market-wide metrics
    avg_occupancy: Optional[float] = None
    total_market_sf: int = 0
    population_3mi: Optional[float] = None
    sf_per_capita: Optional[float] = None

    # Competitive positioning
    nearest_competitor_distance: float = 999.0
    competitors_within_1mi: int = 0
    competitors_within_3mi: int = 0
    competitors_within_5mi: int = 0


# ============================================================================
# UNIT SIZE DEFINITIONS
# ============================================================================

UNIT_SIZES = {
    "5x5": 25,
    "5x10": 50,
    "5x15": 75,
    "10x10": 100,
    "10x15": 150,
    "10x20": 200,
    "10x25": 250,
    "10x30": 300,
    "10x40": 400
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def normalize_unit_size(size_str: str) -> Optional[str]:
    """
    Normalize unit size strings to standard format.

    Examples:
        "5 x 5" -> "5x5"
        "5X5" -> "5x5"
        "5' x 5'" -> "5x5"
        "5 by 5" -> "5x5"

    Args:
        size_str: Raw unit size string

    Returns:
        Normalized size (e.g., "5x5") or None if invalid
    """
    if not size_str:
        return None

    # Convert to lowercase and remove common characters
    normalized = size_str.lower().strip()
    normalized = normalized.replace("'", "").replace('"', "").replace(" ", "")
    normalized = normalized.replace("by", "x").replace("X", "x")

    # Check if it matches a known size
    if normalized in UNIT_SIZES:
        return normalized

    return None


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates using Haversine formula.

    Args:
        lat1, lon1: First coordinate
        lat2, lon2: Second coordinate

    Returns:
        Distance in miles
    """
    from math import radians, cos, sin, asin, sqrt

    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))

    # Earth radius in miles
    r = 3959

    return c * r


# ============================================================================
# COMPETITOR ANALYSIS FUNCTIONS
# ============================================================================

def load_tractiq_cache(market_id: str, cache_dir: str = "src/data/tractiq_cache") -> Optional[Dict]:
    """
    Load TractiQ cached data for a market.

    Args:
        market_id: Market identifier (e.g., "tn_372113104")
        cache_dir: Path to cache directory

    Returns:
        Cached market data dict or None if not found
    """
    cache_path = Path(cache_dir) / f"{market_id}.json"

    if not cache_path.exists():
        return None

    with open(cache_path, 'r') as f:
        return json.load(f)


def parse_tractiq_competitors(tractiq_data: Dict) -> List[CompetitorFacility]:
    """
    Parse TractiQ cached data into CompetitorFacility objects.

    Args:
        tractiq_data: Loaded TractiQ market data

    Returns:
        List of CompetitorFacility objects
    """
    facilities = []

    if "aggregated_data" not in tractiq_data:
        return facilities

    aggregated = tractiq_data["aggregated_data"]

    # Parse competitors list
    if "competitors" in aggregated:
        for comp_data in aggregated["competitors"]:
            facility = CompetitorFacility(
                name=comp_data.get("name", "Unknown"),
                address=comp_data.get("address", ""),
                source="tractiq"
            )

            # Parse coordinates if available
            if "coordinates" in comp_data:
                coords = comp_data["coordinates"]
                facility.latitude = coords.get("lat", 0.0)
                facility.longitude = coords.get("lng", 0.0)

            facilities.append(facility)

    # Parse rate data if available
    if "extracted_rates" in aggregated:
        # TractiQ rate data is aggregated, not per-facility
        # We'll handle this separately in analyze_market_rates()
        pass

    return facilities


def parse_scraper_competitors(scraper_results: List[Dict]) -> List[CompetitorFacility]:
    """
    Parse Google Maps scraper results into CompetitorFacility objects.

    Args:
        scraper_results: List of scraper result dicts with keys: name, address, distance, lat, lng

    Returns:
        List of CompetitorFacility objects
    """
    facilities = []

    for result in scraper_results:
        facility = CompetitorFacility(
            name=result.get("name", "Unknown"),
            address=result.get("address", ""),
            distance_miles=result.get("distance", 0.0),
            latitude=result.get("lat", 0.0),
            longitude=result.get("lng", 0.0),
            source="scraper"
        )

        facilities.append(facility)

    return facilities


def analyze_market_rates(competitors: List[CompetitorFacility],
                         tractiq_data: Optional[Dict] = None) -> Dict[str, MarketRateAnalysis]:
    """
    Analyze market rates across all competitors.

    Args:
        competitors: List of CompetitorFacility objects
        tractiq_data: Optional TractiQ data with aggregated rates

    Returns:
        Dict mapping unit size to MarketRateAnalysis
    """
    rate_analyses = {}

    # Initialize analysis for each standard unit size
    for size, sf in UNIT_SIZES.items():
        analysis = MarketRateAnalysis(
            unit_size=size,
            competitor_count=0,
            rates=[],
            unit_sf=sf
        )
        rate_analyses[size] = analysis

    # Collect rates from competitors
    for competitor in competitors:
        for size, rate in competitor.rates.items():
            normalized_size = normalize_unit_size(size)
            if normalized_size and normalized_size in rate_analyses:
                rate_analyses[normalized_size].rates.append(rate)

    # If TractiQ data available, add aggregated rates
    if tractiq_data and "aggregated_data" in tractiq_data:
        agg = tractiq_data["aggregated_data"]

        # Check for extracted_rates
        if "extracted_rates" in agg:
            for rate_entry in agg["extracted_rates"]:
                size = normalize_unit_size(rate_entry.get("size", ""))
                rate = rate_entry.get("rate", 0)

                if size and size in rate_analyses and rate > 0:
                    rate_analyses[size].rates.append(rate)

        # Check for unit_mix with rate data
        if "unit_mix" in agg and isinstance(agg["unit_mix"], dict):
            for size, data in agg["unit_mix"].items():
                normalized_size = normalize_unit_size(size)

                # TractiQ unit_mix can be either a count or a dict with rate info
                if isinstance(data, dict) and "rate" in data:
                    rate = data["rate"]
                    if normalized_size and normalized_size in rate_analyses and rate > 0:
                        rate_analyses[normalized_size].rates.append(rate)

    # Calculate statistics for each unit size
    for analysis in rate_analyses.values():
        analysis.calculate_statistics()

    # Remove unit sizes with no data
    rate_analyses = {size: analysis for size, analysis in rate_analyses.items()
                     if analysis.competitor_count > 0}

    return rate_analyses


def calculate_market_metrics(competitors: List[CompetitorFacility],
                            site_lat: float, site_lon: float) -> Dict:
    """
    Calculate market-wide competitive metrics.

    Args:
        competitors: List of CompetitorFacility objects
        site_lat, site_lon: Subject site coordinates

    Returns:
        Dict with metrics: nearest_competitor_distance, competitors_within_Xmi, avg_occupancy
    """
    metrics = {
        "nearest_competitor_distance": 999.0,
        "competitors_within_1mi": 0,
        "competitors_within_3mi": 0,
        "competitors_within_5mi": 0,
        "avg_occupancy": None,
        "total_market_sf": 0
    }

    occupancy_values = []
    total_sf = 0

    for competitor in competitors:
        # Calculate distance if coordinates available
        if competitor.latitude and competitor.longitude:
            distance = calculate_distance(site_lat, site_lon,
                                        competitor.latitude, competitor.longitude)
            competitor.distance_miles = distance

            # Update nearest competitor
            if distance < metrics["nearest_competitor_distance"]:
                metrics["nearest_competitor_distance"] = distance

            # Count by radius
            if distance <= 1.0:
                metrics["competitors_within_1mi"] += 1
            if distance <= 3.0:
                metrics["competitors_within_3mi"] += 1
            if distance <= 5.0:
                metrics["competitors_within_5mi"] += 1

        # Collect occupancy data
        if competitor.occupancy_pct is not None:
            occupancy_values.append(competitor.occupancy_pct)

        # Sum total market SF
        if competitor.unit_mix:
            for size, count in competitor.unit_mix.items():
                normalized_size = normalize_unit_size(size)
                if normalized_size and normalized_size in UNIT_SIZES:
                    total_sf += count * UNIT_SIZES[normalized_size]

    # Calculate average occupancy
    if occupancy_values:
        metrics["avg_occupancy"] = statistics.mean(occupancy_values)

    metrics["total_market_sf"] = total_sf

    return metrics


def create_market_analysis(market_name: str, market_id: Optional[str] = None,
                          scraper_results: Optional[List[Dict]] = None,
                          site_lat: Optional[float] = None,
                          site_lon: Optional[float] = None,
                          population_3mi: Optional[float] = None) -> MarketAnalysisReport:
    """
    Create comprehensive market analysis from all available data sources.

    Args:
        market_name: Human-readable market name
        market_id: TractiQ market ID (e.g., "tn_372113104") if available
        scraper_results: Google Maps scraper results
        site_lat, site_lon: Subject site coordinates for distance calculations
        population_3mi: Population within 3-mile radius for SF/capita calculation

    Returns:
        Complete MarketAnalysisReport
    """
    from datetime import datetime

    report = MarketAnalysisReport(
        market_name=market_name,
        analysis_date=datetime.now().strftime("%Y-%m-%d"),
        competitor_count=0
    )

    # Load TractiQ data if market_id provided
    tractiq_data = None
    if market_id:
        tractiq_data = load_tractiq_cache(market_id)

    # Parse competitors from all sources
    competitors = []

    if tractiq_data:
        competitors.extend(parse_tractiq_competitors(tractiq_data))

    if scraper_results:
        competitors.extend(parse_scraper_competitors(scraper_results))

    report.competitors = competitors
    report.competitor_count = len(competitors)

    # Analyze rates
    report.rate_analysis = analyze_market_rates(competitors, tractiq_data)

    # Calculate market metrics if site coordinates provided
    if site_lat and site_lon:
        metrics = calculate_market_metrics(competitors, site_lat, site_lon)

        report.nearest_competitor_distance = metrics["nearest_competitor_distance"]
        report.competitors_within_1mi = metrics["competitors_within_1mi"]
        report.competitors_within_3mi = metrics["competitors_within_3mi"]
        report.competitors_within_5mi = metrics["competitors_within_5mi"]
        report.avg_occupancy = metrics["avg_occupancy"]
        report.total_market_sf = metrics["total_market_sf"]

    # Calculate SF per capita if population provided
    report.population_3mi = population_3mi
    if population_3mi and report.total_market_sf > 0:
        report.sf_per_capita = report.total_market_sf / population_3mi

    return report


def compare_proposed_rates(proposed_rates: Dict[str, float],
                          market_analysis: MarketRateAnalysis) -> Dict:
    """
    Compare proposed rates against market averages.

    Args:
        proposed_rates: Dict of proposed rates {"5x5": 70.0, "10x10": 115.0}
        market_analysis: MarketRateAnalysis object

    Returns:
        Dict with competitiveness metrics
    """
    comparisons = {}

    for size, proposed_rate in proposed_rates.items():
        normalized_size = normalize_unit_size(size)

        if not normalized_size or normalized_size not in market_analysis.rate_analysis:
            continue

        market = market_analysis.rate_analysis[normalized_size]

        if market.avg_rate == 0:
            continue

        diff_pct = ((proposed_rate - market.avg_rate) / market.avg_rate) * 100

        comparisons[normalized_size] = {
            "proposed_rate": proposed_rate,
            "market_avg": market.avg_rate,
            "market_median": market.median_rate,
            "difference_pct": diff_pct,
            "positioning": "below_market" if diff_pct < -2 else ("at_market" if diff_pct < 2 else "above_market")
        }

    return comparisons


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=== Competitor Pricing Analyzer Test ===\n")

    # Test with Nashville TN 37211-3104 cached data
    print("Loading Nashville market data...")
    market_analysis = create_market_analysis(
        market_name="Nashville TN 37211-3104",
        market_id="tn_372113104",
        site_lat=36.1147,  # Example Nashville coordinates
        site_lon=-86.6734,
        population_3mi=85000
    )

    print(f"Market: {market_analysis.market_name}")
    print(f"Analysis Date: {market_analysis.analysis_date}")
    print(f"Competitors Found: {market_analysis.competitor_count}\n")

    print("=== Rate Analysis ===")
    for size, analysis in market_analysis.rate_analysis.items():
        if analysis.competitor_count > 0:
            print(f"\n{size} ({analysis.unit_sf} SF):")
            print(f"  Competitors: {analysis.competitor_count}")
            print(f"  Average Rate: ${analysis.avg_rate:.2f}/mo (${analysis.avg_rate_psf:.3f}/SF)")
            print(f"  Median Rate: ${analysis.median_rate:.2f}/mo")
            print(f"  Range: ${analysis.min_rate:.2f} - ${analysis.max_rate:.2f}")
            if analysis.std_dev > 0:
                print(f"  Std Dev: ${analysis.std_dev:.2f}")

    print("\n=== Market Metrics ===")
    print(f"Nearest Competitor: {market_analysis.nearest_competitor_distance:.2f} miles")
    print(f"Competitors within 1 mile: {market_analysis.competitors_within_1mi}")
    print(f"Competitors within 3 miles: {market_analysis.competitors_within_3mi}")
    print(f"Competitors within 5 miles: {market_analysis.competitors_within_5mi}")

    if market_analysis.avg_occupancy:
        print(f"Average Occupancy: {market_analysis.avg_occupancy:.1f}%")

    if market_analysis.sf_per_capita:
        print(f"SF Per Capita: {market_analysis.sf_per_capita:.2f}")

    print("\n=== Rate Competitiveness Test ===")
    proposed_rates = {
        "5x5": 65.0,
        "5x10": 80.0,
        "10x10": 110.0,
        "10x15": 135.0,
        "10x20": 160.0
    }

    comparisons = compare_proposed_rates(proposed_rates, market_analysis)
    for size, comp in comparisons.items():
        print(f"\n{size}:")
        print(f"  Proposed: ${comp['proposed_rate']:.2f}")
        print(f"  Market Avg: ${comp['market_avg']:.2f}")
        print(f"  Difference: {comp['difference_pct']:+.1f}%")
        print(f"  Positioning: {comp['positioning']}")
