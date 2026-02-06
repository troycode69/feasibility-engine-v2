"""
Sensitivity Analysis Engine for Self-Storage Feasibility

Institutional-grade sensitivity analysis:
- Tornado diagram analysis on key variables
- Impact quantification on IRR, NPV, DSCR
- Variable ranking by sensitivity magnitude
- Support for custom variable ranges

Outputs structured data for visualization (tornado charts).
"""

from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass, field
from copy import deepcopy

from financial_model_v2 import (
    EnhancedProForma,
    UnitMix,
    build_enhanced_pro_forma,
    calculate_irr,
    calculate_npv,
)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SensitivityVariable:
    """Configuration for a sensitivity variable"""
    name: str
    display_name: str
    base_value: float
    unit: str  # "%", "$", "months", "bps"
    test_deltas: List[float] = field(default_factory=lambda: [-0.20, -0.10, 0, 0.10, 0.20])
    # test_deltas are relative changes: -0.20 = -20%, 0.10 = +10%
    is_percentage: bool = False  # If True, add delta directly instead of multiplying


@dataclass
class SensitivityResult:
    """Result for a single variable's sensitivity test"""
    variable_name: str
    display_name: str
    base_value: float
    unit: str

    # Test results
    test_values: List[float] = field(default_factory=list)  # Actual values tested
    test_labels: List[str] = field(default_factory=list)  # e.g., "-20%", "-10%", "Base", "+10%", "+20%"

    # Metric impacts
    irr_results: List[float] = field(default_factory=list)  # IRR at each test value
    npv_results: List[float] = field(default_factory=list)  # NPV at each test value
    dscr_results: List[float] = field(default_factory=list)  # DSCR at each test value

    # Summary
    irr_base: float = 0
    irr_min: float = 0
    irr_max: float = 0
    irr_range: float = 0  # max - min

    npv_base: float = 0
    npv_min: float = 0
    npv_max: float = 0
    npv_range: float = 0

    sensitivity_rank: int = 0  # 1 = most sensitive


@dataclass
class TornadoAnalysis:
    """Complete tornado diagram analysis"""
    project_name: str
    analysis_date: str

    # Base case metrics
    base_irr: float
    base_npv: float
    base_dscr: float

    # Results by variable (sorted by sensitivity)
    results: List[SensitivityResult] = field(default_factory=list)

    # Summary
    most_sensitive_variable: str = ""
    irr_range_total: Tuple[float, float] = (0, 0)  # (min, max) across all scenarios
    npv_range_total: Tuple[float, float] = (0, 0)

    def get_tornado_data(self, metric: str = "irr") -> List[Dict]:
        """
        Get data formatted for tornado chart visualization.

        Args:
            metric: "irr" or "npv"

        Returns:
            List of dicts with variable, low, high, base values
        """
        data = []
        base = self.base_irr if metric == "irr" else self.base_npv

        for result in self.results:
            if metric == "irr":
                values = result.irr_results
            else:
                values = result.npv_results

            if not values:
                continue

            data.append({
                "variable": result.display_name,
                "low": min(values),
                "high": max(values),
                "base": base,
                "range": max(values) - min(values),
            })

        # Sort by range (most sensitive first)
        data.sort(key=lambda x: x["range"], reverse=True)

        return data


# ============================================================================
# SENSITIVITY CONFIGURATIONS
# ============================================================================

def get_default_sensitivity_variables(base_proforma: EnhancedProForma) -> List[SensitivityVariable]:
    """
    Get default sensitivity variables based on the base pro forma.

    Args:
        base_proforma: The base case pro forma

    Returns:
        List of SensitivityVariable configurations
    """
    # Extract base values
    avg_rate = base_proforma.unit_mix.weighted_avg_rate_psf
    construction_cost = base_proforma.development_budget.building_cost / base_proforma.nrsf
    interest_rate = base_proforma.financing.permanent_rate
    exit_cap = base_proforma.exit_cap_rate
    stabilized_occ = base_proforma.stabilized_occupancy
    months_to_stab = base_proforma.months_to_stabilization

    return [
        SensitivityVariable(
            name="rental_rate",
            display_name="Rental Rates",
            base_value=avg_rate,
            unit="$/SF",
            test_deltas=[-0.20, -0.10, 0, 0.10, 0.20],
        ),
        SensitivityVariable(
            name="stabilized_occupancy",
            display_name="Stabilized Occupancy",
            base_value=stabilized_occ,
            unit="%",
            test_deltas=[-10, -5, 0, 5, 8],  # Absolute % points
            is_percentage=True,
        ),
        SensitivityVariable(
            name="construction_cost",
            display_name="Construction Cost",
            base_value=construction_cost,
            unit="$/SF",
            test_deltas=[-0.15, -0.075, 0, 0.075, 0.15],
        ),
        SensitivityVariable(
            name="interest_rate",
            display_name="Interest Rate",
            base_value=interest_rate * 100,  # Convert to %
            unit="%",
            test_deltas=[-1.0, -0.5, 0, 0.5, 1.0],  # Absolute % points (100bps, 50bps)
            is_percentage=True,
        ),
        SensitivityVariable(
            name="exit_cap_rate",
            display_name="Exit Cap Rate",
            base_value=exit_cap * 100,  # Convert to %
            unit="%",
            test_deltas=[-0.75, -0.375, 0, 0.375, 0.75],  # Absolute % points (75bps, 37.5bps)
            is_percentage=True,
        ),
        SensitivityVariable(
            name="months_to_stabilization",
            display_name="Lease-Up Timeline",
            base_value=months_to_stab,
            unit="months",
            test_deltas=[-12, -6, 0, 6, 12],  # Absolute months
            is_percentage=True,
        ),
    ]


# ============================================================================
# SENSITIVITY ENGINE
# ============================================================================

def run_sensitivity_test(
    variable: SensitivityVariable,
    base_params: Dict,
    unit_mix: UnitMix,
) -> SensitivityResult:
    """
    Run sensitivity test for a single variable.

    Args:
        variable: Variable configuration
        base_params: Base case parameters for build_enhanced_pro_forma
        unit_mix: Base unit mix

    Returns:
        SensitivityResult with all test outcomes
    """
    result = SensitivityResult(
        variable_name=variable.name,
        display_name=variable.display_name,
        base_value=variable.base_value,
        unit=variable.unit,
    )

    for delta in variable.test_deltas:
        # Calculate test value
        if variable.is_percentage:
            test_value = variable.base_value + delta
        else:
            test_value = variable.base_value * (1 + delta)

        result.test_values.append(test_value)

        # Create label
        if delta == 0:
            result.test_labels.append("Base")
        elif variable.is_percentage:
            result.test_labels.append(f"{delta:+.1f}")
        else:
            result.test_labels.append(f"{delta*100:+.0f}%")

        # Build pro forma with modified parameter
        modified_params = deepcopy(base_params)
        modified_mix = deepcopy(unit_mix)

        # Apply modification based on variable
        if variable.name == "rental_rate":
            # Modify all unit rates proportionally
            rate_multiplier = test_value / variable.base_value
            for unit in modified_mix.units:
                unit.monthly_rate *= rate_multiplier
                unit.rate_psf = unit.monthly_rate / unit.sf_per_unit

        elif variable.name == "stabilized_occupancy":
            modified_params["stabilized_occupancy"] = max(60, min(98, test_value))

        elif variable.name == "construction_cost":
            modified_params["construction_cost_psf"] = test_value

        elif variable.name == "interest_rate":
            modified_params["interest_rate"] = test_value / 100  # Convert back to decimal

        elif variable.name == "exit_cap_rate":
            modified_params["exit_cap_rate"] = test_value / 100  # Convert back to decimal

        elif variable.name == "months_to_stabilization":
            modified_params["months_to_stabilization"] = max(18, int(test_value))

        # Build modified pro forma
        try:
            proforma = build_enhanced_pro_forma(
                unit_mix=modified_mix,
                **modified_params
            )

            result.irr_results.append(proforma.metrics.irr_7yr)
            result.npv_results.append(proforma.metrics.npv_7yr)
            result.dscr_results.append(proforma.metrics.dscr_stabilized)

        except Exception as e:
            print(f"Error in sensitivity test {variable.name} @ {test_value}: {e}")
            result.irr_results.append(0)
            result.npv_results.append(0)
            result.dscr_results.append(0)

    # Calculate summary stats
    if result.irr_results:
        base_idx = variable.test_deltas.index(0) if 0 in variable.test_deltas else len(variable.test_deltas) // 2
        result.irr_base = result.irr_results[base_idx]
        result.irr_min = min(result.irr_results)
        result.irr_max = max(result.irr_results)
        result.irr_range = result.irr_max - result.irr_min

        result.npv_base = result.npv_results[base_idx]
        result.npv_min = min(result.npv_results)
        result.npv_max = max(result.npv_results)
        result.npv_range = result.npv_max - result.npv_min

    return result


def run_tornado_analysis(
    base_proforma: EnhancedProForma,
    variables: Optional[List[SensitivityVariable]] = None,
) -> TornadoAnalysis:
    """
    Run complete tornado diagram analysis.

    Args:
        base_proforma: Base case pro forma
        variables: Optional custom variables (uses defaults if None)

    Returns:
        Complete TornadoAnalysis with all results
    """
    from datetime import datetime

    # Get variables
    if variables is None:
        variables = get_default_sensitivity_variables(base_proforma)

    # Extract base parameters for rebuilding pro forma
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

    # Run tests for each variable
    results = []
    for var in variables:
        result = run_sensitivity_test(var, base_params, base_proforma.unit_mix)
        results.append(result)

    # Rank by IRR sensitivity
    results.sort(key=lambda r: r.irr_range, reverse=True)
    for i, result in enumerate(results):
        result.sensitivity_rank = i + 1

    # Build analysis
    analysis = TornadoAnalysis(
        project_name=base_proforma.project_name,
        analysis_date=datetime.now().strftime("%Y-%m-%d"),
        base_irr=base_proforma.metrics.irr_7yr,
        base_npv=base_proforma.metrics.npv_7yr,
        base_dscr=base_proforma.metrics.dscr_stabilized,
        results=results,
        most_sensitive_variable=results[0].display_name if results else "",
    )

    # Calculate total ranges
    all_irrs = [irr for r in results for irr in r.irr_results]
    all_npvs = [npv for r in results for npv in r.npv_results]

    if all_irrs:
        analysis.irr_range_total = (min(all_irrs), max(all_irrs))
    if all_npvs:
        analysis.npv_range_total = (min(all_npvs), max(all_npvs))

    return analysis


# ============================================================================
# REPORTING HELPERS
# ============================================================================

def format_sensitivity_table(analysis: TornadoAnalysis) -> str:
    """
    Format sensitivity results as a markdown table.

    Args:
        analysis: Complete tornado analysis

    Returns:
        Markdown formatted table
    """
    lines = [
        "| Variable | Base | -20%/-10% | +10%/+20% | IRR Range |",
        "|----------|------|-----------|-----------|-----------|",
    ]

    for result in analysis.results:
        # Get low and high IRR
        if len(result.irr_results) >= 2:
            low_irr = result.irr_results[0]  # Most negative delta
            high_irr = result.irr_results[-1]  # Most positive delta
        else:
            low_irr = high_irr = result.irr_base

        lines.append(
            f"| {result.display_name} | {result.irr_base:.1f}% | "
            f"{low_irr:.1f}% | {high_irr:.1f}% | {result.irr_range:.1f}% |"
        )

    return "\n".join(lines)


def get_sensitivity_insights(analysis: TornadoAnalysis) -> List[str]:
    """
    Generate insights from sensitivity analysis.

    Args:
        analysis: Complete tornado analysis

    Returns:
        List of insight strings
    """
    insights = []

    if not analysis.results:
        return ["Insufficient data for sensitivity analysis."]

    # Most sensitive variable
    top = analysis.results[0]
    insights.append(
        f"**{top.display_name}** is the most sensitive variable, with IRR ranging "
        f"from {top.irr_min:.1f}% to {top.irr_max:.1f}% ({top.irr_range:.1f}% spread)."
    )

    # IRR downside risk
    irr_low = analysis.irr_range_total[0]
    if irr_low < 10:
        insights.append(
            f"Downside scenario shows IRR of {irr_low:.1f}%, below typical hurdle rates. "
            "Risk mitigation strategies should be considered."
        )
    elif irr_low >= 12:
        insights.append(
            f"Even in downside scenarios, IRR remains attractive at {irr_low:.1f}%, "
            "suggesting resilient returns."
        )

    # Occupancy sensitivity
    occ_result = next((r for r in analysis.results if r.variable_name == "stabilized_occupancy"), None)
    if occ_result and occ_result.irr_range > 5:
        insights.append(
            f"Occupancy assumptions significantly impact returns (IRR range: {occ_result.irr_range:.1f}%). "
            "Market demand validation is critical."
        )

    # Construction cost sensitivity
    cost_result = next((r for r in analysis.results if r.variable_name == "construction_cost"), None)
    if cost_result and cost_result.irr_range > 3:
        insights.append(
            f"Construction costs have meaningful impact (IRR range: {cost_result.irr_range:.1f}%). "
            "Consider fixed-price contracts to mitigate."
        )

    return insights


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    from financial_model_v2 import create_default_unit_mix, build_enhanced_pro_forma

    print("=== Sensitivity Analysis Test ===\n")

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

    print(f"Base Case IRR: {base_proforma.metrics.irr_7yr:.2f}%")
    print(f"Base Case NPV: ${base_proforma.metrics.npv_7yr:,.0f}")
    print()

    # Run tornado analysis
    print("Running sensitivity analysis...")
    analysis = run_tornado_analysis(base_proforma)

    print(f"\nMost Sensitive Variable: {analysis.most_sensitive_variable}")
    print(f"IRR Range (all scenarios): {analysis.irr_range_total[0]:.1f}% to {analysis.irr_range_total[1]:.1f}%")
    print()

    # Print table
    print("Sensitivity Results:")
    print(format_sensitivity_table(analysis))
    print()

    # Print insights
    print("Key Insights:")
    for insight in get_sensitivity_insights(analysis):
        print(f"  - {insight}")
    print()

    # Get tornado data for visualization
    tornado_data = analysis.get_tornado_data("irr")
    print("Tornado Chart Data (IRR):")
    for item in tornado_data[:3]:  # Top 3
        print(f"  {item['variable']}: {item['low']:.1f}% - {item['high']:.1f}% (range: {item['range']:.1f}%)")
