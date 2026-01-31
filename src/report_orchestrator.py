"""
Report Orchestrator - Master Controller for Feasibility Report Generation

This module orchestrates the complete end-to-end report generation process:
1. Collect input data (address, project details, site attributes)
2. Run all analytics modules (scoring, financials, market analysis)
3. Prepare data for LLM
4. Generate report sections via Claude API
5. Compile final report package

This is the main entry point that ties everything together.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path

# Import all analytics modules
try:
    from src import scoring_system
    from src import financial_model
    from src import market_analysis
    from src import competitor_analyzer
    from src import benchmarks
    from src import llm_report_generator
except ModuleNotFoundError:
    import scoring_system
    import financial_model
    import market_analysis
    import competitor_analyzer
    import benchmarks
    import llm_report_generator


@dataclass
class ProjectInputs:
    """All user inputs for a feasibility analysis"""
    # Basic project info
    project_name: str = ""
    site_address: str = ""

    # Project specifications
    proposed_nrsf: int = 60000
    proposed_unit_mix: Dict[str, int] = field(default_factory=dict)
    land_cost: float = 0

    # Site attributes (user-provided ratings)
    visibility_rating: int = 3  # 1-5 scale
    traffic_count: int = 10000  # Average Daily Traffic
    access_quality: int = 3  # 1-5 scale
    lot_size_acres: float = 0
    zoning_status: int = 2  # 1=Approved, 2=Conditional, 3=Variance, 4=Not allowed

    # Financial assumptions
    loan_to_cost: float = 0.75  # 75% LTC typical
    interest_rate: float = 0.065  # 6.5% typical
    exit_cap_rate: float = 0.07  # 7% exit cap

    # Market ID (if TractiQ data available)
    tractiq_market_id: Optional[str] = None


@dataclass
class AnalyticsResults:
    """Results from all analytics modules"""
    # Site coordinates
    latitude: float = 0
    longitude: float = 0
    geocoded_address: str = ""

    # Scoring results
    site_scorecard: Optional[scoring_system.SiteScoreCard] = None

    # Financial results
    pro_forma: Optional[financial_model.ProForma] = None

    # Market results
    market_supply_demand: Optional[market_analysis.SupplyDemandAnalysis] = None
    market_opportunity: Optional[Dict] = None

    # Competitor results
    competitor_analysis: Optional[competitor_analyzer.MarketAnalysisReport] = None

    # Scraper results
    scraper_competitors: List[Dict] = field(default_factory=list)


@dataclass
class FeasibilityReport:
    """Complete feasibility report package"""
    project_inputs: ProjectInputs
    analytics_results: AnalyticsResults
    report_sections: Dict[str, str] = field(default_factory=dict)
    generation_timestamp: str = ""


# ============================================================================
# ORCHESTRATION FUNCTIONS
# ============================================================================

def geocode_site(address: str) -> Tuple[float, float, str]:
    """
    Geocode site address to get coordinates.

    Args:
        address: Full site address

    Returns:
        Tuple of (latitude, longitude, formatted_address)
    """
    # Simplified geocoding for testing - would use intelligence.py in production
    # For Nashville TN address, use known coordinates
    if "Nashville" in address or "37211" in address:
        return (36.1147, -86.6734, address)
    else:
        # Default fallback
        return (36.0, -86.0, address)


def get_scraper_competitors(address: str, radius_miles: float = 5.0) -> List[Dict]:
    """
    Get competitors via real-time scraper.

    Args:
        address: Site address
        radius_miles: Search radius

    Returns:
        List of competitor dicts
    """
    try:
        # Import the appropriate scraper based on environment
        import os
        import socket

        # Detect cloud environment
        env_runtime = os.getenv('STREAMLIT_RUNTIME_ENV')
        hostname = os.getenv('HOSTNAME', 'NOT_SET')
        socket_hostname = socket.gethostname()
        users_exists = os.path.exists('/Users')

        is_cloud = (
            env_runtime == 'cloud' or
            'streamlit' in hostname.lower() or
            'streamlit' in socket_hostname.lower() or
            not users_exists
        )

        # Load appropriate scraper
        if is_cloud:
            from src.scraper_cloud import get_competitors_realtime_cloud
            competitors = get_competitors_realtime_cloud(address, radius_miles=radius_miles)
        else:
            from src.scraper import get_competitors_realtime
            competitors = get_competitors_realtime(address, radius_miles=radius_miles)

        return competitors if competitors else []
    except Exception as e:
        print(f"Scraper error: {e}")
        import traceback
        traceback.print_exc()
        return []


def load_tractiq_data(market_id: Optional[str]) -> Optional[Dict]:
    """
    Load TractiQ cached data if available.

    Args:
        market_id: TractiQ market ID

    Returns:
        Cached market data dict or None
    """
    if not market_id:
        return None

    try:
        cache_path = Path("src/data/tractiq_cache") / f"{market_id}.json"
        if cache_path.exists():
            with open(cache_path) as f:
                return json.load(f)
    except Exception as e:
        print(f"TractiQ data load error: {e}")

    return None


def get_census_demographics(lat: float, lon: float) -> Dict:
    """
    Get demographic data from Census API.

    Args:
        lat, lon: Site coordinates

    Returns:
        Dict with population, income, growth, etc.
    """
    # Placeholder - would call real Census API
    # For now return sample data
    return {
        "population_1mi": 25000,
        "population_3mi": 75000,
        "population_5mi": 150000,
        "households_3mi": 28000,
        "median_income": 72000,
        "renter_occupied_pct": 38.5,
        "growth_rate": 1.5,
        "job_growth": 2.0,
        "unemployment_rate": 4.5,
        "gdp_growth": 2.5,
        "median_age": 37.2
    }


def run_analytics(inputs: ProjectInputs) -> AnalyticsResults:
    """
    Run all analytics modules and compile results.

    Args:
        inputs: ProjectInputs with all user-provided data

    Returns:
        Complete AnalyticsResults
    """
    results = AnalyticsResults()

    print(f"\n{'='*70}")
    print(f"RUNNING FEASIBILITY ANALYSIS: {inputs.project_name}")
    print(f"{'='*70}\n")

    # Step 1: Geocode site address
    print("[1/7] Geocoding site address...")
    lat, lon, formatted_address = geocode_site(inputs.site_address)
    results.latitude = lat
    results.longitude = lon
    results.geocoded_address = formatted_address
    print(f"      ✓ Location: {lat:.4f}, {lon:.4f}")

    # Step 2: Get demographics
    print("[2/7] Fetching demographic data...")
    demographics = get_census_demographics(lat, lon)
    print(f"      ✓ Population (3-mile): {demographics['population_3mi']:,}")
    print(f"      ✓ Median Income: ${demographics['median_income']:,}")

    # Step 3: Load TractiQ data AND run scraper (merge both sources)
    print("[3/7] Loading market intelligence...")
    tractiq_data = load_tractiq_data(inputs.tractiq_market_id)
    if tractiq_data:
        print(f"      ✓ TractiQ data loaded: {tractiq_data.get('competitor_count', 0)} competitors")
    else:
        print("      ℹ No TractiQ data available")

    # Always run scraper to get additional competitors
    print("      🔍 Running web scraper for additional competitors...")
    scraper_results = get_scraper_competitors(inputs.site_address, radius_miles=5.0)
    print(f"      ✓ Scraper found: {len(scraper_results)} competitors")
    results.scraper_competitors = scraper_results

    # Step 4: Market supply/demand analysis
    print("[4/7] Analyzing market supply/demand...")
    results.market_supply_demand = market_analysis.perform_supply_demand_analysis(
        market_name=f"{inputs.project_name} Market",
        demographics=demographics,
        tractiq_data=tractiq_data,
        scraper_results=results.scraper_competitors,
        site_lat=lat,
        site_lon=lon
    )
    print(f"      ✓ SF Per Capita: {results.market_supply_demand.sf_per_capita_3mi:.2f}")
    print(f"      ✓ Market Balance: {results.market_supply_demand.balance_tier_3mi}")

    # Get opportunity assessment
    results.market_opportunity = market_analysis.assess_market_opportunity(
        results.market_supply_demand
    )
    print(f"      ✓ Opportunity Score: {results.market_opportunity['opportunity_score']}/100")

    # Step 5: Financial pro forma
    print("[5/7] Building financial pro forma...")

    # Calculate construction costs
    state = formatted_address.split(",")[-2].strip().split()[-1] if "," in formatted_address else "TN"
    construction = benchmarks.calculate_construction_cost(
        inputs.proposed_nrsf,
        state,
        "mid",
        "mixed"
    )

    # Development costs
    dev_costs = {
        "land_cost": inputs.land_cost,
        "hard_costs": construction["hard_cost"],
        "soft_costs": construction["soft_cost"],
        "contingency": 0,
        "financing_costs": 150000
    }

    total_cost = sum(dev_costs.values())
    loan_amount = total_cost * inputs.loan_to_cost

    # Financing terms
    financing = {
        "loan_amount": loan_amount,
        "interest_rate": inputs.interest_rate,
        "term_years": 10,
        "amortization_years": 25
    }

    # Revenue assumptions (would use market rate analysis in production)
    revenue = {
        "avg_rate_psf": 1.20,  # $1.20/SF/month
        "stabilized_occupancy": 95.0
    }

    # Expense assumptions
    expenses = benchmarks.get_expense_ratio(inputs.proposed_nrsf)

    # Occupancy curve
    occ_curve = benchmarks.get_occupancy_curve("standard")

    # Build pro forma
    results.pro_forma = financial_model.build_pro_forma(
        project_name=inputs.project_name,
        nrsf=inputs.proposed_nrsf,
        development_costs=dev_costs,
        financing_terms=financing,
        revenue_assumptions=revenue,
        expense_assumptions=expenses,
        occupancy_curve=occ_curve["occupancy_pct"],
        exit_cap_rate=inputs.exit_cap_rate,
        holding_period=10
    )

    print(f"      ✓ Total Development Cost: ${results.pro_forma.development_costs.total_cost:,.0f}")
    print(f"      ✓ Stabilized NOI: ${results.pro_forma.stabilized.net_operating_income:,.0f}")
    print(f"      ✓ Cap Rate: {results.pro_forma.metrics.cap_rate*100:.2f}%")
    print(f"      ✓ 10-Year IRR: {results.pro_forma.metrics.irr_10yr:.2f}%")

    # Step 6: Site scoring
    print("[6/7] Calculating 100-point site score...")

    # Demographics scoring
    demographics_data = {
        "population_3mi": demographics["population_3mi"],
        "growth_rate": demographics["growth_rate"],
        "median_income": demographics["median_income"],
        "renter_occupied_pct": demographics["renter_occupied_pct"],
        "median_age": demographics.get("median_age", 37.0)
    }

    # Supply/demand scoring
    supply_demand_data = {
        "sf_per_capita": results.market_supply_demand.sf_per_capita_3mi,
        "existing_occupancy_avg": 88.0,  # Would come from competitor data
        "distance_to_nearest": results.market_supply_demand.supply.facilities_within_1mi if results.market_supply_demand.supply.facilities_within_1mi > 0 else 2.5,
        "market_rate_trend": 1.5,  # Would come from historical rate data
        "development_pipeline": 1  # Would come from market research
    }

    # Site attributes scoring
    lot_size_sf = inputs.lot_size_acres * 43560
    building_footprint = inputs.proposed_nrsf * 0.65  # Assume 65% coverage
    lot_ratio = lot_size_sf / building_footprint if building_footprint > 0 else 3.5

    site_attributes_data = {
        "visibility_rating": inputs.visibility_rating,
        "traffic_count": inputs.traffic_count,
        "access_quality": inputs.access_quality,
        "lot_size_ratio": lot_ratio,
        "zoning_status": inputs.zoning_status
    }

    # Competitive positioning (would use market rate analysis)
    competitive_data = {
        "rate_competitiveness_pct": -5.0,  # 5% below market
        "product_differentiation": 4,  # 4/5
        "brand_strength": 3  # 3/5
    }

    # Economic market
    economic_data = {
        "unemployment_rate": demographics["unemployment_rate"],
        "job_growth": demographics["job_growth"],
        "gdp_growth": demographics["gdp_growth"]
    }

    # Create scorecard
    results.site_scorecard = scoring_system.create_site_scorecard(
        site_name=inputs.project_name,
        site_address=formatted_address,
        demographics_data=demographics_data,
        supply_demand_data=supply_demand_data,
        site_attributes_data=site_attributes_data,
        competitive_data=competitive_data,
        economic_data=economic_data
    )

    print(f"      ✓ Total Score: {results.site_scorecard.total_score}/100")
    print(f"      ✓ Tier: {results.site_scorecard.tier}")
    print(f"      ✓ Recommendation: {results.site_scorecard.recommendation}")

    # Step 7: Analytics summary
    print("[7/7] Analytics complete!\n")
    print(f"{'='*70}")
    print("ANALYTICS SUMMARY")
    print(f"{'='*70}")
    print(f"Site Score:        {results.site_scorecard.total_score}/100 ({results.site_scorecard.tier})")
    print(f"Market Balance:    {results.market_supply_demand.balance_tier_3mi.upper()}")
    print(f"SF Per Capita:     {results.market_supply_demand.sf_per_capita_3mi:.2f}")
    print(f"Cap Rate:          {results.pro_forma.metrics.cap_rate*100:.2f}%")
    print(f"IRR (10-yr):       {results.pro_forma.metrics.irr_10yr:.2f}%")
    print(f"DSCR:              {results.pro_forma.metrics.dscr:.2f}x")
    print(f"Break-even Occ:    {results.pro_forma.metrics.break_even_occupancy:.1f}%")
    print(f"Recommendation:    {results.site_scorecard.recommendation}")
    print(f"{'='*70}\n")

    return results


def generate_report(inputs: ProjectInputs, use_llm: bool = True) -> FeasibilityReport:
    """
    Generate complete feasibility report.

    Args:
        inputs: ProjectInputs with all user-provided data
        use_llm: If True, generate narrative sections via Claude API

    Returns:
        Complete FeasibilityReport
    """
    # Run analytics
    analytics = run_analytics(inputs)

    # Create report package
    report = FeasibilityReport(
        project_inputs=inputs,
        analytics_results=analytics,
        generation_timestamp=datetime.now().isoformat()
    )

    if use_llm:
        # Prepare data for LLM
        print("Preparing data for LLM report generation...")

        report_data = llm_report_generator.ReportData(
            project_name=inputs.project_name,
            site_address=analytics.geocoded_address,
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
            site_score=analytics.site_scorecard.to_dict(),
            financial_metrics={
                "total_development_cost": analytics.pro_forma.development_costs.total_cost,
                "land_cost": inputs.land_cost,
                "hard_costs": analytics.pro_forma.development_costs.hard_costs,
                "soft_costs": analytics.pro_forma.development_costs.soft_costs,
                "noi_stabilized": analytics.pro_forma.stabilized.net_operating_income,
                "cap_rate": analytics.pro_forma.metrics.cap_rate * 100,
                "dscr": analytics.pro_forma.metrics.dscr,
                "break_even_occupancy": analytics.pro_forma.metrics.break_even_occupancy,
                "irr_10yr": analytics.pro_forma.metrics.irr_10yr,
                "npv_10yr": analytics.pro_forma.metrics.npv_10yr,
                "cash_on_cash_yr1": analytics.pro_forma.metrics.cash_on_cash_return
            },
            market_analysis={
                "sf_per_capita": analytics.market_supply_demand.sf_per_capita_3mi,
                "balance_tier": analytics.market_supply_demand.balance_tier_3mi,
                "saturation_score": analytics.market_supply_demand.saturation_score,
                "opportunity_score": analytics.market_opportunity["opportunity_score"],
                "opportunity_tier": analytics.market_opportunity["opportunity_tier"],
                "supply_gap_sf": analytics.market_supply_demand.supply_gap_sf
            },
            demographics={
                "population_3mi": analytics.market_supply_demand.demand.population_3mi,
                "median_income": analytics.market_supply_demand.demand.median_income_3mi,
                "renter_occupied_pct": analytics.market_supply_demand.demand.renter_occupied_pct,
                "growth_rate": analytics.market_supply_demand.demand.population_growth_rate
            },
            proposed_nrsf=inputs.proposed_nrsf,
            proposed_unit_mix=inputs.proposed_unit_mix
        )

        # Generate report sections via Claude API
        report.report_sections = llm_report_generator.generate_complete_report(report_data)

    print(f"\n{'='*70}")
    print("REPORT GENERATION COMPLETE")
    print(f"{'='*70}\n")

    return report


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=== Report Orchestrator Test ===\n")

    # Create sample project inputs
    sample_inputs = ProjectInputs(
        project_name="Test Storage Facility",
        site_address="123 Main Street, Nashville, TN 37211",
        proposed_nrsf=60000,
        land_cost=800000,
        visibility_rating=4,
        traffic_count=18500,
        access_quality=5,
        lot_size_acres=5.2,
        zoning_status=1,
        tractiq_market_id="tn_372113104"
    )

    # Run analytics only (no LLM calls)
    print("Running analytics pipeline (no LLM)...\n")
    report = generate_report(sample_inputs, use_llm=False)

    print("\n✓ Analytics pipeline test complete!")
    print(f"\nFinal Recommendation: {report.analytics_results.site_scorecard.recommendation}")
    print(f"Site Score: {report.analytics_results.site_scorecard.total_score}/100")
    print(f"Cap Rate: {report.analytics_results.pro_forma.metrics.cap_rate*100:.2f}%")
