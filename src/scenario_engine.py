"""
Scenario Modeling Engine for Self-Storage Feasibility

McKinley-level 3-case scenario analysis:
- Conservative (Downside)
- Base Case
- Aggressive (Upside)

Probability-weighted returns and risk-adjusted metrics.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from copy import deepcopy
from datetime import datetime

from financial_model_v2 import (
    EnhancedProForma,
    UnitMix,
    ReturnMetrics,
    build_enhanced_pro_forma,
)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ScenarioAssumptions:
    """Assumptions for a single scenario"""
    name: str  # "Conservative", "Base Case", "Aggressive"
    description: str

    # Rate adjustments (relative to base)
    rental_rate_adjustment: float = 0  # e.g., -0.10 = 10% lower rates
    rate_growth_adjustment: float = 0  # e.g., -0.01 = 1% lower annual growth

    # Occupancy adjustments
    stabilized_occupancy: float = 92.0  # Absolute %
    months_to_stabilization: int = 36

    # Cost adjustments
    construction_cost_adjustment: float = 0  # e.g., 0.10 = 10% higher costs
    expense_ratio_adjustment: float = 0  # e.g., 0.05 = 5% higher expenses

    # Financing
    interest_rate_adjustment: float = 0  # e.g., 0.005 = 50bps higher

    # Exit
    exit_cap_rate: float = 0.065  # Absolute

    # Probability weight
    probability_weight: float = 0.25  # 0-1 (e.g., 0.25 = 25%)


@dataclass
class ScenarioResult:
    """Results for a single scenario"""
    scenario: ScenarioAssumptions
    proforma: EnhancedProForma

    # Key metrics summary
    irr_7yr: float = 0
    irr_10yr: float = 0
    npv_7yr: float = 0
    equity_multiple_7yr: float = 0
    dscr_stabilized: float = 0
    development_yield: float = 0

    # Weighted contribution to expected value
    weighted_irr: float = 0
    weighted_npv: float = 0


@dataclass
class ScenarioAnalysis:
    """Complete 3-case scenario analysis"""
    project_name: str
    analysis_date: str

    # Individual scenarios
    conservative: ScenarioResult = None
    base_case: ScenarioResult = None
    aggressive: ScenarioResult = None

    # Probability-weighted expected values
    expected_irr: float = 0
    expected_npv: float = 0
    expected_equity_multiple: float = 0

    # Risk metrics
    irr_range: Tuple[float, float] = (0, 0)  # (min, max)
    npv_range: Tuple[float, float] = (0, 0)
    downside_risk_irr: float = 0  # IRR in conservative case
    upside_potential_irr: float = 0  # IRR in aggressive case

    # Investment decision
    meets_hurdle_all_scenarios: bool = False
    meets_hurdle_expected: bool = False
    hurdle_rate: float = 12.0  # Default 12%

    def get_all_results(self) -> List[ScenarioResult]:
        """Get all scenario results as list"""
        results = []
        if self.conservative:
            results.append(self.conservative)
        if self.base_case:
            results.append(self.base_case)
        if self.aggressive:
            results.append(self.aggressive)
        return results


# ============================================================================
# DEFAULT SCENARIOS
# ============================================================================

def get_conservative_scenario(base_proforma: EnhancedProForma) -> ScenarioAssumptions:
    """
    Get conservative (downside) scenario assumptions.

    Conservative assumptions:
    - 10% lower rental rates
    - 88% stabilized occupancy (vs 92%)
    - 42 month lease-up (vs 36)
    - 10% higher construction costs
    - 50bps higher interest rate
    - 75bps higher exit cap rate
    """
    return ScenarioAssumptions(
        name="Conservative",
        description="Downside scenario with market headwinds, slower lease-up, and cost pressures",
        rental_rate_adjustment=-0.10,
        rate_growth_adjustment=-0.01,
        stabilized_occupancy=88.0,
        months_to_stabilization=42,
        construction_cost_adjustment=0.10,
        expense_ratio_adjustment=0.05,
        interest_rate_adjustment=0.005,
        exit_cap_rate=base_proforma.exit_cap_rate + 0.0075,
        probability_weight=0.25,
    )


def get_base_case_scenario(base_proforma: EnhancedProForma) -> ScenarioAssumptions:
    """
    Get base case scenario assumptions.

    Base case uses current market assumptions.
    """
    return ScenarioAssumptions(
        name="Base Case",
        description="Expected scenario based on current market conditions and typical execution",
        rental_rate_adjustment=0,
        rate_growth_adjustment=0,
        stabilized_occupancy=base_proforma.stabilized_occupancy,
        months_to_stabilization=base_proforma.months_to_stabilization,
        construction_cost_adjustment=0,
        expense_ratio_adjustment=0,
        interest_rate_adjustment=0,
        exit_cap_rate=base_proforma.exit_cap_rate,
        probability_weight=0.50,
    )


def get_aggressive_scenario(base_proforma: EnhancedProForma) -> ScenarioAssumptions:
    """
    Get aggressive (upside) scenario assumptions.

    Aggressive assumptions:
    - 5% higher rental rates
    - 95% stabilized occupancy
    - 30 month lease-up
    - 5% lower construction costs (good bid)
    - 25bps lower exit cap rate
    """
    return ScenarioAssumptions(
        name="Aggressive",
        description="Upside scenario with strong market, fast lease-up, and favorable execution",
        rental_rate_adjustment=0.05,
        rate_growth_adjustment=0.005,
        stabilized_occupancy=95.0,
        months_to_stabilization=30,
        construction_cost_adjustment=-0.05,
        expense_ratio_adjustment=-0.02,
        interest_rate_adjustment=0,
        exit_cap_rate=base_proforma.exit_cap_rate - 0.0025,
        probability_weight=0.25,
    )


# ============================================================================
# SCENARIO ENGINE
# ============================================================================

def run_scenario(
    scenario: ScenarioAssumptions,
    base_params: Dict,
    unit_mix: UnitMix,
) -> ScenarioResult:
    """
    Run a single scenario.

    Args:
        scenario: Scenario assumptions
        base_params: Base case parameters
        unit_mix: Base unit mix

    Returns:
        ScenarioResult with pro forma and metrics
    """
    # Deep copy to avoid modifying originals
    modified_params = deepcopy(base_params)
    modified_mix = deepcopy(unit_mix)

    # Apply rental rate adjustment
    if scenario.rental_rate_adjustment != 0:
        rate_multiplier = 1 + scenario.rental_rate_adjustment
        for unit in modified_mix.units:
            unit.monthly_rate *= rate_multiplier
            unit.rate_psf = unit.monthly_rate / unit.sf_per_unit

    # Apply other adjustments
    modified_params["stabilized_occupancy"] = scenario.stabilized_occupancy
    modified_params["months_to_stabilization"] = scenario.months_to_stabilization
    modified_params["exit_cap_rate"] = scenario.exit_cap_rate

    # Construction cost adjustment
    if scenario.construction_cost_adjustment != 0:
        modified_params["construction_cost_psf"] *= (1 + scenario.construction_cost_adjustment)

    # Interest rate adjustment
    if scenario.interest_rate_adjustment != 0:
        modified_params["interest_rate"] += scenario.interest_rate_adjustment

    # Rate growth adjustment
    if scenario.rate_growth_adjustment != 0:
        modified_params["annual_rate_growth"] += scenario.rate_growth_adjustment

    # Expense adjustment
    if scenario.expense_ratio_adjustment != 0:
        modified_params["annual_expense_growth"] += scenario.expense_ratio_adjustment

    # Build pro forma
    proforma = build_enhanced_pro_forma(
        unit_mix=modified_mix,
        **modified_params
    )

    # Create result
    result = ScenarioResult(
        scenario=scenario,
        proforma=proforma,
        irr_7yr=proforma.metrics.irr_7yr,
        irr_10yr=proforma.metrics.irr_10yr,
        npv_7yr=proforma.metrics.npv_7yr,
        equity_multiple_7yr=proforma.metrics.equity_multiple_7yr,
        dscr_stabilized=proforma.metrics.dscr_stabilized,
        development_yield=proforma.metrics.development_yield * 100,
        weighted_irr=proforma.metrics.irr_7yr * scenario.probability_weight,
        weighted_npv=proforma.metrics.npv_7yr * scenario.probability_weight,
    )

    return result


def run_scenario_analysis(
    base_proforma: EnhancedProForma,
    conservative: Optional[ScenarioAssumptions] = None,
    base_case: Optional[ScenarioAssumptions] = None,
    aggressive: Optional[ScenarioAssumptions] = None,
    hurdle_rate: float = 12.0,
) -> ScenarioAnalysis:
    """
    Run complete 3-case scenario analysis.

    Args:
        base_proforma: Base case pro forma
        conservative: Optional custom conservative assumptions
        base_case: Optional custom base case assumptions
        aggressive: Optional custom aggressive assumptions
        hurdle_rate: IRR hurdle rate for go/no-go decision

    Returns:
        Complete ScenarioAnalysis
    """
    # Get default scenarios if not provided
    if conservative is None:
        conservative = get_conservative_scenario(base_proforma)
    if base_case is None:
        base_case = get_base_case_scenario(base_proforma)
    if aggressive is None:
        aggressive = get_aggressive_scenario(base_proforma)

    # Extract base parameters
    base_params = {
        "project_name": base_proforma.project_name,
        "address": base_proforma.address,
        "land_cost": base_proforma.development_budget.land_cost,
        "construction_cost_psf": base_proforma.development_budget.building_cost / base_proforma.nrsf,
        "ltc": base_proforma.financing.permanent_ltv,
        "interest_rate": base_proforma.financing.permanent_rate,
        "loan_term_years": base_proforma.financing.permanent_term_years,
        "amort_years": base_proforma.financing.permanent_amort_years,
        "months_to_stabilization": base_proforma.months_to_stabilization,
        "stabilized_occupancy": base_proforma.stabilized_occupancy,
        "annual_rate_growth": base_proforma.annual_rate_growth,
        "annual_expense_growth": base_proforma.annual_expense_growth,
        "exit_cap_rate": base_proforma.exit_cap_rate,
        "discount_rate": base_proforma.discount_rate,
    }

    # Run each scenario
    conservative_result = run_scenario(conservative, base_params, base_proforma.unit_mix)
    base_case_result = run_scenario(base_case, base_params, base_proforma.unit_mix)
    aggressive_result = run_scenario(aggressive, base_params, base_proforma.unit_mix)

    # Calculate expected values (probability-weighted)
    expected_irr = (
        conservative_result.weighted_irr +
        base_case_result.weighted_irr +
        aggressive_result.weighted_irr
    )

    expected_npv = (
        conservative_result.weighted_npv +
        base_case_result.weighted_npv +
        aggressive_result.weighted_npv
    )

    expected_em = (
        conservative_result.equity_multiple_7yr * conservative.probability_weight +
        base_case_result.equity_multiple_7yr * base_case.probability_weight +
        aggressive_result.equity_multiple_7yr * aggressive.probability_weight
    )

    # Risk metrics
    all_irrs = [conservative_result.irr_7yr, base_case_result.irr_7yr, aggressive_result.irr_7yr]
    all_npvs = [conservative_result.npv_7yr, base_case_result.npv_7yr, aggressive_result.npv_7yr]

    # Build analysis
    analysis = ScenarioAnalysis(
        project_name=base_proforma.project_name,
        analysis_date=datetime.now().strftime("%Y-%m-%d"),
        conservative=conservative_result,
        base_case=base_case_result,
        aggressive=aggressive_result,
        expected_irr=expected_irr,
        expected_npv=expected_npv,
        expected_equity_multiple=expected_em,
        irr_range=(min(all_irrs), max(all_irrs)),
        npv_range=(min(all_npvs), max(all_npvs)),
        downside_risk_irr=conservative_result.irr_7yr,
        upside_potential_irr=aggressive_result.irr_7yr,
        meets_hurdle_all_scenarios=all(irr >= hurdle_rate for irr in all_irrs),
        meets_hurdle_expected=expected_irr >= hurdle_rate,
        hurdle_rate=hurdle_rate,
    )

    return analysis


# ============================================================================
# REPORTING HELPERS
# ============================================================================

def format_scenario_comparison_table(analysis: ScenarioAnalysis) -> str:
    """
    Format scenario comparison as markdown table.

    Args:
        analysis: Complete scenario analysis

    Returns:
        Markdown formatted table
    """
    lines = [
        "| Metric | Conservative | Base Case | Aggressive | Expected |",
        "|--------|--------------|-----------|------------|----------|",
    ]

    c = analysis.conservative
    b = analysis.base_case
    a = analysis.aggressive

    # IRR
    lines.append(
        f"| IRR (7-Year) | {c.irr_7yr:.1f}% | {b.irr_7yr:.1f}% | "
        f"{a.irr_7yr:.1f}% | **{analysis.expected_irr:.1f}%** |"
    )

    # NPV
    lines.append(
        f"| NPV (7-Year) | ${c.npv_7yr:,.0f} | ${b.npv_7yr:,.0f} | "
        f"${a.npv_7yr:,.0f} | **${analysis.expected_npv:,.0f}** |"
    )

    # Equity Multiple
    lines.append(
        f"| Equity Multiple | {c.equity_multiple_7yr:.2f}x | {b.equity_multiple_7yr:.2f}x | "
        f"{a.equity_multiple_7yr:.2f}x | **{analysis.expected_equity_multiple:.2f}x** |"
    )

    # DSCR
    lines.append(
        f"| DSCR (Stabilized) | {c.dscr_stabilized:.2f}x | {b.dscr_stabilized:.2f}x | "
        f"{a.dscr_stabilized:.2f}x | - |"
    )

    # Dev Yield
    lines.append(
        f"| Development Yield | {c.development_yield:.1f}% | {b.development_yield:.1f}% | "
        f"{a.development_yield:.1f}% | - |"
    )

    # Probability
    lines.append(
        f"| Probability Weight | {c.scenario.probability_weight*100:.0f}% | "
        f"{b.scenario.probability_weight*100:.0f}% | {a.scenario.probability_weight*100:.0f}% | 100% |"
    )

    return "\n".join(lines)


def get_scenario_insights(analysis: ScenarioAnalysis) -> List[str]:
    """
    Generate insights from scenario analysis.

    Args:
        analysis: Complete scenario analysis

    Returns:
        List of insight strings
    """
    insights = []

    # Expected IRR vs hurdle
    if analysis.meets_hurdle_expected:
        insights.append(
            f"Expected IRR of **{analysis.expected_irr:.1f}%** exceeds the {analysis.hurdle_rate:.0f}% "
            f"hurdle rate, indicating an attractive risk-adjusted investment opportunity."
        )
    else:
        insights.append(
            f"Expected IRR of **{analysis.expected_irr:.1f}%** falls below the {analysis.hurdle_rate:.0f}% "
            f"hurdle rate. Consider renegotiating terms or passing on this opportunity."
        )

    # Downside protection
    if analysis.meets_hurdle_all_scenarios:
        insights.append(
            f"Strong downside protection: Even the conservative scenario delivers {analysis.downside_risk_irr:.1f}% IRR, "
            f"exceeding the hurdle rate in all cases."
        )
    elif analysis.downside_risk_irr > 8:
        insights.append(
            f"Moderate downside risk: Conservative scenario yields {analysis.downside_risk_irr:.1f}% IRR. "
            f"Returns remain positive but fall below institutional hurdle rates."
        )
    else:
        insights.append(
            f"Significant downside risk: Conservative scenario yields only {analysis.downside_risk_irr:.1f}% IRR. "
            f"Risk mitigation measures are essential."
        )

    # Upside potential
    spread = analysis.upside_potential_irr - analysis.expected_irr
    if spread > 5:
        insights.append(
            f"Substantial upside potential: Aggressive scenario offers {analysis.upside_potential_irr:.1f}% IRR, "
            f"providing {spread:.1f}% upside above expected returns."
        )

    # IRR range
    irr_range = analysis.irr_range[1] - analysis.irr_range[0]
    if irr_range > 10:
        insights.append(
            f"Wide return dispersion ({irr_range:.1f}% IRR range) indicates meaningful execution risk. "
            f"Focus on controllable factors: construction management and lease-up strategy."
        )
    elif irr_range < 5:
        insights.append(
            f"Narrow return dispersion ({irr_range:.1f}% IRR range) suggests stable, predictable outcomes."
        )

    return insights


def get_investment_recommendation(analysis: ScenarioAnalysis) -> Dict:
    """
    Generate investment recommendation based on scenario analysis.

    Args:
        analysis: Complete scenario analysis

    Returns:
        Dict with recommendation, confidence, and rationale
    """
    # Score the investment
    score = 0
    rationale = []

    # Expected IRR vs hurdle (40 points max)
    if analysis.expected_irr >= analysis.hurdle_rate + 5:
        score += 40
        rationale.append(f"Strong expected returns ({analysis.expected_irr:.1f}% vs {analysis.hurdle_rate:.0f}% hurdle)")
    elif analysis.expected_irr >= analysis.hurdle_rate:
        score += 25
        rationale.append(f"Adequate expected returns ({analysis.expected_irr:.1f}%)")
    elif analysis.expected_irr >= analysis.hurdle_rate - 2:
        score += 10
        rationale.append(f"Marginal expected returns ({analysis.expected_irr:.1f}%)")
    else:
        rationale.append(f"Below-hurdle expected returns ({analysis.expected_irr:.1f}%)")

    # Downside protection (30 points max)
    if analysis.meets_hurdle_all_scenarios:
        score += 30
        rationale.append("Downside scenario meets hurdle rate")
    elif analysis.downside_risk_irr >= 8:
        score += 20
        rationale.append(f"Acceptable downside ({analysis.downside_risk_irr:.1f}% IRR)")
    elif analysis.downside_risk_irr >= 5:
        score += 10
        rationale.append(f"Modest downside risk ({analysis.downside_risk_irr:.1f}% IRR)")
    else:
        rationale.append(f"Significant downside risk ({analysis.downside_risk_irr:.1f}% IRR)")

    # NPV (15 points max)
    if analysis.expected_npv > 500000:
        score += 15
        rationale.append(f"Strong NPV (${analysis.expected_npv:,.0f})")
    elif analysis.expected_npv > 0:
        score += 10
        rationale.append(f"Positive NPV (${analysis.expected_npv:,.0f})")
    else:
        rationale.append(f"Negative NPV (${analysis.expected_npv:,.0f})")

    # Equity multiple (15 points max)
    if analysis.expected_equity_multiple >= 2.5:
        score += 15
        rationale.append(f"Excellent equity multiple ({analysis.expected_equity_multiple:.2f}x)")
    elif analysis.expected_equity_multiple >= 2.0:
        score += 10
        rationale.append(f"Good equity multiple ({analysis.expected_equity_multiple:.2f}x)")
    elif analysis.expected_equity_multiple >= 1.5:
        score += 5
        rationale.append(f"Moderate equity multiple ({analysis.expected_equity_multiple:.2f}x)")

    # Determine recommendation
    if score >= 85:
        recommendation = "STRONG PROCEED"
        confidence = "High"
    elif score >= 70:
        recommendation = "PROCEED"
        confidence = "Moderate-High"
    elif score >= 55:
        recommendation = "PROCEED WITH CAUTION"
        confidence = "Moderate"
    elif score >= 40:
        recommendation = "CONDITIONAL PROCEED"
        confidence = "Low"
    else:
        recommendation = "PASS"
        confidence = "N/A"

    return {
        "recommendation": recommendation,
        "score": score,
        "confidence": confidence,
        "rationale": rationale,
        "expected_irr": analysis.expected_irr,
        "downside_irr": analysis.downside_risk_irr,
        "expected_npv": analysis.expected_npv,
        "equity_multiple": analysis.expected_equity_multiple,
    }


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    from financial_model_v2 import create_default_unit_mix, build_enhanced_pro_forma

    print("=== Scenario Analysis Test ===\n")

    # Create base pro forma
    unit_mix = create_default_unit_mix(
        target_nrsf=60000,
        avg_rate_psf=1.25,
        cc_percentage=40.0
    )

    base_proforma = build_enhanced_pro_forma(
        project_name="Test Facility",
        address="123 Main St, Nashville, TN",
        unit_mix=unit_mix,
        land_cost=800000,
        construction_cost_psf=85,
        ltc=0.70,
        interest_rate=0.065,
        months_to_stabilization=36,
        stabilized_occupancy=92.0,
    )

    print(f"Base Pro Forma IRR: {base_proforma.metrics.irr_7yr:.2f}%")
    print()

    # Run scenario analysis
    print("Running scenario analysis...")
    analysis = run_scenario_analysis(base_proforma, hurdle_rate=12.0)

    print("\n" + "="*60)
    print("SCENARIO COMPARISON")
    print("="*60)
    print()
    print(format_scenario_comparison_table(analysis))
    print()

    print("="*60)
    print("KEY INSIGHTS")
    print("="*60)
    for insight in get_scenario_insights(analysis):
        print(f"\n  {insight}")
    print()

    print("="*60)
    print("INVESTMENT RECOMMENDATION")
    print("="*60)
    rec = get_investment_recommendation(analysis)
    print(f"\n  Recommendation: {rec['recommendation']}")
    print(f"  Score: {rec['score']}/100")
    print(f"  Confidence: {rec['confidence']}")
    print(f"\n  Rationale:")
    for r in rec['rationale']:
        print(f"    - {r}")
