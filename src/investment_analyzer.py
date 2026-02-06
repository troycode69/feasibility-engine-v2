"""
Investment Sizing & Breakeven Analyzer for Self-Storage Feasibility

McKinley-level investment analysis:
- Breakeven occupancy and rate calculations
- Maximum supportable land cost for target IRR
- Optimal facility size based on market gap
- Debt sizing based on DSCR constraints
- Go/No-Go investment decision framework
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from copy import deepcopy

from financial_model_v2 import (
    EnhancedProForma,
    UnitMix,
    build_enhanced_pro_forma,
    create_default_unit_mix,
)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class BreakevenAnalysis:
    """Breakeven metrics"""
    # Occupancy breakeven
    breakeven_occupancy_debt_service: float = 0  # % to cover debt service
    breakeven_occupancy_cash_neutral: float = 0  # % to break even on cash flow

    # Rate breakeven
    breakeven_rate_psf: float = 0  # Min rate to cover debt service at stabilized occ
    current_rate_psf: float = 0
    rate_cushion_pct: float = 0  # How much rates can drop before breakeven

    # Time breakeven
    months_to_positive_cash_flow: int = 0
    months_to_cumulative_breakeven: int = 0  # When cumulative CF turns positive


@dataclass
class LandCostAnalysis:
    """Maximum supportable land cost analysis"""
    current_land_cost: float = 0
    max_land_cost_for_target_irr: float = 0
    land_cost_cushion: float = 0  # Max - Current
    land_cost_cushion_pct: float = 0

    # Sensitivity
    irr_at_current_land: float = 0
    irr_at_max_land: float = 0  # Should equal target IRR
    target_irr: float = 12.0


@dataclass
class FacilitySizingAnalysis:
    """Optimal facility sizing recommendations"""
    # Market-based sizing
    market_sf_gap: int = 0  # Undersupply in SF
    recommended_nrsf_market: int = 0  # Based on market gap

    # Financial-based sizing
    min_nrsf_viable: int = 0  # Minimum to achieve target returns
    optimal_nrsf_financial: int = 0  # Sweet spot for returns
    max_nrsf_absorbable: int = 0  # Max market can absorb in reasonable time

    # Final recommendation
    recommended_nrsf: int = 0
    recommended_units: int = 0
    sizing_rationale: str = ""


@dataclass
class DebtSizingAnalysis:
    """Debt capacity analysis"""
    # DSCR-based
    max_loan_dscr_constrained: float = 0  # Max loan at min DSCR
    min_dscr_requirement: float = 1.25

    # LTV-based
    max_loan_ltv_constrained: float = 0
    max_ltv: float = 0.70

    # LTC-based
    max_loan_ltc_constrained: float = 0
    max_ltc: float = 0.75

    # Recommended
    recommended_loan_amount: float = 0
    binding_constraint: str = ""  # "DSCR", "LTV", or "LTC"
    recommended_equity: float = 0
    equity_percentage: float = 0


@dataclass
class InvestmentAnalysis:
    """Complete investment analysis"""
    project_name: str = ""
    analysis_date: str = ""

    # Component analyses
    breakeven: BreakevenAnalysis = field(default_factory=BreakevenAnalysis)
    land_cost: LandCostAnalysis = field(default_factory=LandCostAnalysis)
    facility_sizing: FacilitySizingAnalysis = field(default_factory=FacilitySizingAnalysis)
    debt_sizing: DebtSizingAnalysis = field(default_factory=DebtSizingAnalysis)

    # Investment metrics
    total_equity_required: float = 0
    projected_irr: float = 0
    projected_equity_multiple: float = 0

    # Decision
    investment_grade: str = ""  # "A", "B", "C", "D", "F"
    recommendation: str = ""  # "STRONG BUY", "BUY", "HOLD", "PASS"
    key_risks: List[str] = field(default_factory=list)
    key_opportunities: List[str] = field(default_factory=list)


# ============================================================================
# BREAKEVEN CALCULATIONS
# ============================================================================

def calculate_breakeven_metrics(proforma: EnhancedProForma) -> BreakevenAnalysis:
    """
    Calculate breakeven occupancy and rate metrics.

    Args:
        proforma: Enhanced pro forma model

    Returns:
        BreakevenAnalysis with all breakeven calculations
    """
    analysis = BreakevenAnalysis()

    # Get stabilized year data (year 4)
    if len(proforma.annual_summaries) >= 4:
        stabilized = proforma.annual_summaries[3]
    elif proforma.annual_summaries:
        stabilized = proforma.annual_summaries[-1]
    else:
        return analysis

    gpr = stabilized.gross_potential_revenue
    opex = stabilized.total_operating_expenses
    debt_service = proforma.financing.annual_debt_service

    # Breakeven occupancy for debt service coverage
    # (OpEx + Debt Service) / GPR = Breakeven Occ
    if gpr > 0:
        analysis.breakeven_occupancy_debt_service = (
            (opex + debt_service) / gpr * 100
        )

        # Breakeven for cash neutral (including cap reserves ~1% of EGR)
        cap_reserves = gpr * 0.92 * 0.01  # Assuming 92% occ for reserve calc
        analysis.breakeven_occupancy_cash_neutral = (
            (opex + debt_service + cap_reserves) / gpr * 100
        )

    # Rate breakeven
    unit_mix = proforma.unit_mix
    if unit_mix.total_sf > 0:
        analysis.current_rate_psf = unit_mix.weighted_avg_rate_psf

        # At stabilized occupancy, what rate covers costs?
        stabilized_occ = proforma.stabilized_occupancy / 100
        required_egr = opex + debt_service
        required_gpr = required_egr / stabilized_occ  # Gross needed
        analysis.breakeven_rate_psf = required_gpr / 12 / unit_mix.total_sf

        # Rate cushion
        if analysis.current_rate_psf > 0:
            analysis.rate_cushion_pct = (
                (analysis.current_rate_psf - analysis.breakeven_rate_psf)
                / analysis.current_rate_psf * 100
            )

    # Time to positive cash flow
    for i, cf in enumerate(proforma.monthly_cash_flows):
        if cf.cash_flow_before_tax > 0 and analysis.months_to_positive_cash_flow == 0:
            analysis.months_to_positive_cash_flow = i + 1
        if cf.cumulative_cash_flow > 0 and analysis.months_to_cumulative_breakeven == 0:
            analysis.months_to_cumulative_breakeven = i + 1
            break

    return analysis


# ============================================================================
# LAND COST ANALYSIS
# ============================================================================

def calculate_max_land_cost(
    proforma: EnhancedProForma,
    target_irr: float = 12.0,
    tolerance: float = 0.5,
) -> LandCostAnalysis:
    """
    Calculate maximum supportable land cost to achieve target IRR.

    Uses binary search to find the land cost that yields target IRR.

    Args:
        proforma: Base pro forma
        target_irr: Target IRR percentage (e.g., 12.0 for 12%)
        tolerance: IRR tolerance for convergence

    Returns:
        LandCostAnalysis with max land cost calculations
    """
    analysis = LandCostAnalysis()
    analysis.current_land_cost = proforma.development_budget.land_cost
    analysis.irr_at_current_land = proforma.metrics.irr_7yr
    analysis.target_irr = target_irr

    # If current IRR is below target, max land cost is less than current
    # If current IRR is above target, max land cost is more than current

    # Binary search bounds
    if analysis.irr_at_current_land >= target_irr:
        # Can support higher land cost
        low = analysis.current_land_cost
        high = analysis.current_land_cost * 3  # Upper bound
    else:
        # Need lower land cost
        low = 0
        high = analysis.current_land_cost

    # Extract base parameters
    base_params = {
        "project_name": proforma.project_name,
        "address": proforma.address,
        "construction_cost_psf": proforma.development_budget.building_cost / proforma.nrsf,
        "ltc": proforma.financing.permanent_ltv,
        "interest_rate": proforma.financing.permanent_rate,
        "loan_term_years": proforma.financing.permanent_term_years,
        "amort_years": proforma.financing.permanent_amort_years,
        "months_to_stabilization": proforma.months_to_stabilization,
        "stabilized_occupancy": proforma.stabilized_occupancy,
        "annual_rate_growth": proforma.annual_rate_growth,
        "annual_expense_growth": proforma.annual_expense_growth,
        "exit_cap_rate": proforma.exit_cap_rate,
        "discount_rate": proforma.discount_rate,
    }

    # Binary search
    max_iterations = 20
    for _ in range(max_iterations):
        mid = (low + high) / 2

        try:
            test_proforma = build_enhanced_pro_forma(
                unit_mix=deepcopy(proforma.unit_mix),
                land_cost=mid,
                **base_params
            )
            test_irr = test_proforma.metrics.irr_7yr
        except:
            test_irr = 0

        if abs(test_irr - target_irr) < tolerance:
            analysis.max_land_cost_for_target_irr = mid
            analysis.irr_at_max_land = test_irr
            break
        elif test_irr > target_irr:
            low = mid  # Can afford more land
        else:
            high = mid  # Need less land
    else:
        # Didn't converge - use last mid value
        analysis.max_land_cost_for_target_irr = mid
        analysis.irr_at_max_land = test_irr

    # Calculate cushion
    analysis.land_cost_cushion = (
        analysis.max_land_cost_for_target_irr - analysis.current_land_cost
    )
    if analysis.current_land_cost > 0:
        analysis.land_cost_cushion_pct = (
            analysis.land_cost_cushion / analysis.current_land_cost * 100
        )

    return analysis


# ============================================================================
# FACILITY SIZING
# ============================================================================

def calculate_optimal_facility_size(
    market_sf_per_capita: float,
    target_sf_per_capita: float,
    population_3mi: int,
    current_supply_sf: int,
    avg_rate_psf: float,
    land_cost: float,
    target_irr: float = 12.0,
) -> FacilitySizingAnalysis:
    """
    Calculate optimal facility size based on market and financial factors.

    Args:
        market_sf_per_capita: Current market SF per capita
        target_sf_per_capita: Target/healthy SF per capita (typically 6-7)
        population_3mi: Population within 3 miles
        current_supply_sf: Current market supply in SF
        avg_rate_psf: Average market rate per SF
        land_cost: Land cost for the site
        target_irr: Target IRR for financial viability

    Returns:
        FacilitySizingAnalysis with sizing recommendations
    """
    analysis = FacilitySizingAnalysis()

    # Market-based sizing
    target_total_sf = population_3mi * target_sf_per_capita
    analysis.market_sf_gap = max(0, target_total_sf - current_supply_sf)

    # Recommended market-based size (capture 15-25% of gap)
    analysis.recommended_nrsf_market = int(analysis.market_sf_gap * 0.20)

    # Financial-based sizing - test different sizes
    sizes_to_test = [30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000]

    viable_sizes = []
    best_irr = 0
    best_size = 0

    for size in sizes_to_test:
        try:
            unit_mix = create_default_unit_mix(
                target_nrsf=size,
                avg_rate_psf=avg_rate_psf,
                cc_percentage=40.0
            )

            proforma = build_enhanced_pro_forma(
                project_name="Size Test",
                address="Test",
                unit_mix=unit_mix,
                land_cost=land_cost,
                construction_cost_psf=85,
                ltc=0.70,
                interest_rate=0.065,
                months_to_stabilization=36,
                stabilized_occupancy=92.0,
            )

            irr = proforma.metrics.irr_7yr

            if irr >= target_irr:
                viable_sizes.append((size, irr))

            if irr > best_irr:
                best_irr = irr
                best_size = size

        except Exception as e:
            continue

    # Set financial-based sizing
    if viable_sizes:
        analysis.min_nrsf_viable = min(s[0] for s in viable_sizes)
        analysis.optimal_nrsf_financial = best_size
    else:
        analysis.min_nrsf_viable = 0
        analysis.optimal_nrsf_financial = 0

    # Max absorbable (assume 36-month absorption, ~2,000 SF/month typical)
    analysis.max_nrsf_absorbable = 36 * 2000  # 72,000 SF

    # Final recommendation
    candidates = [
        analysis.recommended_nrsf_market,
        analysis.optimal_nrsf_financial,
        analysis.max_nrsf_absorbable
    ]
    candidates = [c for c in candidates if c > 0]

    if candidates:
        # Take the minimum of viable options (conservative)
        analysis.recommended_nrsf = min(
            max(candidates),  # Don't go below market opportunity
            analysis.max_nrsf_absorbable  # But cap at absorbable
        )

        # Round to nearest 5,000
        analysis.recommended_nrsf = round(analysis.recommended_nrsf / 5000) * 5000

        # Estimate units (assuming ~115 SF average unit)
        analysis.recommended_units = int(analysis.recommended_nrsf / 115)

        # Rationale
        if analysis.market_sf_gap > 0:
            analysis.sizing_rationale = (
                f"Market gap of {analysis.market_sf_gap:,} SF supports development. "
                f"Recommended {analysis.recommended_nrsf:,} SF to capture ~20% of gap "
                f"while maintaining absorption within 36 months."
            )
        else:
            analysis.sizing_rationale = (
                f"Market appears saturated (no SF gap). Recommend smaller facility "
                f"of {analysis.recommended_nrsf:,} SF focused on premium positioning."
            )
    else:
        analysis.recommended_nrsf = 50000  # Default
        analysis.recommended_units = 435
        analysis.sizing_rationale = "Insufficient data for optimization. Using standard 50,000 SF facility."

    return analysis


# ============================================================================
# DEBT SIZING
# ============================================================================

def calculate_debt_capacity(proforma: EnhancedProForma) -> DebtSizingAnalysis:
    """
    Calculate debt capacity based on DSCR, LTV, and LTC constraints.

    Args:
        proforma: Enhanced pro forma

    Returns:
        DebtSizingAnalysis with debt capacity calculations
    """
    analysis = DebtSizingAnalysis()

    # Get stabilized NOI
    if len(proforma.annual_summaries) >= 4:
        stabilized_noi = proforma.annual_summaries[3].net_operating_income
    elif proforma.annual_summaries:
        stabilized_noi = proforma.annual_summaries[-1].net_operating_income
    else:
        return analysis

    total_cost = proforma.development_budget.total_development_cost

    # DSCR-based max loan
    # Max Debt Service = NOI / Min DSCR
    # Then solve for loan amount given rate and amort
    max_annual_ds = stabilized_noi / analysis.min_dscr_requirement

    # Approximate loan amount from debt service
    # DS = Loan * (r(1+r)^n) / ((1+r)^n - 1) where r = monthly rate, n = months
    monthly_rate = proforma.financing.permanent_rate / 12
    n_months = proforma.financing.permanent_amort_years * 12

    if monthly_rate > 0:
        payment_factor = (monthly_rate * (1 + monthly_rate) ** n_months) / ((1 + monthly_rate) ** n_months - 1)
        max_monthly_ds = max_annual_ds / 12
        analysis.max_loan_dscr_constrained = max_monthly_ds / payment_factor

    # LTV-based max loan (using stabilized value = NOI / cap rate)
    stabilized_value = stabilized_noi / proforma.exit_cap_rate
    analysis.max_loan_ltv_constrained = stabilized_value * analysis.max_ltv

    # LTC-based max loan
    analysis.max_loan_ltc_constrained = total_cost * analysis.max_ltc

    # Recommended = minimum of all constraints
    constraints = {
        "DSCR": analysis.max_loan_dscr_constrained,
        "LTV": analysis.max_loan_ltv_constrained,
        "LTC": analysis.max_loan_ltc_constrained,
    }

    # Filter out zero/negative values
    valid_constraints = {k: v for k, v in constraints.items() if v > 0}

    if valid_constraints:
        analysis.binding_constraint = min(valid_constraints, key=valid_constraints.get)
        analysis.recommended_loan_amount = min(valid_constraints.values())
    else:
        analysis.recommended_loan_amount = total_cost * 0.65  # Conservative default
        analysis.binding_constraint = "Default"

    # Equity required
    analysis.recommended_equity = total_cost - analysis.recommended_loan_amount
    analysis.equity_percentage = analysis.recommended_equity / total_cost * 100 if total_cost > 0 else 0

    return analysis


# ============================================================================
# COMPLETE INVESTMENT ANALYSIS
# ============================================================================

def run_investment_analysis(
    proforma: EnhancedProForma,
    market_data: Optional[Dict] = None,
    target_irr: float = 12.0,
) -> InvestmentAnalysis:
    """
    Run complete investment analysis.

    Args:
        proforma: Enhanced pro forma
        market_data: Optional market data (sf_per_capita, population, etc.)
        target_irr: Target IRR for viability assessment

    Returns:
        Complete InvestmentAnalysis
    """
    from datetime import datetime

    analysis = InvestmentAnalysis()
    analysis.project_name = proforma.project_name
    analysis.analysis_date = datetime.now().strftime("%Y-%m-%d")

    # Run component analyses
    analysis.breakeven = calculate_breakeven_metrics(proforma)
    analysis.land_cost = calculate_max_land_cost(proforma, target_irr)
    analysis.debt_sizing = calculate_debt_capacity(proforma)

    # Facility sizing (if market data provided)
    if market_data:
        analysis.facility_sizing = calculate_optimal_facility_size(
            market_sf_per_capita=market_data.get("sf_per_capita_3mi", 6.0),
            target_sf_per_capita=market_data.get("target_sf_per_capita", 6.5),
            population_3mi=market_data.get("population_3mi", 75000),
            current_supply_sf=market_data.get("total_sf_3mi", 450000),
            avg_rate_psf=proforma.unit_mix.weighted_avg_rate_psf,
            land_cost=proforma.development_budget.land_cost,
            target_irr=target_irr,
        )

    # Investment metrics
    analysis.total_equity_required = analysis.debt_sizing.recommended_equity
    analysis.projected_irr = proforma.metrics.irr_7yr
    analysis.projected_equity_multiple = proforma.metrics.equity_multiple_7yr

    # Grade the investment
    score = 0

    # IRR vs target (40 points)
    if proforma.metrics.irr_7yr >= target_irr + 5:
        score += 40
    elif proforma.metrics.irr_7yr >= target_irr + 2:
        score += 30
    elif proforma.metrics.irr_7yr >= target_irr:
        score += 20
    elif proforma.metrics.irr_7yr >= target_irr - 2:
        score += 10

    # DSCR (20 points)
    if proforma.metrics.dscr_stabilized >= 1.50:
        score += 20
    elif proforma.metrics.dscr_stabilized >= 1.35:
        score += 15
    elif proforma.metrics.dscr_stabilized >= 1.25:
        score += 10
    elif proforma.metrics.dscr_stabilized >= 1.15:
        score += 5

    # Breakeven cushion (20 points)
    occ_cushion = proforma.stabilized_occupancy - analysis.breakeven.breakeven_occupancy_debt_service
    if occ_cushion >= 20:
        score += 20
    elif occ_cushion >= 15:
        score += 15
    elif occ_cushion >= 10:
        score += 10
    elif occ_cushion >= 5:
        score += 5

    # Land cost cushion (20 points)
    if analysis.land_cost.land_cost_cushion_pct >= 50:
        score += 20
    elif analysis.land_cost.land_cost_cushion_pct >= 25:
        score += 15
    elif analysis.land_cost.land_cost_cushion_pct >= 10:
        score += 10
    elif analysis.land_cost.land_cost_cushion_pct >= 0:
        score += 5

    # Assign grade
    if score >= 85:
        analysis.investment_grade = "A"
        analysis.recommendation = "STRONG BUY"
    elif score >= 70:
        analysis.investment_grade = "B"
        analysis.recommendation = "BUY"
    elif score >= 55:
        analysis.investment_grade = "C"
        analysis.recommendation = "HOLD"
    elif score >= 40:
        analysis.investment_grade = "D"
        analysis.recommendation = "CONDITIONAL"
    else:
        analysis.investment_grade = "F"
        analysis.recommendation = "PASS"

    # Identify risks
    if analysis.breakeven.breakeven_occupancy_debt_service > 75:
        analysis.key_risks.append("High breakeven occupancy (>75%)")
    if analysis.land_cost.land_cost_cushion_pct < 10:
        analysis.key_risks.append("Limited land cost cushion")
    if proforma.metrics.dscr_stabilized < 1.25:
        analysis.key_risks.append("DSCR below lender minimum")
    if proforma.months_to_stabilization > 42:
        analysis.key_risks.append("Extended lease-up timeline")

    # Identify opportunities
    if analysis.land_cost.land_cost_cushion_pct > 30:
        analysis.key_opportunities.append("Significant land cost flexibility")
    if proforma.metrics.irr_7yr > target_irr + 5:
        analysis.key_opportunities.append("Returns well above hurdle")
    if analysis.breakeven.rate_cushion_pct > 20:
        analysis.key_opportunities.append("Strong rate cushion for market softness")

    return analysis


def format_investment_analysis_report(analysis: InvestmentAnalysis) -> str:
    """
    Format investment analysis as markdown report.

    Args:
        analysis: Complete investment analysis

    Returns:
        Markdown formatted report
    """
    lines = [
        f"# Investment Analysis: {analysis.project_name}",
        f"*Analysis Date: {analysis.analysis_date}*",
        "",
        f"## Investment Grade: {analysis.investment_grade}",
        f"**Recommendation: {analysis.recommendation}**",
        "",
        "---",
        "",
        "## Breakeven Analysis",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Breakeven Occupancy (Debt Service) | {analysis.breakeven.breakeven_occupancy_debt_service:.1f}% |",
        f"| Breakeven Occupancy (Cash Neutral) | {analysis.breakeven.breakeven_occupancy_cash_neutral:.1f}% |",
        f"| Breakeven Rate ($/SF) | ${analysis.breakeven.breakeven_rate_psf:.2f} |",
        f"| Current Rate ($/SF) | ${analysis.breakeven.current_rate_psf:.2f} |",
        f"| Rate Cushion | {analysis.breakeven.rate_cushion_pct:.1f}% |",
        f"| Months to Positive Cash Flow | {analysis.breakeven.months_to_positive_cash_flow} |",
        "",
        "---",
        "",
        "## Land Cost Analysis",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Current Land Cost | ${analysis.land_cost.current_land_cost:,.0f} |",
        f"| Max Land for {analysis.land_cost.target_irr:.0f}% IRR | ${analysis.land_cost.max_land_cost_for_target_irr:,.0f} |",
        f"| Land Cost Cushion | ${analysis.land_cost.land_cost_cushion:,.0f} ({analysis.land_cost.land_cost_cushion_pct:.1f}%) |",
        f"| IRR at Current Land | {analysis.land_cost.irr_at_current_land:.1f}% |",
        "",
        "---",
        "",
        "## Debt Sizing",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Max Loan (DSCR Constrained) | ${analysis.debt_sizing.max_loan_dscr_constrained:,.0f} |",
        f"| Max Loan (LTV Constrained) | ${analysis.debt_sizing.max_loan_ltv_constrained:,.0f} |",
        f"| Max Loan (LTC Constrained) | ${analysis.debt_sizing.max_loan_ltc_constrained:,.0f} |",
        f"| **Recommended Loan** | **${analysis.debt_sizing.recommended_loan_amount:,.0f}** |",
        f"| Binding Constraint | {analysis.debt_sizing.binding_constraint} |",
        f"| Required Equity | ${analysis.debt_sizing.recommended_equity:,.0f} ({analysis.debt_sizing.equity_percentage:.1f}%) |",
        "",
    ]

    if analysis.key_risks:
        lines.extend([
            "---",
            "",
            "## Key Risks",
            "",
        ])
        for risk in analysis.key_risks:
            lines.append(f"- {risk}")
        lines.append("")

    if analysis.key_opportunities:
        lines.extend([
            "---",
            "",
            "## Key Opportunities",
            "",
        ])
        for opp in analysis.key_opportunities:
            lines.append(f"- {opp}")

    return "\n".join(lines)


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    from financial_model_v2 import create_default_unit_mix, build_enhanced_pro_forma

    print("=== Investment Analyzer Test ===\n")

    # Create base pro forma
    unit_mix = create_default_unit_mix(
        target_nrsf=60000,
        avg_rate_psf=1.25,
        cc_percentage=40.0
    )

    proforma = build_enhanced_pro_forma(
        project_name="Nashville Self Storage",
        address="1202 Antioch Pike, Nashville, TN",
        unit_mix=unit_mix,
        land_cost=800000,
        construction_cost_psf=85,
        ltc=0.70,
        interest_rate=0.065,
        months_to_stabilization=36,
        stabilized_occupancy=92.0,
    )

    print(f"Project: {proforma.project_name}")
    print(f"Base IRR: {proforma.metrics.irr_7yr:.2f}%")
    print()

    # Run investment analysis
    market_data = {
        "sf_per_capita_3mi": 5.8,
        "target_sf_per_capita": 6.5,
        "population_3mi": 87000,
        "total_sf_3mi": 504600,
    }

    analysis = run_investment_analysis(proforma, market_data, target_irr=12.0)

    print(format_investment_analysis_report(analysis))
