"""
Absorption Rate Analyzer for Self-Storage Feasibility

McKinley-level market absorption analysis:
- Annual demand estimation based on population and SF/capita gaps
- Years to absorb pipeline and proposed facility
- Absorption risk classification
- Phasing recommendations for high-risk markets
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class DemandEstimate:
    """Market demand estimation"""
    # Population base
    population_3mi: int = 0
    population_growth_rate: float = 0  # Annual %
    projected_population_5yr: int = 0

    # Household base (more relevant for storage)
    households_3mi: int = 0
    avg_household_size: float = 2.5

    # Demand drivers
    renter_percentage: float = 40.0
    storage_propensity: float = 0.10  # % of HH using storage

    # Calculated demand
    estimated_storage_users_3mi: int = 0
    avg_sf_per_user: float = 100  # Average SF rented per user
    estimated_demand_sf: int = 0

    # Annual new demand
    annual_new_demand_sf: int = 0


@dataclass
class SupplyAnalysis:
    """Market supply analysis"""
    # Current supply
    current_total_sf: int = 0
    current_facility_count: int = 0
    current_sf_per_capita: float = 0

    # Pipeline
    pipeline_sf: int = 0
    pipeline_facility_count: int = 0
    pipeline_completion_months: int = 24  # When pipeline comes online

    # Proposed
    proposed_sf: int = 0

    # Combined
    future_total_sf: int = 0
    future_sf_per_capita: float = 0


@dataclass
class AbsorptionMetrics:
    """Absorption calculations"""
    # Market capacity
    target_sf_per_capita: float = 6.5
    equilibrium_sf: int = 0  # SF at target SF/capita
    current_gap_sf: int = 0  # Positive = undersupplied

    # Absorption rates
    historical_absorption_sf_annual: int = 0
    projected_absorption_sf_annual: int = 0

    # Time to absorb
    years_to_absorb_gap: float = 0
    years_to_absorb_pipeline: float = 0
    years_to_absorb_proposed: float = 0
    total_years_to_market_balance: float = 0

    # Absorption capacity
    market_can_absorb_proposed: bool = True
    absorption_feasibility_pct: float = 100  # How much of proposed can be absorbed in 3 years


@dataclass
class AbsorptionRiskAssessment:
    """Absorption risk classification"""
    risk_level: str = "low"  # "low", "moderate", "high", "very_high"
    risk_score: int = 0  # 0-100
    risk_factors: List[str] = field(default_factory=list)
    mitigating_factors: List[str] = field(default_factory=list)

    # Phasing recommendation
    phasing_recommended: bool = False
    recommended_phases: int = 1
    phase_1_sf: int = 0
    phase_2_sf: int = 0
    months_between_phases: int = 18


@dataclass
class AbsorptionAnalysis:
    """Complete absorption analysis"""
    market_name: str = ""
    analysis_date: str = ""

    # Components
    demand: DemandEstimate = field(default_factory=DemandEstimate)
    supply: SupplyAnalysis = field(default_factory=SupplyAnalysis)
    absorption: AbsorptionMetrics = field(default_factory=AbsorptionMetrics)
    risk: AbsorptionRiskAssessment = field(default_factory=AbsorptionRiskAssessment)

    # Summary
    market_absorption_outlook: str = "neutral"  # "favorable", "neutral", "challenging"
    key_insights: List[str] = field(default_factory=list)


# ============================================================================
# DEMAND ESTIMATION
# ============================================================================

def estimate_demand(
    population_3mi: int,
    population_growth_rate: float,
    renter_percentage: float = 40.0,
    households_3mi: Optional[int] = None,
    storage_propensity: float = 0.10,
    avg_sf_per_user: float = 100,
) -> DemandEstimate:
    """
    Estimate storage demand for a market.

    Args:
        population_3mi: Population within 3 miles
        population_growth_rate: Annual population growth rate (%)
        renter_percentage: % of households that rent
        households_3mi: Households (if known, otherwise estimated)
        storage_propensity: % of households that use storage
        avg_sf_per_user: Average SF rented per user

    Returns:
        DemandEstimate with calculated demand
    """
    demand = DemandEstimate()
    demand.population_3mi = population_3mi
    demand.population_growth_rate = population_growth_rate
    demand.renter_percentage = renter_percentage
    demand.storage_propensity = storage_propensity
    demand.avg_sf_per_user = avg_sf_per_user

    # Estimate households if not provided
    if households_3mi:
        demand.households_3mi = households_3mi
    else:
        demand.households_3mi = int(population_3mi / demand.avg_household_size)

    # Project population 5 years out
    demand.projected_population_5yr = int(
        population_3mi * (1 + population_growth_rate / 100) ** 5
    )

    # Estimate storage users
    # Formula: Households * (Renter Factor) * Storage Propensity
    # Renters use storage 2x more than owners
    owner_pct = (100 - renter_percentage) / 100
    renter_pct = renter_percentage / 100

    owner_users = demand.households_3mi * owner_pct * (storage_propensity * 0.7)
    renter_users = demand.households_3mi * renter_pct * (storage_propensity * 1.5)

    demand.estimated_storage_users_3mi = int(owner_users + renter_users)
    demand.estimated_demand_sf = int(demand.estimated_storage_users_3mi * avg_sf_per_user)

    # Annual new demand from population growth
    new_households_annual = int(demand.households_3mi * (population_growth_rate / 100))
    new_storage_users_annual = int(new_households_annual * storage_propensity)
    demand.annual_new_demand_sf = int(new_storage_users_annual * avg_sf_per_user)

    return demand


# ============================================================================
# SUPPLY ANALYSIS
# ============================================================================

def analyze_supply(
    current_sf: int,
    current_facilities: int,
    pipeline_sf: int,
    proposed_sf: int,
    population_3mi: int,
    pipeline_completion_months: int = 24,
) -> SupplyAnalysis:
    """
    Analyze current and future supply.

    Args:
        current_sf: Current market supply in SF
        current_facilities: Current facility count
        pipeline_sf: Under construction/planned SF
        proposed_sf: Proposed facility SF
        population_3mi: Population for SF/capita calc
        pipeline_completion_months: Months until pipeline completes

    Returns:
        SupplyAnalysis
    """
    supply = SupplyAnalysis()
    supply.current_total_sf = current_sf
    supply.current_facility_count = current_facilities
    supply.pipeline_sf = pipeline_sf
    supply.proposed_sf = proposed_sf
    supply.pipeline_completion_months = pipeline_completion_months

    # SF per capita
    if population_3mi > 0:
        supply.current_sf_per_capita = current_sf / population_3mi

    # Future supply
    supply.future_total_sf = current_sf + pipeline_sf + proposed_sf

    if population_3mi > 0:
        supply.future_sf_per_capita = supply.future_total_sf / population_3mi

    return supply


# ============================================================================
# ABSORPTION CALCULATIONS
# ============================================================================

def calculate_absorption(
    demand: DemandEstimate,
    supply: SupplyAnalysis,
    target_sf_per_capita: float = 6.5,
    historical_absorption_sf: Optional[int] = None,
) -> AbsorptionMetrics:
    """
    Calculate absorption metrics.

    Args:
        demand: Demand estimates
        supply: Supply analysis
        target_sf_per_capita: Target/equilibrium SF per capita
        historical_absorption_sf: Known historical absorption if available

    Returns:
        AbsorptionMetrics
    """
    absorption = AbsorptionMetrics()
    absorption.target_sf_per_capita = target_sf_per_capita

    # Equilibrium SF
    absorption.equilibrium_sf = int(demand.population_3mi * target_sf_per_capita)

    # Current gap (positive = undersupplied)
    absorption.current_gap_sf = absorption.equilibrium_sf - supply.current_total_sf

    # Absorption rate
    if historical_absorption_sf:
        absorption.historical_absorption_sf_annual = historical_absorption_sf
    else:
        # Estimate: annual new demand + portion of gap filled
        gap_fill_rate = 0.15  # Assume 15% of gap filled annually
        gap_absorption = max(0, absorption.current_gap_sf * gap_fill_rate)
        absorption.historical_absorption_sf_annual = int(
            demand.annual_new_demand_sf + gap_absorption
        )

    # Projected absorption (may differ from historical)
    absorption.projected_absorption_sf_annual = absorption.historical_absorption_sf_annual

    # Years to absorb
    if absorption.projected_absorption_sf_annual > 0:
        # Gap
        if absorption.current_gap_sf > 0:
            absorption.years_to_absorb_gap = (
                absorption.current_gap_sf / absorption.projected_absorption_sf_annual
            )
        else:
            absorption.years_to_absorb_gap = 0

        # Pipeline
        absorption.years_to_absorb_pipeline = (
            supply.pipeline_sf / absorption.projected_absorption_sf_annual
        ) if supply.pipeline_sf > 0 else 0

        # Proposed
        absorption.years_to_absorb_proposed = (
            supply.proposed_sf / absorption.projected_absorption_sf_annual
        ) if supply.proposed_sf > 0 else 0

        # Total to market balance
        total_new_sf = max(0, -absorption.current_gap_sf) + supply.pipeline_sf + supply.proposed_sf
        absorption.total_years_to_market_balance = (
            total_new_sf / absorption.projected_absorption_sf_annual
        ) if total_new_sf > 0 else 0

    # Feasibility check
    three_year_absorption = absorption.projected_absorption_sf_annual * 3
    if supply.proposed_sf > 0 and three_year_absorption > 0:
        absorption.absorption_feasibility_pct = min(100, (three_year_absorption / supply.proposed_sf) * 100)
        absorption.market_can_absorb_proposed = absorption.absorption_feasibility_pct >= 80
    else:
        absorption.market_can_absorb_proposed = True
        absorption.absorption_feasibility_pct = 100

    return absorption


# ============================================================================
# RISK ASSESSMENT
# ============================================================================

def assess_absorption_risk(
    demand: DemandEstimate,
    supply: SupplyAnalysis,
    absorption: AbsorptionMetrics,
) -> AbsorptionRiskAssessment:
    """
    Assess absorption risk and recommend phasing if needed.

    Args:
        demand: Demand estimates
        supply: Supply analysis
        absorption: Absorption metrics

    Returns:
        AbsorptionRiskAssessment
    """
    risk = AbsorptionRiskAssessment()
    risk_score = 0

    # Risk factor: SF per capita too high
    if supply.future_sf_per_capita > 8.0:
        risk_score += 30
        risk.risk_factors.append(f"Future SF/capita of {supply.future_sf_per_capita:.1f} exceeds 8.0 threshold")
    elif supply.future_sf_per_capita > 7.0:
        risk_score += 15
        risk.risk_factors.append(f"Future SF/capita of {supply.future_sf_per_capita:.1f} approaching saturation")

    # Risk factor: Low population growth
    if demand.population_growth_rate < 0.5:
        risk_score += 20
        risk.risk_factors.append(f"Low population growth ({demand.population_growth_rate:.1f}%)")
    elif demand.population_growth_rate < 1.0:
        risk_score += 10
        risk.risk_factors.append(f"Modest population growth ({demand.population_growth_rate:.1f}%)")

    # Risk factor: Large pipeline
    if supply.pipeline_sf > absorption.projected_absorption_sf_annual * 2:
        risk_score += 25
        risk.risk_factors.append("Pipeline represents >2 years of absorption")
    elif supply.pipeline_sf > absorption.projected_absorption_sf_annual:
        risk_score += 15
        risk.risk_factors.append("Significant pipeline competition")

    # Risk factor: Long absorption time
    if absorption.years_to_absorb_proposed > 4:
        risk_score += 20
        risk.risk_factors.append(f"Extended absorption timeline ({absorption.years_to_absorb_proposed:.1f} years)")
    elif absorption.years_to_absorb_proposed > 3:
        risk_score += 10
        risk.risk_factors.append(f"Absorption timeline of {absorption.years_to_absorb_proposed:.1f} years")

    # Mitigating factors
    if absorption.current_gap_sf > supply.proposed_sf:
        risk_score -= 15
        risk.mitigating_factors.append("Market undersupply exceeds proposed facility")

    if demand.population_growth_rate > 2.0:
        risk_score -= 10
        risk.mitigating_factors.append("Strong population growth supporting demand")

    if demand.renter_percentage > 50:
        risk_score -= 5
        risk.mitigating_factors.append("High renter population (strong storage demand)")

    # Cap score
    risk.risk_score = max(0, min(100, risk_score))

    # Classify risk level
    if risk.risk_score >= 60:
        risk.risk_level = "very_high"
    elif risk.risk_score >= 40:
        risk.risk_level = "high"
    elif risk.risk_score >= 20:
        risk.risk_level = "moderate"
    else:
        risk.risk_level = "low"

    # Phasing recommendation
    if risk.risk_level in ("high", "very_high") and supply.proposed_sf > 40000:
        risk.phasing_recommended = True
        risk.recommended_phases = 2

        # Split 60/40
        risk.phase_1_sf = int(supply.proposed_sf * 0.60)
        risk.phase_2_sf = supply.proposed_sf - risk.phase_1_sf

        # Delay based on absorption
        if absorption.projected_absorption_sf_annual > 0:
            phase_1_absorption_months = int(
                (risk.phase_1_sf / absorption.projected_absorption_sf_annual) * 12
            )
            risk.months_between_phases = max(12, min(24, phase_1_absorption_months))
        else:
            risk.months_between_phases = 18
    elif risk.risk_level == "moderate" and supply.proposed_sf > 60000:
        risk.phasing_recommended = True
        risk.recommended_phases = 2
        risk.phase_1_sf = int(supply.proposed_sf * 0.65)
        risk.phase_2_sf = supply.proposed_sf - risk.phase_1_sf
        risk.months_between_phases = 12

    return risk


# ============================================================================
# MAIN ANALYSIS FUNCTION
# ============================================================================

def analyze_absorption(
    population_3mi: int,
    population_growth_rate: float,
    current_supply_sf: int,
    current_facilities: int,
    pipeline_sf: int,
    proposed_sf: int,
    renter_percentage: float = 40.0,
    households_3mi: Optional[int] = None,
    target_sf_per_capita: float = 6.5,
    market_name: str = "Market",
) -> AbsorptionAnalysis:
    """
    Run complete absorption analysis.

    Args:
        population_3mi: Population within 3 miles
        population_growth_rate: Annual growth rate (%)
        current_supply_sf: Current market SF
        current_facilities: Number of facilities
        pipeline_sf: Under construction/planned SF
        proposed_sf: Proposed facility SF
        renter_percentage: % renters
        households_3mi: Households if known
        target_sf_per_capita: Target equilibrium
        market_name: Market name for report

    Returns:
        Complete AbsorptionAnalysis
    """
    analysis = AbsorptionAnalysis()
    analysis.market_name = market_name
    analysis.analysis_date = datetime.now().strftime("%Y-%m-%d")

    # Run components
    analysis.demand = estimate_demand(
        population_3mi=population_3mi,
        population_growth_rate=population_growth_rate,
        renter_percentage=renter_percentage,
        households_3mi=households_3mi,
    )

    analysis.supply = analyze_supply(
        current_sf=current_supply_sf,
        current_facilities=current_facilities,
        pipeline_sf=pipeline_sf,
        proposed_sf=proposed_sf,
        population_3mi=population_3mi,
    )

    analysis.absorption = calculate_absorption(
        demand=analysis.demand,
        supply=analysis.supply,
        target_sf_per_capita=target_sf_per_capita,
    )

    analysis.risk = assess_absorption_risk(
        demand=analysis.demand,
        supply=analysis.supply,
        absorption=analysis.absorption,
    )

    # Overall outlook
    if analysis.risk.risk_level == "low":
        analysis.market_absorption_outlook = "favorable"
    elif analysis.risk.risk_level == "moderate":
        analysis.market_absorption_outlook = "neutral"
    else:
        analysis.market_absorption_outlook = "challenging"

    # Key insights
    if analysis.absorption.current_gap_sf > 0:
        analysis.key_insights.append(
            f"Market is undersupplied by {analysis.absorption.current_gap_sf:,} SF"
        )
    else:
        analysis.key_insights.append(
            f"Market is oversupplied by {abs(analysis.absorption.current_gap_sf):,} SF"
        )

    analysis.key_insights.append(
        f"Annual absorption capacity: ~{analysis.absorption.projected_absorption_sf_annual:,} SF"
    )

    analysis.key_insights.append(
        f"Proposed facility absorption timeline: {analysis.absorption.years_to_absorb_proposed:.1f} years"
    )

    if analysis.risk.phasing_recommended:
        analysis.key_insights.append(
            f"Phased development recommended: {analysis.risk.phase_1_sf:,} SF initially, "
            f"{analysis.risk.phase_2_sf:,} SF in {analysis.risk.months_between_phases} months"
        )

    return analysis


def format_absorption_report(analysis: AbsorptionAnalysis) -> str:
    """
    Format absorption analysis as markdown.

    Args:
        analysis: Complete absorption analysis

    Returns:
        Markdown formatted report
    """
    lines = [
        f"# Absorption Analysis: {analysis.market_name}",
        f"*Analysis Date: {analysis.analysis_date}*",
        "",
        f"## Market Outlook: {analysis.market_absorption_outlook.title()}",
        f"**Risk Level: {analysis.risk.risk_level.replace('_', ' ').title()}** (Score: {analysis.risk.risk_score}/100)",
        "",
        "---",
        "",
        "## Demand Metrics",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Population (3mi) | {analysis.demand.population_3mi:,} |",
        f"| Population Growth | {analysis.demand.population_growth_rate:.1f}%/year |",
        f"| Households (3mi) | {analysis.demand.households_3mi:,} |",
        f"| Estimated Storage Users | {analysis.demand.estimated_storage_users_3mi:,} |",
        f"| Estimated Demand (SF) | {analysis.demand.estimated_demand_sf:,} |",
        f"| Annual New Demand | {analysis.demand.annual_new_demand_sf:,} SF |",
        "",
        "---",
        "",
        "## Supply Metrics",
        "",
        f"| Metric | Current | With Pipeline | With Proposed |",
        f"|--------|---------|---------------|---------------|",
        f"| Total SF | {analysis.supply.current_total_sf:,} | {analysis.supply.current_total_sf + analysis.supply.pipeline_sf:,} | {analysis.supply.future_total_sf:,} |",
        f"| SF/Capita | {analysis.supply.current_sf_per_capita:.1f} | - | {analysis.supply.future_sf_per_capita:.1f} |",
        "",
        "---",
        "",
        "## Absorption Capacity",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Target SF/Capita | {analysis.absorption.target_sf_per_capita:.1f} |",
        f"| Current Gap | {analysis.absorption.current_gap_sf:,} SF |",
        f"| Annual Absorption | {analysis.absorption.projected_absorption_sf_annual:,} SF |",
        f"| Years to Absorb Proposed | {analysis.absorption.years_to_absorb_proposed:.1f} |",
        f"| Absorption Feasibility | {analysis.absorption.absorption_feasibility_pct:.0f}% |",
        "",
    ]

    if analysis.risk.risk_factors:
        lines.extend([
            "---",
            "",
            "## Risk Factors",
            "",
        ])
        for factor in analysis.risk.risk_factors:
            lines.append(f"- {factor}")
        lines.append("")

    if analysis.risk.mitigating_factors:
        lines.extend([
            "## Mitigating Factors",
            "",
        ])
        for factor in analysis.risk.mitigating_factors:
            lines.append(f"- {factor}")
        lines.append("")

    if analysis.risk.phasing_recommended:
        lines.extend([
            "---",
            "",
            "## Phasing Recommendation",
            "",
            f"**Recommended:** Build in {analysis.risk.recommended_phases} phases",
            "",
            f"- **Phase 1:** {analysis.risk.phase_1_sf:,} SF",
            f"- **Phase 2:** {analysis.risk.phase_2_sf:,} SF (after {analysis.risk.months_between_phases} months)",
            "",
        ])

    lines.extend([
        "---",
        "",
        "## Key Insights",
        "",
    ])
    for insight in analysis.key_insights:
        lines.append(f"- {insight}")

    return "\n".join(lines)


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=== Absorption Analyzer Test ===\n")

    analysis = analyze_absorption(
        population_3mi=87000,
        population_growth_rate=1.5,
        current_supply_sf=504600,
        current_facilities=15,
        pipeline_sf=45000,
        proposed_sf=60000,
        renter_percentage=46.0,
        market_name="Nashville, TN",
    )

    print(format_absorption_report(analysis))
