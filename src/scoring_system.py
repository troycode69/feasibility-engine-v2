"""
100-Point Site Scoring System for Self-Storage Feasibility Analysis

This module implements the proprietary StorSageHQ scoring methodology:
- Demographics: 25 points
- Supply/Demand: 25 points
- Site Attributes: 25 points
- Competitive Positioning: 15 points
- Economic Market: 10 points
TOTAL: 100 points

Scoring tiers:
- 85-100: Excellent - PROCEED with high confidence
- 70-84: Good - PROCEED with standard confidence
- 55-69: Fair - PROCEED WITH CAUTION (further analysis recommended)
- 40-54: Weak - PROCEED WITH EXTREME CAUTION
- 0-39: Poor - DO NOT PROCEED

"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
try:
    import src.benchmarks as benchmarks
except ModuleNotFoundError:
    import benchmarks


@dataclass
class DemographicScores:
    """Demographics category (25 points total)"""
    population_3mi: float = 0
    population_3mi_score: int = 0
    population_3mi_tier: str = ""

    growth_rate: float = 0  # Annual % growth
    growth_rate_score: int = 0
    growth_rate_tier: str = ""

    median_income: float = 0
    median_income_score: int = 0
    median_income_tier: str = ""

    renter_occupied_pct: float = 0
    renter_occupied_pct_score: int = 0
    renter_occupied_pct_tier: str = ""

    median_age: float = 0
    median_age_score: int = 0
    median_age_tier: str = ""

    total_score: int = 0
    max_score: int = 25

    def calculate_total(self):
        """Sum all demographic scores"""
        self.total_score = (
            self.population_3mi_score +
            self.growth_rate_score +
            self.median_income_score +
            self.renter_occupied_pct_score +
            self.median_age_score
        )
        return self.total_score


@dataclass
class SupplyDemandScores:
    """Supply/Demand category (25 points total)"""
    sf_per_capita: float = 0
    sf_per_capita_score: int = 0
    sf_per_capita_tier: str = ""

    existing_occupancy_avg: float = 0
    existing_occupancy_avg_score: int = 0
    existing_occupancy_avg_tier: str = ""

    distance_to_nearest: float = 0
    distance_to_nearest_score: int = 0
    distance_to_nearest_tier: str = ""

    market_rate_trend: float = 0  # % change past 12 months
    market_rate_trend_score: int = 0
    market_rate_trend_tier: str = ""

    development_pipeline: int = 0  # Count of facilities in planning/construction
    development_pipeline_score: int = 0
    development_pipeline_tier: str = ""

    total_score: int = 0
    max_score: int = 25

    def calculate_total(self):
        """Sum all supply/demand scores"""
        self.total_score = (
            self.sf_per_capita_score +
            self.existing_occupancy_avg_score +
            self.distance_to_nearest_score +
            self.market_rate_trend_score +
            self.development_pipeline_score
        )
        return self.total_score


@dataclass
class SiteAttributeScores:
    """Site Attributes category (25 points total)"""
    visibility_rating: int = 0  # 1-5 subjective scale
    visibility_score: int = 0
    visibility_tier: str = ""

    traffic_count: int = 0  # Average Daily Traffic
    traffic_count_score: int = 0
    traffic_count_tier: str = ""

    access_quality: int = 0  # 1-5 subjective scale
    access_quality_score: int = 0
    access_quality_tier: str = ""

    lot_size_ratio: float = 0  # Lot size / building footprint ratio
    lot_size_ratio_score: int = 0
    lot_size_ratio_tier: str = ""

    zoning_status: int = 0  # 1=Approved, 2=Conditional, 3=Variance needed, 4=Not allowed
    zoning_status_score: int = 0
    zoning_status_tier: str = ""

    total_score: int = 0
    max_score: int = 25

    def calculate_total(self):
        """Sum all site attribute scores"""
        self.total_score = (
            self.visibility_score +
            self.traffic_count_score +
            self.access_quality_score +
            self.lot_size_ratio_score +
            self.zoning_status_score
        )
        return self.total_score


@dataclass
class CompetitivePositioningScores:
    """Competitive Positioning category (15 points total)"""
    rate_competitiveness: float = 0  # Proposed rate vs market avg (% difference)
    rate_competitiveness_score: int = 0  # 0-5 points

    product_differentiation: int = 0  # 1-5 subjective assessment
    product_differentiation_score: int = 0  # 0-5 points

    brand_strength: int = 0  # 1-5 subjective (StorSageHQ brand awareness in market)
    brand_strength_score: int = 0  # 0-5 points

    total_score: int = 0
    max_score: int = 15

    def calculate_total(self):
        """Sum all competitive positioning scores"""
        self.total_score = (
            self.rate_competitiveness_score +
            self.product_differentiation_score +
            self.brand_strength_score
        )
        return self.total_score


@dataclass
class EconomicMarketScores:
    """Economic Market category (10 points total)"""
    unemployment_rate: float = 0  # Local unemployment %
    unemployment_score: int = 0  # 0-3 points

    job_growth: float = 0  # % job growth past 12 months
    job_growth_score: int = 0  # 0-4 points

    gdp_growth: float = 0  # State/metro GDP growth %
    gdp_growth_score: int = 0  # 0-3 points

    total_score: int = 0
    max_score: int = 10

    def calculate_total(self):
        """Sum all economic market scores"""
        self.total_score = (
            self.unemployment_score +
            self.job_growth_score +
            self.gdp_growth_score
        )
        return self.total_score


@dataclass
class SiteScoreCard:
    """Complete 100-point site score card"""
    site_name: str = ""
    site_address: str = ""
    analysis_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    demographics: DemographicScores = field(default_factory=DemographicScores)
    supply_demand: SupplyDemandScores = field(default_factory=SupplyDemandScores)
    site_attributes: SiteAttributeScores = field(default_factory=SiteAttributeScores)
    competitive_positioning: CompetitivePositioningScores = field(default_factory=CompetitivePositioningScores)
    economic_market: EconomicMarketScores = field(default_factory=EconomicMarketScores)

    total_score: int = 0
    max_score: int = 100
    tier: str = ""
    recommendation: str = ""
    confidence: str = ""

    def calculate_total(self):
        """Calculate overall site score from all categories"""
        self.demographics.calculate_total()
        self.supply_demand.calculate_total()
        self.site_attributes.calculate_total()
        self.competitive_positioning.calculate_total()
        self.economic_market.calculate_total()

        self.total_score = (
            self.demographics.total_score +
            self.supply_demand.total_score +
            self.site_attributes.total_score +
            self.competitive_positioning.total_score +
            self.economic_market.total_score
        )

        # Determine tier and recommendation
        if self.total_score >= 85:
            self.tier = "Excellent"
            self.recommendation = "PROCEED"
            self.confidence = "High Confidence"
        elif self.total_score >= 70:
            self.tier = "Good"
            self.recommendation = "PROCEED"
            self.confidence = "Standard Confidence"
        elif self.total_score >= 55:
            self.tier = "Fair"
            self.recommendation = "PROCEED WITH CAUTION"
            self.confidence = "Further Analysis Recommended"
        elif self.total_score >= 40:
            self.tier = "Weak"
            self.recommendation = "PROCEED WITH EXTREME CAUTION"
            self.confidence = "High Risk"
        else:
            self.tier = "Poor"
            self.recommendation = "DO NOT PROCEED"
            self.confidence = "Unacceptable Risk"

        return self.total_score

    def to_dict(self) -> Dict:
        """Convert score card to dictionary for JSON serialization"""
        return {
            "site_name": self.site_name,
            "site_address": self.site_address,
            "analysis_date": self.analysis_date,
            "total_score": self.total_score,
            "max_score": self.max_score,
            "tier": self.tier,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "demographics": {
                "total_score": self.demographics.total_score,
                "max_score": self.demographics.max_score,
                "population_3mi": self.demographics.population_3mi,
                "population_3mi_score": self.demographics.population_3mi_score,
                "population_3mi_tier": self.demographics.population_3mi_tier,
                "growth_rate": self.demographics.growth_rate,
                "growth_rate_score": self.demographics.growth_rate_score,
                "growth_rate_tier": self.demographics.growth_rate_tier,
                "median_income": self.demographics.median_income,
                "median_income_score": self.demographics.median_income_score,
                "median_income_tier": self.demographics.median_income_tier,
                "renter_occupied_pct": self.demographics.renter_occupied_pct,
                "renter_occupied_pct_score": self.demographics.renter_occupied_pct_score,
                "renter_occupied_pct_tier": self.demographics.renter_occupied_pct_tier,
                "median_age": self.demographics.median_age,
                "median_age_score": self.demographics.median_age_score,
                "median_age_tier": self.demographics.median_age_tier
            },
            "supply_demand": {
                "total_score": self.supply_demand.total_score,
                "max_score": self.supply_demand.max_score,
                "sf_per_capita": self.supply_demand.sf_per_capita,
                "sf_per_capita_score": self.supply_demand.sf_per_capita_score,
                "sf_per_capita_tier": self.supply_demand.sf_per_capita_tier,
                "existing_occupancy_avg": self.supply_demand.existing_occupancy_avg,
                "existing_occupancy_avg_score": self.supply_demand.existing_occupancy_avg_score,
                "existing_occupancy_avg_tier": self.supply_demand.existing_occupancy_avg_tier,
                "distance_to_nearest": self.supply_demand.distance_to_nearest,
                "distance_to_nearest_score": self.supply_demand.distance_to_nearest_score,
                "distance_to_nearest_tier": self.supply_demand.distance_to_nearest_tier,
                "market_rate_trend": self.supply_demand.market_rate_trend,
                "market_rate_trend_score": self.supply_demand.market_rate_trend_score,
                "market_rate_trend_tier": self.supply_demand.market_rate_trend_tier,
                "development_pipeline": self.supply_demand.development_pipeline,
                "development_pipeline_score": self.supply_demand.development_pipeline_score,
                "development_pipeline_tier": self.supply_demand.development_pipeline_tier
            },
            "site_attributes": {
                "total_score": self.site_attributes.total_score,
                "max_score": self.site_attributes.max_score,
                "visibility_rating": self.site_attributes.visibility_rating,
                "visibility_score": self.site_attributes.visibility_score,
                "visibility_tier": self.site_attributes.visibility_tier,
                "traffic_count": self.site_attributes.traffic_count,
                "traffic_count_score": self.site_attributes.traffic_count_score,
                "traffic_count_tier": self.site_attributes.traffic_count_tier,
                "access_quality": self.site_attributes.access_quality,
                "access_quality_score": self.site_attributes.access_quality_score,
                "access_quality_tier": self.site_attributes.access_quality_tier,
                "lot_size_ratio": self.site_attributes.lot_size_ratio,
                "lot_size_ratio_score": self.site_attributes.lot_size_ratio_score,
                "lot_size_ratio_tier": self.site_attributes.lot_size_ratio_tier,
                "zoning_status": self.site_attributes.zoning_status,
                "zoning_status_score": self.site_attributes.zoning_status_score,
                "zoning_status_tier": self.site_attributes.zoning_status_tier
            },
            "competitive_positioning": {
                "total_score": self.competitive_positioning.total_score,
                "max_score": self.competitive_positioning.max_score,
                "rate_competitiveness": self.competitive_positioning.rate_competitiveness,
                "rate_competitiveness_score": self.competitive_positioning.rate_competitiveness_score,
                "product_differentiation": self.competitive_positioning.product_differentiation,
                "product_differentiation_score": self.competitive_positioning.product_differentiation_score,
                "brand_strength": self.competitive_positioning.brand_strength,
                "brand_strength_score": self.competitive_positioning.brand_strength_score
            },
            "economic_market": {
                "total_score": self.economic_market.total_score,
                "max_score": self.economic_market.max_score,
                "unemployment_rate": self.economic_market.unemployment_rate,
                "unemployment_score": self.economic_market.unemployment_score,
                "job_growth": self.economic_market.job_growth,
                "job_growth_score": self.economic_market.job_growth_score,
                "gdp_growth": self.economic_market.gdp_growth,
                "gdp_growth_score": self.economic_market.gdp_growth_score
            }
        }


# ============================================================================
# SCORING CALCULATOR FUNCTIONS
# ============================================================================

def score_demographics(population_3mi: float, growth_rate: float, median_income: float,
                      renter_occupied_pct: float, median_age: float) -> DemographicScores:
    """
    Calculate demographic scores from raw data.

    Args:
        population_3mi: Population within 3-mile radius
        growth_rate: Annual population growth rate (%)
        median_income: Median household income ($)
        renter_occupied_pct: % of housing units renter-occupied
        median_age: Median age of population

    Returns:
        DemographicScores object with all scores calculated
    """
    scores = DemographicScores()

    # Store raw values
    scores.population_3mi = population_3mi
    scores.growth_rate = growth_rate
    scores.median_income = median_income
    scores.renter_occupied_pct = renter_occupied_pct
    scores.median_age = median_age

    # Calculate scores using benchmarks
    scores.population_3mi_score, scores.population_3mi_tier = \
        benchmarks.score_demographic_metric("population_3mi", population_3mi)

    scores.growth_rate_score, scores.growth_rate_tier = \
        benchmarks.score_demographic_metric("growth_rate", growth_rate)

    scores.median_income_score, scores.median_income_tier = \
        benchmarks.score_demographic_metric("median_income", median_income)

    scores.renter_occupied_pct_score, scores.renter_occupied_pct_tier = \
        benchmarks.score_demographic_metric("renter_occupied_pct", renter_occupied_pct)

    scores.median_age_score, scores.median_age_tier = \
        benchmarks.score_demographic_metric("age_demographics", median_age)

    scores.calculate_total()

    return scores


def score_supply_demand(sf_per_capita: float, existing_occupancy_avg: float,
                       distance_to_nearest: float, market_rate_trend: float,
                       development_pipeline: int) -> SupplyDemandScores:
    """
    Calculate supply/demand scores from raw data.

    Args:
        sf_per_capita: Square feet of storage per capita in market
        existing_occupancy_avg: Average occupancy of existing competitors (%)
        distance_to_nearest: Distance to nearest competitor (miles)
        market_rate_trend: % change in average market rates (past 12 months)
        development_pipeline: Count of facilities in planning/construction (5-mile radius)

    Returns:
        SupplyDemandScores object with all scores calculated
    """
    scores = SupplyDemandScores()

    # Store raw values
    scores.sf_per_capita = sf_per_capita
    scores.existing_occupancy_avg = existing_occupancy_avg
    scores.distance_to_nearest = distance_to_nearest
    scores.market_rate_trend = market_rate_trend
    scores.development_pipeline = development_pipeline

    # Calculate scores using benchmarks
    scores.sf_per_capita_score, scores.sf_per_capita_tier = \
        benchmarks.score_supply_demand_metric("sf_per_capita", sf_per_capita)

    scores.existing_occupancy_avg_score, scores.existing_occupancy_avg_tier = \
        benchmarks.score_supply_demand_metric("existing_occupancy_avg", existing_occupancy_avg)

    scores.distance_to_nearest_score, scores.distance_to_nearest_tier = \
        benchmarks.score_supply_demand_metric("distance_to_nearest", distance_to_nearest)

    scores.market_rate_trend_score, scores.market_rate_trend_tier = \
        benchmarks.score_supply_demand_metric("market_rate_trend", market_rate_trend)

    scores.development_pipeline_score, scores.development_pipeline_tier = \
        benchmarks.score_supply_demand_metric("development_pipeline", development_pipeline)

    scores.calculate_total()

    return scores


def score_site_attributes(visibility_rating: int, traffic_count: int, access_quality: int,
                         lot_size_ratio: float, zoning_status: int) -> SiteAttributeScores:
    """
    Calculate site attribute scores from raw data.

    Args:
        visibility_rating: 1-5 subjective visibility assessment
        traffic_count: Average Daily Traffic (ADT)
        access_quality: 1-5 subjective ingress/egress assessment
        lot_size_ratio: Lot size / building footprint ratio
        zoning_status: 1=Approved, 2=Conditional, 3=Variance, 4=Not allowed

    Returns:
        SiteAttributeScores object with all scores calculated
    """
    scores = SiteAttributeScores()

    # Store raw values
    scores.visibility_rating = visibility_rating
    scores.traffic_count = traffic_count
    scores.access_quality = access_quality
    scores.lot_size_ratio = lot_size_ratio
    scores.zoning_status = zoning_status

    # Calculate scores using benchmarks
    scores.visibility_score, scores.visibility_tier = \
        benchmarks.score_site_attribute("visibility", visibility_rating)

    scores.traffic_count_score, scores.traffic_count_tier = \
        benchmarks.score_site_attribute("traffic_count", traffic_count)

    scores.access_quality_score, scores.access_quality_tier = \
        benchmarks.score_site_attribute("access_quality", access_quality)

    scores.lot_size_ratio_score, scores.lot_size_ratio_tier = \
        benchmarks.score_site_attribute("lot_size_adequacy", lot_size_ratio)

    scores.zoning_status_score, scores.zoning_status_tier = \
        benchmarks.score_site_attribute("zoning_status", zoning_status)

    scores.calculate_total()

    return scores


def score_competitive_positioning(rate_competitiveness_pct: float,
                                  product_differentiation: int,
                                  brand_strength: int) -> CompetitivePositioningScores:
    """
    Calculate competitive positioning scores.

    Args:
        rate_competitiveness_pct: Proposed rate vs market avg (% difference, negative = below market)
        product_differentiation: 1-5 subjective assessment
        brand_strength: 1-5 subjective brand awareness assessment

    Returns:
        CompetitivePositioningScores object
    """
    scores = CompetitivePositioningScores()

    scores.rate_competitiveness = rate_competitiveness_pct
    scores.product_differentiation = product_differentiation
    scores.brand_strength = brand_strength

    # Rate competitiveness scoring (5 points max)
    # Being 5-10% below market = excellent, at market = good, above market = poor
    if rate_competitiveness_pct <= -10:
        scores.rate_competitiveness_score = 5  # Significantly below market
    elif rate_competitiveness_pct <= -5:
        scores.rate_competitiveness_score = 4
    elif rate_competitiveness_pct <= 0:
        scores.rate_competitiveness_score = 3
    elif rate_competitiveness_pct <= 5:
        scores.rate_competitiveness_score = 2
    else:
        scores.rate_competitiveness_score = 1  # Above market pricing

    # Product differentiation: 1-5 scale maps directly to score
    scores.product_differentiation_score = product_differentiation

    # Brand strength: 1-5 scale maps directly to score
    scores.brand_strength_score = brand_strength

    scores.calculate_total()

    return scores


def score_economic_market(unemployment_rate: float, job_growth: float,
                         gdp_growth: float) -> EconomicMarketScores:
    """
    Calculate economic market scores.

    Args:
        unemployment_rate: Local unemployment rate (%)
        job_growth: % job growth past 12 months
        gdp_growth: State/metro GDP growth (%)

    Returns:
        EconomicMarketScores object
    """
    scores = EconomicMarketScores()

    scores.unemployment_rate = unemployment_rate
    scores.job_growth = job_growth
    scores.gdp_growth = gdp_growth

    # Unemployment scoring (3 points max) - lower is better
    if unemployment_rate < 3.5:
        scores.unemployment_score = 3
    elif unemployment_rate < 5.0:
        scores.unemployment_score = 2
    elif unemployment_rate < 7.0:
        scores.unemployment_score = 1
    else:
        scores.unemployment_score = 0

    # Job growth scoring (4 points max)
    if job_growth >= 3.0:
        scores.job_growth_score = 4
    elif job_growth >= 2.0:
        scores.job_growth_score = 3
    elif job_growth >= 1.0:
        scores.job_growth_score = 2
    elif job_growth >= 0:
        scores.job_growth_score = 1
    else:
        scores.job_growth_score = 0

    # GDP growth scoring (3 points max)
    if gdp_growth >= 3.0:
        scores.gdp_growth_score = 3
    elif gdp_growth >= 2.0:
        scores.gdp_growth_score = 2
    elif gdp_growth >= 1.0:
        scores.gdp_growth_score = 1
    else:
        scores.gdp_growth_score = 0

    scores.calculate_total()

    return scores


def create_site_scorecard(site_name: str, site_address: str,
                         demographics_data: Dict, supply_demand_data: Dict,
                         site_attributes_data: Dict, competitive_data: Dict,
                         economic_data: Dict) -> SiteScoreCard:
    """
    Create a complete site scorecard from all input data.

    Args:
        site_name: Name of the site
        site_address: Full address of the site
        demographics_data: Dict with keys: population_3mi, growth_rate, median_income, renter_occupied_pct, median_age
        supply_demand_data: Dict with keys: sf_per_capita, existing_occupancy_avg, distance_to_nearest, market_rate_trend, development_pipeline
        site_attributes_data: Dict with keys: visibility_rating, traffic_count, access_quality, lot_size_ratio, zoning_status
        competitive_data: Dict with keys: rate_competitiveness_pct, product_differentiation, brand_strength
        economic_data: Dict with keys: unemployment_rate, job_growth, gdp_growth

    Returns:
        Complete SiteScoreCard with all scores calculated
    """
    scorecard = SiteScoreCard()
    scorecard.site_name = site_name
    scorecard.site_address = site_address

    # Calculate each category
    scorecard.demographics = score_demographics(**demographics_data)
    scorecard.supply_demand = score_supply_demand(**supply_demand_data)
    scorecard.site_attributes = score_site_attributes(**site_attributes_data)
    scorecard.competitive_positioning = score_competitive_positioning(**competitive_data)
    scorecard.economic_market = score_economic_market(**economic_data)

    # Calculate overall total
    scorecard.calculate_total()

    return scorecard


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=== 100-Point Scoring System Test ===\n")

    # Test with Poughkeepsie example data from the template
    demographics = {
        "population_3mi": 61297,
        "growth_rate": 0.37,
        "median_income": 77883,
        "renter_occupied_pct": 46.1,
        "median_age": 38.6
    }

    supply_demand = {
        "sf_per_capita": 5.8,
        "existing_occupancy_avg": 88.0,
        "distance_to_nearest": 1.2,
        "market_rate_trend": 2.1,
        "development_pipeline": 1
    }

    site_attributes = {
        "visibility_rating": 4,
        "traffic_count": 18500,
        "access_quality": 5,
        "lot_size_ratio": 3.8,
        "zoning_status": 1
    }

    competitive = {
        "rate_competitiveness_pct": -7.5,  # 7.5% below market
        "product_differentiation": 4,
        "brand_strength": 3
    }

    economic = {
        "unemployment_rate": 4.2,
        "job_growth": 2.3,
        "gdp_growth": 2.7
    }

    scorecard = create_site_scorecard(
        site_name="Poughkeepsie Storage Center",
        site_address="123 Main Street, Poughkeepsie, NY 12601",
        demographics_data=demographics,
        supply_demand_data=supply_demand,
        site_attributes_data=site_attributes,
        competitive_data=competitive,
        economic_data=economic
    )

    print(f"Site: {scorecard.site_name}")
    print(f"Address: {scorecard.site_address}")
    print(f"Analysis Date: {scorecard.analysis_date}\n")

    print(f"Demographics: {scorecard.demographics.total_score}/{scorecard.demographics.max_score}")
    print(f"  Population (3-Mile): {scorecard.demographics.population_3mi:,.0f} - {scorecard.demographics.population_3mi_score}/5 ({scorecard.demographics.population_3mi_tier})")
    print(f"  Growth Rate: {scorecard.demographics.growth_rate:.2f}% - {scorecard.demographics.growth_rate_score}/5 ({scorecard.demographics.growth_rate_tier})")
    print(f"  Median Income: ${scorecard.demographics.median_income:,.0f} - {scorecard.demographics.median_income_score}/5 ({scorecard.demographics.median_income_tier})")
    print(f"  Renter-Occupied: {scorecard.demographics.renter_occupied_pct:.1f}% - {scorecard.demographics.renter_occupied_pct_score}/5 ({scorecard.demographics.renter_occupied_pct_tier})")
    print(f"  Median Age: {scorecard.demographics.median_age:.1f} - {scorecard.demographics.median_age_score}/5 ({scorecard.demographics.median_age_tier})\n")

    print(f"Supply/Demand: {scorecard.supply_demand.total_score}/{scorecard.supply_demand.max_score}")
    print(f"  SF Per Capita: {scorecard.supply_demand.sf_per_capita:.1f} - {scorecard.supply_demand.sf_per_capita_score}/5 ({scorecard.supply_demand.sf_per_capita_tier})")
    print(f"  Avg Occupancy: {scorecard.supply_demand.existing_occupancy_avg:.0f}% - {scorecard.supply_demand.existing_occupancy_avg_score}/5 ({scorecard.supply_demand.existing_occupancy_avg_tier})")
    print(f"  Distance to Nearest: {scorecard.supply_demand.distance_to_nearest:.1f} mi - {scorecard.supply_demand.distance_to_nearest_score}/5 ({scorecard.supply_demand.distance_to_nearest_tier})")
    print(f"  Rate Trend: {scorecard.supply_demand.market_rate_trend:+.1f}% - {scorecard.supply_demand.market_rate_trend_score}/5 ({scorecard.supply_demand.market_rate_trend_tier})")
    print(f"  Dev Pipeline: {scorecard.supply_demand.development_pipeline} - {scorecard.supply_demand.development_pipeline_score}/5 ({scorecard.supply_demand.development_pipeline_tier})\n")

    print(f"Site Attributes: {scorecard.site_attributes.total_score}/{scorecard.site_attributes.max_score}")
    print(f"  Visibility: {scorecard.site_attributes.visibility_rating}/5 - {scorecard.site_attributes.visibility_score}/5 ({scorecard.site_attributes.visibility_tier})")
    print(f"  Traffic Count: {scorecard.site_attributes.traffic_count:,} ADT - {scorecard.site_attributes.traffic_count_score}/5 ({scorecard.site_attributes.traffic_count_tier})")
    print(f"  Access Quality: {scorecard.site_attributes.access_quality}/5 - {scorecard.site_attributes.access_quality_score}/5 ({scorecard.site_attributes.access_quality_tier})")
    print(f"  Lot Size Ratio: {scorecard.site_attributes.lot_size_ratio:.1f}:1 - {scorecard.site_attributes.lot_size_ratio_score}/5 ({scorecard.site_attributes.lot_size_ratio_tier})")
    print(f"  Zoning: {scorecard.site_attributes.zoning_status} - {scorecard.site_attributes.zoning_status_score}/5 ({scorecard.site_attributes.zoning_status_tier})\n")

    print(f"Competitive Positioning: {scorecard.competitive_positioning.total_score}/{scorecard.competitive_positioning.max_score}")
    print(f"  Rate Competitiveness: {scorecard.competitive_positioning.rate_competitiveness:+.1f}% - {scorecard.competitive_positioning.rate_competitiveness_score}/5")
    print(f"  Product Differentiation: {scorecard.competitive_positioning.product_differentiation}/5 - {scorecard.competitive_positioning.product_differentiation_score}/5")
    print(f"  Brand Strength: {scorecard.competitive_positioning.brand_strength}/5 - {scorecard.competitive_positioning.brand_strength_score}/5\n")

    print(f"Economic Market: {scorecard.economic_market.total_score}/{scorecard.economic_market.max_score}")
    print(f"  Unemployment: {scorecard.economic_market.unemployment_rate:.1f}% - {scorecard.economic_market.unemployment_score}/3")
    print(f"  Job Growth: {scorecard.economic_market.job_growth:.1f}% - {scorecard.economic_market.job_growth_score}/4")
    print(f"  GDP Growth: {scorecard.economic_market.gdp_growth:.1f}% - {scorecard.economic_market.gdp_growth_score}/3\n")

    print("="*50)
    print(f"TOTAL SCORE: {scorecard.total_score}/{scorecard.max_score}")
    print(f"TIER: {scorecard.tier}")
    print(f"RECOMMENDATION: {scorecard.recommendation}")
    print(f"CONFIDENCE: {scorecard.confidence}")
    print("="*50)
