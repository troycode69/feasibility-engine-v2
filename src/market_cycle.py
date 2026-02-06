"""
Market Cycle Assessment for Self-Storage Feasibility

McKinley-level market cycle analysis:
- Determine market cycle phase (Recovery, Expansion, Hypersupply, Recession)
- Entry timing recommendations
- Development timeline risk assessment
- Cycle-adjusted return expectations
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class CyclePhase(Enum):
    """Real estate market cycle phases"""
    RECOVERY = "recovery"
    EXPANSION = "expansion"
    HYPERSUPPLY = "hypersupply"
    RECESSION = "recession"


@dataclass
class CycleIndicator:
    """Individual cycle indicator"""
    name: str
    current_value: float
    trend: str  # "rising", "stable", "falling"
    cycle_signal: CyclePhase
    weight: float = 1.0
    description: str = ""


@dataclass
class MarketCycleAssessment:
    """Complete market cycle assessment"""
    market_name: str
    analysis_date: str

    # Cycle determination
    cycle_phase: CyclePhase = CyclePhase.EXPANSION
    cycle_confidence: float = 0.5  # 0-1 confidence in assessment
    phase_maturity: str = "mid"  # "early", "mid", "late"

    # Indicators
    indicators: List[CycleIndicator] = field(default_factory=list)

    # Trends
    occupancy_trend: str = "stable"
    rate_trend: str = "stable"
    supply_trend: str = "stable"
    demand_trend: str = "stable"

    # Timing
    entry_timing: str = "neutral"  # "favorable", "neutral", "unfavorable"
    timing_rationale: str = ""

    # Development risk
    development_timeline_risk: str = "moderate"  # "low", "moderate", "high"
    cycle_risk_premium: float = 0  # Additional IRR required due to cycle risk

    # Return expectations
    expected_return_adjustment: float = 0  # +/- adjustment to base case IRR
    cycle_adjusted_irr_range: Tuple[float, float] = (0, 0)

    # Recommendations
    recommendations: List[str] = field(default_factory=list)


# ============================================================================
# CYCLE INDICATORS
# ============================================================================

def assess_occupancy_indicator(
    current_occupancy: float,
    historical_occupancy: Optional[float] = None,
    market_avg_occupancy: float = 90.0,
) -> CycleIndicator:
    """
    Assess occupancy as a cycle indicator.

    Args:
        current_occupancy: Current market occupancy %
        historical_occupancy: 12-month ago occupancy if available
        market_avg_occupancy: Long-term market average

    Returns:
        CycleIndicator for occupancy
    """
    # Determine trend
    if historical_occupancy:
        change = current_occupancy - historical_occupancy
        if change > 2:
            trend = "rising"
        elif change < -2:
            trend = "falling"
        else:
            trend = "stable"
    else:
        trend = "stable"

    # Determine cycle signal
    if current_occupancy >= 93:
        if trend == "rising":
            phase = CyclePhase.EXPANSION
            desc = "High occupancy with upward momentum indicates expansion"
        else:
            phase = CyclePhase.HYPERSUPPLY
            desc = "High occupancy plateauing may signal approaching hypersupply"
    elif current_occupancy >= 88:
        if trend == "rising":
            phase = CyclePhase.RECOVERY
            desc = "Occupancy recovering toward equilibrium"
        elif trend == "falling":
            phase = CyclePhase.HYPERSUPPLY
            desc = "Declining occupancy from healthy levels suggests hypersupply onset"
        else:
            phase = CyclePhase.EXPANSION
            desc = "Stable healthy occupancy indicates mature expansion"
    elif current_occupancy >= 82:
        if trend == "rising":
            phase = CyclePhase.RECOVERY
            desc = "Occupancy improving from trough"
        else:
            phase = CyclePhase.RECESSION
            desc = "Below-average occupancy with flat/falling trend indicates recession"
    else:
        phase = CyclePhase.RECESSION
        desc = "Low occupancy indicates recessionary conditions"

    return CycleIndicator(
        name="Occupancy",
        current_value=current_occupancy,
        trend=trend,
        cycle_signal=phase,
        weight=1.5,  # High importance
        description=desc
    )


def assess_rate_indicator(
    rate_growth_12mo: float,
    rate_growth_3mo_annualized: Optional[float] = None,
) -> CycleIndicator:
    """
    Assess rate growth as a cycle indicator.

    Args:
        rate_growth_12mo: 12-month rate growth %
        rate_growth_3mo_annualized: Recent 3-month trend annualized

    Returns:
        CycleIndicator for rates
    """
    # Determine trend
    if rate_growth_3mo_annualized is not None:
        if rate_growth_3mo_annualized > rate_growth_12mo + 2:
            trend = "rising"
        elif rate_growth_3mo_annualized < rate_growth_12mo - 2:
            trend = "falling"
        else:
            trend = "stable"
    else:
        if rate_growth_12mo > 3:
            trend = "rising"
        elif rate_growth_12mo < 0:
            trend = "falling"
        else:
            trend = "stable"

    # Determine cycle signal
    if rate_growth_12mo >= 5:
        phase = CyclePhase.EXPANSION
        desc = "Strong rate growth indicates robust demand and pricing power"
    elif rate_growth_12mo >= 2:
        if trend == "rising":
            phase = CyclePhase.RECOVERY
            desc = "Improving rate growth suggests recovery momentum"
        else:
            phase = CyclePhase.EXPANSION
            desc = "Healthy rate growth in mature expansion"
    elif rate_growth_12mo >= 0:
        if trend == "falling":
            phase = CyclePhase.HYPERSUPPLY
            desc = "Decelerating rate growth signals supply pressure"
        else:
            phase = CyclePhase.RECOVERY
            desc = "Flat rates with stability suggests recovery"
    else:
        phase = CyclePhase.RECESSION
        desc = "Negative rate growth indicates market weakness"

    return CycleIndicator(
        name="Rate Growth",
        current_value=rate_growth_12mo,
        trend=trend,
        cycle_signal=phase,
        weight=1.3,
        description=desc
    )


def assess_supply_indicator(
    sf_per_capita: float,
    pipeline_sf_pct: float,  # Pipeline as % of current supply
    population_growth: float,
) -> CycleIndicator:
    """
    Assess supply conditions as a cycle indicator.

    Args:
        sf_per_capita: Current SF per capita
        pipeline_sf_pct: Pipeline as % of current supply
        population_growth: Annual population growth %

    Returns:
        CycleIndicator for supply
    """
    # Determine trend based on pipeline
    if pipeline_sf_pct > 8:
        trend = "rising"
    elif pipeline_sf_pct > 4:
        trend = "stable"
    else:
        trend = "falling"

    # Determine cycle signal
    # Adjust for population growth - high growth markets can absorb more supply
    adjusted_supply_pressure = sf_per_capita - (population_growth * 0.5)

    if adjusted_supply_pressure < 5.5:
        phase = CyclePhase.RECOVERY
        desc = "Undersupplied market with limited pipeline supports recovery"
    elif adjusted_supply_pressure < 6.5:
        if trend == "rising":
            phase = CyclePhase.EXPANSION
            desc = "Balanced supply with new development indicates expansion"
        else:
            phase = CyclePhase.EXPANSION
            desc = "Balanced supply environment"
    elif adjusted_supply_pressure < 7.5:
        if trend == "rising":
            phase = CyclePhase.HYPERSUPPLY
            desc = "Supply approaching saturation with continued construction"
        else:
            phase = CyclePhase.EXPANSION
            desc = "Adequate supply levels in late expansion"
    else:
        phase = CyclePhase.HYPERSUPPLY
        desc = "Oversupplied market conditions"

    return CycleIndicator(
        name="Supply Conditions",
        current_value=sf_per_capita,
        trend=trend,
        cycle_signal=phase,
        weight=1.2,
        description=desc
    )


def assess_demand_indicator(
    population_growth: float,
    household_growth: Optional[float] = None,
    employment_growth: Optional[float] = None,
) -> CycleIndicator:
    """
    Assess demand drivers as a cycle indicator.

    Args:
        population_growth: Annual population growth %
        household_growth: Household formation rate if available
        employment_growth: Employment growth if available

    Returns:
        CycleIndicator for demand
    """
    # Use best available data
    primary_metric = household_growth if household_growth else population_growth

    # Employment adds context
    if employment_growth is not None:
        if employment_growth > primary_metric:
            trend = "rising"
        elif employment_growth < primary_metric - 1:
            trend = "falling"
        else:
            trend = "stable"
    else:
        trend = "stable"

    # Determine cycle signal
    if primary_metric >= 2.0:
        phase = CyclePhase.EXPANSION
        desc = "Strong demographic growth driving robust demand"
    elif primary_metric >= 1.0:
        if trend == "rising":
            phase = CyclePhase.RECOVERY
            desc = "Improving demographics support demand recovery"
        else:
            phase = CyclePhase.EXPANSION
            desc = "Healthy demand growth in expansion"
    elif primary_metric >= 0.5:
        phase = CyclePhase.HYPERSUPPLY if trend == "falling" else CyclePhase.RECOVERY
        desc = "Modest demand growth" + (" with slowing momentum" if trend == "falling" else "")
    else:
        phase = CyclePhase.RECESSION
        desc = "Weak demand fundamentals"

    return CycleIndicator(
        name="Demand Drivers",
        current_value=primary_metric,
        trend=trend,
        cycle_signal=phase,
        weight=1.0,
        description=desc
    )


# ============================================================================
# CYCLE DETERMINATION
# ============================================================================

def determine_cycle_phase(indicators: List[CycleIndicator]) -> Tuple[CyclePhase, float, str]:
    """
    Determine overall cycle phase from indicators.

    Args:
        indicators: List of cycle indicators

    Returns:
        Tuple of (phase, confidence, maturity)
    """
    if not indicators:
        return CyclePhase.EXPANSION, 0.5, "mid"

    # Weighted vote
    phase_scores = {
        CyclePhase.RECOVERY: 0,
        CyclePhase.EXPANSION: 0,
        CyclePhase.HYPERSUPPLY: 0,
        CyclePhase.RECESSION: 0,
    }

    total_weight = sum(i.weight for i in indicators)

    for indicator in indicators:
        phase_scores[indicator.cycle_signal] += indicator.weight

    # Normalize
    for phase in phase_scores:
        phase_scores[phase] /= total_weight

    # Determine winner
    winning_phase = max(phase_scores, key=phase_scores.get)
    confidence = phase_scores[winning_phase]

    # Determine maturity based on secondary signals
    trend_signals = [i.trend for i in indicators]
    rising_count = trend_signals.count("rising")
    falling_count = trend_signals.count("falling")

    if winning_phase == CyclePhase.EXPANSION:
        if rising_count > falling_count:
            maturity = "early"
        elif falling_count > rising_count:
            maturity = "late"
        else:
            maturity = "mid"
    elif winning_phase == CyclePhase.RECOVERY:
        if rising_count >= 2:
            maturity = "late"  # Recovery ending, expansion starting
        else:
            maturity = "early"
    elif winning_phase == CyclePhase.HYPERSUPPLY:
        if falling_count >= 2:
            maturity = "late"  # Approaching recession
        else:
            maturity = "early"
    else:  # Recession
        if rising_count >= 1:
            maturity = "late"  # Recovery may be starting
        else:
            maturity = "mid"

    return winning_phase, confidence, maturity


# ============================================================================
# TIMING & RISK ASSESSMENT
# ============================================================================

def assess_entry_timing(
    phase: CyclePhase,
    maturity: str,
    development_timeline_months: int = 24,
) -> Tuple[str, str, str, float]:
    """
    Assess entry timing based on cycle position.

    Args:
        phase: Current cycle phase
        maturity: Phase maturity (early/mid/late)
        development_timeline_months: Expected months to completion

    Returns:
        Tuple of (timing, rationale, risk_level, risk_premium)
    """
    # Map cycle phase and maturity to timing
    timing_map = {
        (CyclePhase.RECOVERY, "early"): ("favorable", "low", 0),
        (CyclePhase.RECOVERY, "mid"): ("favorable", "low", 0),
        (CyclePhase.RECOVERY, "late"): ("very_favorable", "low", -0.5),  # Bonus
        (CyclePhase.EXPANSION, "early"): ("very_favorable", "low", -0.5),
        (CyclePhase.EXPANSION, "mid"): ("favorable", "moderate", 0),
        (CyclePhase.EXPANSION, "late"): ("neutral", "moderate", 0.5),
        (CyclePhase.HYPERSUPPLY, "early"): ("neutral", "moderate", 1.0),
        (CyclePhase.HYPERSUPPLY, "mid"): ("unfavorable", "high", 1.5),
        (CyclePhase.HYPERSUPPLY, "late"): ("unfavorable", "high", 2.0),
        (CyclePhase.RECESSION, "early"): ("unfavorable", "high", 2.5),
        (CyclePhase.RECESSION, "mid"): ("neutral", "moderate", 1.5),  # Contrarian opportunity
        (CyclePhase.RECESSION, "late"): ("favorable", "moderate", 0.5),  # Recovery coming
    }

    key = (phase, maturity)
    timing, risk_level, risk_premium = timing_map.get(key, ("neutral", "moderate", 0.5))

    # Adjust for development timeline
    # If opening coincides with different phase, adjust
    if development_timeline_months > 30:
        # Long timeline adds uncertainty
        risk_premium += 0.5
        if timing == "favorable":
            timing = "neutral"

    # Generate rationale
    rationale_templates = {
        "very_favorable": f"Market in {phase.value} phase ({maturity}) presents optimal entry window. "
                         f"Development timeline aligns with cycle momentum.",
        "favorable": f"Market in {phase.value} phase ({maturity}) offers attractive entry conditions. "
                    f"Moderate risk with solid fundamentals.",
        "neutral": f"Market in {phase.value} phase ({maturity}) presents balanced risk/reward. "
                  f"Careful underwriting and conservative assumptions recommended.",
        "unfavorable": f"Market in {phase.value} phase ({maturity}) presents elevated cycle risk. "
                      f"Consider delaying entry or requiring higher returns to compensate.",
    }

    rationale = rationale_templates.get(timing, "Standard entry conditions.")

    return timing, rationale, risk_level, risk_premium


# ============================================================================
# MAIN ANALYSIS FUNCTION
# ============================================================================

def assess_market_cycle(
    market_name: str,
    current_occupancy: float,
    rate_growth_12mo: float,
    sf_per_capita: float,
    population_growth: float,
    pipeline_sf_pct: float = 5.0,
    historical_occupancy: Optional[float] = None,
    rate_growth_3mo: Optional[float] = None,
    employment_growth: Optional[float] = None,
    base_case_irr: float = 12.0,
) -> MarketCycleAssessment:
    """
    Run complete market cycle assessment.

    Args:
        market_name: Market name
        current_occupancy: Current market occupancy %
        rate_growth_12mo: 12-month rate growth %
        sf_per_capita: Current SF per capita
        population_growth: Annual population growth %
        pipeline_sf_pct: Pipeline as % of current supply
        historical_occupancy: 12-month ago occupancy
        rate_growth_3mo: 3-month rate growth annualized
        employment_growth: Employment growth if available
        base_case_irr: Base case IRR for adjustment

    Returns:
        Complete MarketCycleAssessment
    """
    assessment = MarketCycleAssessment(
        market_name=market_name,
        analysis_date=datetime.now().strftime("%Y-%m-%d"),
    )

    # Build indicators
    assessment.indicators = [
        assess_occupancy_indicator(current_occupancy, historical_occupancy),
        assess_rate_indicator(rate_growth_12mo, rate_growth_3mo),
        assess_supply_indicator(sf_per_capita, pipeline_sf_pct, population_growth),
        assess_demand_indicator(population_growth, employment_growth=employment_growth),
    ]

    # Set trends
    for indicator in assessment.indicators:
        if indicator.name == "Occupancy":
            assessment.occupancy_trend = indicator.trend
        elif indicator.name == "Rate Growth":
            assessment.rate_trend = indicator.trend
        elif indicator.name == "Supply Conditions":
            assessment.supply_trend = indicator.trend
        elif indicator.name == "Demand Drivers":
            assessment.demand_trend = indicator.trend

    # Determine cycle
    assessment.cycle_phase, assessment.cycle_confidence, assessment.phase_maturity = \
        determine_cycle_phase(assessment.indicators)

    # Assess timing
    assessment.entry_timing, assessment.timing_rationale, assessment.development_timeline_risk, \
        assessment.cycle_risk_premium = assess_entry_timing(
            assessment.cycle_phase,
            assessment.phase_maturity
        )

    # Adjust expected returns
    assessment.expected_return_adjustment = -assessment.cycle_risk_premium

    # Calculate cycle-adjusted IRR range
    adjusted_base = base_case_irr + assessment.expected_return_adjustment
    assessment.cycle_adjusted_irr_range = (
        adjusted_base - 3,  # Downside
        adjusted_base + 2   # Upside
    )

    # Generate recommendations
    if assessment.entry_timing == "very_favorable":
        assessment.recommendations.append("Accelerate development timeline to capture cycle window")
        assessment.recommendations.append("Consider securing additional sites in market")
    elif assessment.entry_timing == "favorable":
        assessment.recommendations.append("Proceed with development on standard timeline")
        assessment.recommendations.append("Monitor supply pipeline for changes")
    elif assessment.entry_timing == "neutral":
        assessment.recommendations.append("Use conservative lease-up assumptions")
        assessment.recommendations.append("Build in rate flexibility for market softness")
    else:
        assessment.recommendations.append("Consider delaying project 12-18 months")
        assessment.recommendations.append("Require higher IRR hurdle to compensate for cycle risk")
        assessment.recommendations.append("Consider phased development approach")

    return assessment


def format_cycle_assessment_report(assessment: MarketCycleAssessment) -> str:
    """
    Format market cycle assessment as markdown.

    Args:
        assessment: Complete market cycle assessment

    Returns:
        Markdown formatted report
    """
    lines = [
        f"# Market Cycle Assessment: {assessment.market_name}",
        f"*Analysis Date: {assessment.analysis_date}*",
        "",
        "## Cycle Position",
        "",
        f"**Current Phase:** {assessment.cycle_phase.value.title()} ({assessment.phase_maturity.title()})",
        "",
        f"**Confidence:** {assessment.cycle_confidence*100:.0f}%",
        "",
        f"**Entry Timing:** {assessment.entry_timing.replace('_', ' ').title()}",
        "",
        f"*{assessment.timing_rationale}*",
        "",
        "---",
        "",
        "## Cycle Indicators",
        "",
        "| Indicator | Value | Trend | Signal |",
        "|-----------|-------|-------|--------|",
    ]

    for indicator in assessment.indicators:
        lines.append(
            f"| {indicator.name} | {indicator.current_value:.1f} | "
            f"{indicator.trend.title()} | {indicator.cycle_signal.value.title()} |"
        )

    lines.extend([
        "",
        "### Indicator Details",
        "",
    ])

    for indicator in assessment.indicators:
        lines.append(f"- **{indicator.name}:** {indicator.description}")

    lines.extend([
        "",
        "---",
        "",
        "## Risk Assessment",
        "",
        f"- **Development Timeline Risk:** {assessment.development_timeline_risk.title()}",
        f"- **Cycle Risk Premium:** {assessment.cycle_risk_premium:.1f}% additional return required",
        f"- **Expected Return Adjustment:** {assessment.expected_return_adjustment:+.1f}%",
        f"- **Cycle-Adjusted IRR Range:** {assessment.cycle_adjusted_irr_range[0]:.1f}% - {assessment.cycle_adjusted_irr_range[1]:.1f}%",
        "",
        "---",
        "",
        "## Recommendations",
        "",
    ])

    for rec in assessment.recommendations:
        lines.append(f"- {rec}")

    return "\n".join(lines)


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=== Market Cycle Assessment Test ===\n")

    # Test with Nashville-like market
    assessment = assess_market_cycle(
        market_name="Nashville, TN",
        current_occupancy=91.5,
        rate_growth_12mo=3.2,
        sf_per_capita=5.8,
        population_growth=1.5,
        pipeline_sf_pct=6.0,
        base_case_irr=13.5,
    )

    print(format_cycle_assessment_report(assessment))
