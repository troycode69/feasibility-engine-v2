"""
Market Analysis Module for Self-Storage Feasibility

This module performs supply/demand analysis and market saturation scoring:
- SF per capita calculations
- Market saturation assessment
- Supply gap identification
- Demand forecasting

Key metrics:
- Industry benchmark: 5-7 SF per capita is balanced
- <5 SF/capita = undersupplied (opportunity)
- >7 SF/capita = oversupplied (saturated)
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class MarketSupplyMetrics:
    """Supply-side market metrics"""
    total_market_sf: int = 0
    competitor_count: int = 0
    facilities_within_1mi: int = 0
    facilities_within_3mi: int = 0
    facilities_within_5mi: int = 0

    # Unit mix breakdown
    unit_mix_market: Dict[str, int] = field(default_factory=dict)

    # Development pipeline
    facilities_under_construction: int = 0
    planned_sf_coming: int = 0


@dataclass
class MarketDemandMetrics:
    """Demand-side market metrics"""
    population_1mi: float = 0
    population_3mi: float = 0
    population_5mi: float = 0

    households_3mi: float = 0
    median_income_3mi: float = 0
    renter_occupied_pct: float = 0

    # Growth indicators
    population_growth_rate: float = 0  # Annual % growth
    job_growth_rate: float = 0


@dataclass
class SupplyDemandAnalysis:
    """Complete supply/demand analysis"""
    market_name: str
    analysis_date: str

    supply: MarketSupplyMetrics = field(default_factory=MarketSupplyMetrics)
    demand: MarketDemandMetrics = field(default_factory=MarketDemandMetrics)

    # Calculated metrics
    sf_per_capita_1mi: float = 0.0
    sf_per_capita_3mi: float = 0.0
    sf_per_capita_5mi: float = 0.0

    balance_tier_3mi: str = ""  # "undersupplied", "balanced", "oversupplied"
    saturation_score: int = 0  # 0-100 (100 = severely oversaturated)

    # Gap analysis
    supply_gap_sf: int = 0  # Negative = undersupplied, Positive = oversupplied
    recommended_size_sf: int = 0

    def calculate_metrics(self):
        """Calculate all derived metrics"""
        # SF per capita calculations
        if self.demand.population_1mi > 0:
            self.sf_per_capita_1mi = self.supply.total_market_sf / self.demand.population_1mi

        if self.demand.population_3mi > 0:
            self.sf_per_capita_3mi = self.supply.total_market_sf / self.demand.population_3mi

        if self.demand.population_5mi > 0:
            self.sf_per_capita_5mi = self.supply.total_market_sf / self.demand.population_5mi

        # Market balance tier (using 3-mile radius as standard)
        sf_per_cap = self.sf_per_capita_3mi
        if sf_per_cap < 5.0:
            self.balance_tier_3mi = "undersupplied"
        elif sf_per_cap <= 7.0:
            self.balance_tier_3mi = "balanced"
        else:
            self.balance_tier_3mi = "oversupplied"

        # Saturation score (0-100, where 100 = severely oversaturated)
        # Based on SF/capita: 0-4 = low saturation, 5-7 = moderate, 8+ = high
        if sf_per_cap <= 4.0:
            self.saturation_score = int((sf_per_cap / 4.0) * 30)  # 0-30 range
        elif sf_per_cap <= 7.0:
            excess = sf_per_cap - 4.0
            self.saturation_score = 30 + int((excess / 3.0) * 30)  # 30-60 range
        elif sf_per_cap <= 10.0:
            excess = sf_per_cap - 7.0
            self.saturation_score = 60 + int((excess / 3.0) * 25)  # 60-85 range
        else:
            self.saturation_score = min(100, 85 + int((sf_per_cap - 10.0) * 3))  # 85-100

        # Supply gap calculation
        # Target: 6 SF per capita (middle of balanced range)
        target_sf = self.demand.population_3mi * 6.0
        self.supply_gap_sf = int(self.supply.total_market_sf - target_sf)

        # Recommended facility size
        # If undersupplied, recommend filling some of the gap
        # If oversupplied, recommend smaller facility or none
        if self.supply_gap_sf < 0:
            # Undersupplied - recommend filling 30-40% of gap
            gap_to_fill = abs(self.supply_gap_sf) * 0.35
            self.recommended_size_sf = int(gap_to_fill)
        else:
            # Oversupplied - recommend smaller facility if other factors strong
            self.recommended_size_sf = 40000  # Minimum viable size


# ============================================================================
# ANALYSIS FUNCTIONS
# ============================================================================

def calculate_market_supply(tractiq_data: Optional[Dict] = None,
                           scraper_results: Optional[List[Dict]] = None,
                           site_lat: Optional[float] = None,
                           site_lon: Optional[float] = None) -> MarketSupplyMetrics:
    """
    Calculate market supply metrics from all available data.

    Args:
        tractiq_data: TractiQ cached market data
        scraper_results: Google Maps scraper results
        site_lat, site_lon: Subject site coordinates for distance calculations

    Returns:
        MarketSupplyMetrics object
    """
    try:
        from src.competitor_analyzer import calculate_distance, UNIT_SIZES
    except ModuleNotFoundError:
        from competitor_analyzer import calculate_distance, UNIT_SIZES

    metrics = MarketSupplyMetrics()

    # Combine competitor lists
    competitors = []

    if tractiq_data and "aggregated_data" in tractiq_data:
        agg = tractiq_data["aggregated_data"]

        # Get competitor count
        if "competitors" in agg:
            competitors.extend(agg["competitors"])
            metrics.competitor_count = len(agg["competitors"])

        # Get unit mix for total SF calculation
        if "unit_mix" in agg:
            metrics.unit_mix_market = agg["unit_mix"]

            for size, count in agg["unit_mix"].items():
                size_normalized = size.lower().replace(" ", "")
                if size_normalized in UNIT_SIZES:
                    metrics.total_market_sf += count * UNIT_SIZES[size_normalized]

    if scraper_results:
        # Add scraper competitors
        for result in scraper_results:
            competitors.append({
                "name": result.get("name", ""),
                "address": result.get("address", ""),
                "lat": result.get("lat", 0.0),
                "lng": result.get("lng", 0.0),
                "distance": result.get("distance", 999.0)
            })

    # Calculate distance-based metrics if site coordinates provided
    if site_lat and site_lon:
        for comp in competitors:
            if "lat" in comp and "lng" in comp and comp["lat"] and comp["lng"]:
                distance = calculate_distance(site_lat, site_lon,
                                            comp["lat"], comp["lng"])

                if distance <= 1.0:
                    metrics.facilities_within_1mi += 1
                if distance <= 3.0:
                    metrics.facilities_within_3mi += 1
                if distance <= 5.0:
                    metrics.facilities_within_5mi += 1
            elif "distance" in comp:
                # Use pre-calculated distance from scraper
                distance = comp["distance"]
                if distance <= 1.0:
                    metrics.facilities_within_1mi += 1
                if distance <= 3.0:
                    metrics.facilities_within_3mi += 1
                if distance <= 5.0:
                    metrics.facilities_within_5mi += 1

    return metrics


def calculate_market_demand(demographics: Dict) -> MarketDemandMetrics:
    """
    Calculate market demand metrics from demographic data.

    Args:
        demographics: Dict with keys like population_3mi, median_income, growth_rate, etc.

    Returns:
        MarketDemandMetrics object
    """
    metrics = MarketDemandMetrics()

    # Map demographic data to metrics
    metrics.population_1mi = demographics.get("population_1mi", 0)
    metrics.population_3mi = demographics.get("population_3mi", 0)
    metrics.population_5mi = demographics.get("population_5mi", 0)

    metrics.households_3mi = demographics.get("households_3mi", 0)
    metrics.median_income_3mi = demographics.get("median_income", 0)
    metrics.renter_occupied_pct = demographics.get("renter_occupied_pct", 0)

    metrics.population_growth_rate = demographics.get("growth_rate", 0)
    metrics.job_growth_rate = demographics.get("job_growth", 0)

    return metrics


def perform_supply_demand_analysis(market_name: str,
                                   demographics: Dict,
                                   tractiq_data: Optional[Dict] = None,
                                   scraper_results: Optional[List[Dict]] = None,
                                   site_lat: Optional[float] = None,
                                   site_lon: Optional[float] = None) -> SupplyDemandAnalysis:
    """
    Perform complete supply/demand analysis.

    Args:
        market_name: Human-readable market name
        demographics: Dict with population, income, growth, etc.
        tractiq_data: TractiQ cached market data
        scraper_results: Google Maps scraper results
        site_lat, site_lon: Subject site coordinates

    Returns:
        Complete SupplyDemandAnalysis
    """
    from datetime import datetime

    analysis = SupplyDemandAnalysis(
        market_name=market_name,
        analysis_date=datetime.now().strftime("%Y-%m-%d")
    )

    # Calculate supply metrics
    analysis.supply = calculate_market_supply(
        tractiq_data=tractiq_data,
        scraper_results=scraper_results,
        site_lat=site_lat,
        site_lon=site_lon
    )

    # Calculate demand metrics
    analysis.demand = calculate_market_demand(demographics)

    # Calculate derived metrics
    analysis.calculate_metrics()

    return analysis


def assess_market_opportunity(analysis: SupplyDemandAnalysis) -> Dict:
    """
    Assess market opportunity based on supply/demand analysis.

    Args:
        analysis: Complete SupplyDemandAnalysis

    Returns:
        Dict with opportunity assessment and recommendations
    """
    assessment = {
        "opportunity_score": 0,  # 0-100
        "opportunity_tier": "",
        "key_findings": [],
        "recommendations": [],
        "risk_factors": []
    }

    # Calculate opportunity score (0-100, higher = better opportunity)
    score = 0

    # Factor 1: SF per capita (40 points max)
    sf_per_cap = analysis.sf_per_capita_3mi
    if sf_per_cap < 4.0:
        score += 40  # Excellent - significantly undersupplied
        assessment["key_findings"].append(f"Market is significantly undersupplied at {sf_per_cap:.1f} SF/capita (target: 6.0)")
    elif sf_per_cap < 5.5:
        score += 30  # Good - moderately undersupplied
        assessment["key_findings"].append(f"Market is moderately undersupplied at {sf_per_cap:.1f} SF/capita")
    elif sf_per_cap < 7.0:
        score += 20  # Fair - balanced market
        assessment["key_findings"].append(f"Market is balanced at {sf_per_cap:.1f} SF/capita")
    elif sf_per_cap < 9.0:
        score += 10  # Weak - moderately oversupplied
        assessment["key_findings"].append(f"Market is moderately oversupplied at {sf_per_cap:.1f} SF/capita")
        assessment["risk_factors"].append("Market shows moderate oversupply")
    else:
        score += 0  # Poor - significantly oversupplied
        assessment["key_findings"].append(f"Market is significantly oversupplied at {sf_per_cap:.1f} SF/capita")
        assessment["risk_factors"].append("Market is severely oversupplied")

    # Factor 2: Population growth (25 points max)
    growth = analysis.demand.population_growth_rate
    if growth >= 2.0:
        score += 25
        assessment["key_findings"].append(f"Strong population growth at {growth:.1f}% annually")
    elif growth >= 1.0:
        score += 18
        assessment["key_findings"].append(f"Moderate population growth at {growth:.1f}% annually")
    elif growth >= 0.5:
        score += 12
    elif growth >= 0:
        score += 5
        assessment["risk_factors"].append("Slow population growth")
    else:
        score += 0
        assessment["risk_factors"].append("Negative population growth")

    # Factor 3: Competitive density (20 points max)
    facilities_3mi = analysis.supply.facilities_within_3mi
    pop_3mi = analysis.demand.population_3mi
    if pop_3mi > 0:
        facilities_per_10k = (facilities_3mi / pop_3mi) * 10000
        if facilities_per_10k < 0.5:
            score += 20  # Very low density
            assessment["key_findings"].append("Low competitive density - opportunity")
        elif facilities_per_10k < 1.0:
            score += 15  # Low density
        elif facilities_per_10k < 1.5:
            score += 10  # Moderate density
        elif facilities_per_10k < 2.0:
            score += 5  # High density
            assessment["risk_factors"].append("High competitive density")
        else:
            score += 0  # Very high density
            assessment["risk_factors"].append("Very high competitive density")

    # Factor 4: Demographics (15 points max)
    income = analysis.demand.median_income_3mi
    renter_pct = analysis.demand.renter_occupied_pct

    if income >= 75000:
        score += 8
    elif income >= 60000:
        score += 6
    elif income >= 45000:
        score += 3

    if renter_pct >= 40:
        score += 7
    elif renter_pct >= 30:
        score += 5
    elif renter_pct >= 25:
        score += 2

    assessment["opportunity_score"] = min(100, score)

    # Determine tier
    if score >= 80:
        assessment["opportunity_tier"] = "Excellent"
        assessment["recommendations"].append("Strong market opportunity - proceed with confidence")
    elif score >= 65:
        assessment["opportunity_tier"] = "Good"
        assessment["recommendations"].append("Good market opportunity - standard risk profile")
    elif score >= 50:
        assessment["opportunity_tier"] = "Fair"
        assessment["recommendations"].append("Fair opportunity - requires strong execution")
        assessment["risk_factors"].append("Market requires careful positioning")
    elif score >= 35:
        assessment["opportunity_tier"] = "Weak"
        assessment["recommendations"].append("Weak opportunity - proceed with caution")
        assessment["risk_factors"].append("Multiple market challenges present")
    else:
        assessment["opportunity_tier"] = "Poor"
        assessment["recommendations"].append("Poor opportunity - not recommended")
        assessment["risk_factors"].append("Market conditions not favorable")

    # Facility size recommendation
    if analysis.recommended_size_sf > 0:
        assessment["recommendations"].append(
            f"Recommended facility size: {analysis.recommended_size_sf:,} NRSF"
        )

    return assessment


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=== Market Supply/Demand Analysis Test ===\n")

    # Test with sample data
    demographics = {
        "population_1mi": 25000,
        "population_3mi": 75000,
        "population_5mi": 150000,
        "households_3mi": 28000,
        "median_income": 72000,
        "renter_occupied_pct": 38.5,
        "growth_rate": 1.8,
        "job_growth": 2.1
    }

    # Load TractiQ data
    from pathlib import Path
    tractiq_path = Path("data/tractiq_cache/tn_372113104.json")
    if tractiq_path.exists():
        import json
        with open(tractiq_path) as f:
            tractiq_data = json.load(f)
    else:
        tractiq_data = None

    analysis = perform_supply_demand_analysis(
        market_name="Test Market - Nashville TN",
        demographics=demographics,
        tractiq_data=tractiq_data,
        site_lat=36.1147,
        site_lon=-86.6734
    )

    print(f"Market: {analysis.market_name}")
    print(f"Analysis Date: {analysis.analysis_date}\n")

    print("=== SUPPLY METRICS ===")
    print(f"Total Market SF: {analysis.supply.total_market_sf:,}")
    print(f"Competitor Count: {analysis.supply.competitor_count}")
    print(f"Facilities within 1 mile: {analysis.supply.facilities_within_1mi}")
    print(f"Facilities within 3 miles: {analysis.supply.facilities_within_3mi}")
    print(f"Facilities within 5 miles: {analysis.supply.facilities_within_5mi}\n")

    print("=== DEMAND METRICS ===")
    print(f"Population (3-Mile): {analysis.demand.population_3mi:,}")
    print(f"Median Income: ${analysis.demand.median_income_3mi:,}")
    print(f"Renter-Occupied: {analysis.demand.renter_occupied_pct:.1f}%")
    print(f"Population Growth: {analysis.demand.population_growth_rate:.1f}%\n")

    print("=== SUPPLY/DEMAND BALANCE ===")
    print(f"SF Per Capita (3-Mile): {analysis.sf_per_capita_3mi:.2f}")
    print(f"Market Balance: {analysis.balance_tier_3mi}")
    print(f"Saturation Score: {analysis.saturation_score}/100")
    print(f"Supply Gap: {analysis.supply_gap_sf:,} SF")
    print(f"Recommended Size: {analysis.recommended_size_sf:,} NRSF\n")

    # Opportunity assessment
    opportunity = assess_market_opportunity(analysis)

    print("=== OPPORTUNITY ASSESSMENT ===")
    print(f"Opportunity Score: {opportunity['opportunity_score']}/100")
    print(f"Opportunity Tier: {opportunity['opportunity_tier']}\n")

    print("Key Findings:")
    for finding in opportunity["key_findings"]:
        print(f"  • {finding}")

    if opportunity["risk_factors"]:
        print("\nRisk Factors:")
        for risk in opportunity["risk_factors"]:
            print(f"  ⚠ {risk}")

    print("\nRecommendations:")
    for rec in opportunity["recommendations"]:
        print(f"  → {rec}")
