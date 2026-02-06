"""
Rate Trend Analyzer for Self-Storage Feasibility

McKinley-level rate analysis:
- Historical rate trend extraction from TractiQ data
- 12-month trailing rate growth calculations
- Rate volatility and trend direction assessment
- Competitive rate positioning (percentile rank)
- Rate forecasting
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date
from statistics import mean, stdev
import re


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class RateDataPoint:
    """Single rate observation"""
    date: str  # YYYY-MM or YYYY-MM-DD
    unit_size: str  # "10x10", "10x20", etc.
    climate_controlled: bool
    rate: float  # Monthly rate
    rate_psf: float  # Rate per SF
    source: str = "TractiQ"


@dataclass
class RateTrendMetrics:
    """Calculated rate trend metrics for a unit size"""
    unit_size: str
    climate_controlled: bool

    # Current rates
    current_rate: float = 0
    current_rate_psf: float = 0

    # Historical data
    data_points: List[RateDataPoint] = field(default_factory=list)
    months_of_data: int = 0

    # Growth metrics
    rate_growth_12mo: float = 0  # YoY growth %
    rate_growth_6mo_annualized: float = 0
    rate_growth_3mo_annualized: float = 0

    # Volatility
    rate_volatility: float = 0  # Std dev of monthly changes
    rate_stability_score: float = 0  # 0-100, higher = more stable

    # Trend
    trend_direction: str = "stable"  # "accelerating", "stable", "decelerating", "declining"
    trend_strength: float = 0  # 0-1


@dataclass
class MarketRatePosition:
    """Competitive rate positioning"""
    # Subject property proposed rate
    proposed_rate_psf: float = 0
    proposed_rate_10x10: float = 0

    # Market statistics
    market_avg_rate_psf: float = 0
    market_median_rate_psf: float = 0
    market_min_rate_psf: float = 0
    market_max_rate_psf: float = 0

    # Positioning
    percentile_rank: float = 0  # 0-100, where proposed rate falls
    premium_discount_pct: float = 0  # vs market average (positive = premium)
    positioning_tier: str = "standard"  # "value", "standard", "premium"


@dataclass
class RateForecast:
    """Rate forecast"""
    current_rate_psf: float = 0
    forecast_12mo_rate_psf: float = 0
    forecast_24mo_rate_psf: float = 0
    forecast_36mo_rate_psf: float = 0

    annual_growth_assumption: float = 0.03  # Default 3%
    forecast_confidence: str = "medium"  # "low", "medium", "high"
    forecast_rationale: str = ""


@dataclass
class RateTrendAnalysis:
    """Complete rate trend analysis"""
    market_name: str
    analysis_date: str

    # Rate trends by unit type
    rate_trends: Dict[str, RateTrendMetrics] = field(default_factory=dict)

    # Overall market metrics
    overall_rate_growth_12mo: float = 0
    overall_trend_direction: str = "stable"

    # Competitive positioning
    market_position: MarketRatePosition = field(default_factory=MarketRatePosition)

    # Forecast
    forecast: RateForecast = field(default_factory=RateForecast)

    # Summary
    rate_environment: str = "neutral"  # "strong", "neutral", "weak"
    pricing_power: str = "moderate"  # "strong", "moderate", "limited"


# ============================================================================
# RATE DATA EXTRACTION
# ============================================================================

def extract_rates_from_tractiq(tractiq_data: Dict) -> List[RateDataPoint]:
    """
    Extract rate data points from TractiQ cached data.

    Args:
        tractiq_data: TractiQ cache data structure

    Returns:
        List of RateDataPoint observations
    """
    data_points = []

    # Get competitors with rates
    competitors = tractiq_data.get("competitors", [])

    for comp in competitors:
        # Extract cached date
        cached_date = comp.get("cached_date", datetime.now().strftime("%Y-%m-%d"))
        if "T" in cached_date:
            cached_date = cached_date.split("T")[0]

        # Extract rates by unit size
        for key, value in comp.items():
            if not key.startswith("rate_") or value is None:
                continue

            try:
                rate = float(value)
                if rate <= 0:
                    continue
            except (ValueError, TypeError):
                continue

            # Parse rate key: rate_cc-10x10 or rate_noncc-10x10
            parts = key.replace("rate_", "").split("-")
            if len(parts) == 2:
                cc_type, size = parts
                climate_controlled = cc_type == "cc"
            else:
                # Old format: rate_10x10_cc
                match = re.match(r"(\d+x\d+)_(cc|noncc)?", key.replace("rate_", ""))
                if match:
                    size = match.group(1)
                    climate_controlled = match.group(2) == "cc"
                else:
                    continue

            # Get SF for rate_psf calculation
            size_sf = {
                "5x5": 25, "5x10": 50, "10x10": 100,
                "10x15": 150, "10x20": 200, "10x30": 300
            }.get(size, 100)

            data_points.append(RateDataPoint(
                date=cached_date,
                unit_size=size,
                climate_controlled=climate_controlled,
                rate=rate * size_sf,  # Convert to monthly if PSF
                rate_psf=rate,
                source="TractiQ"
            ))

    return data_points


def extract_historical_rates_from_pdf(pdf_text: str) -> List[RateDataPoint]:
    """
    Extract historical rate data from Rate Trends PDF text.

    Args:
        pdf_text: Extracted text from Rate Trends PDF

    Returns:
        List of historical RateDataPoint observations
    """
    data_points = []

    # Pattern for rate trend data: "Month Year: $X.XX"
    # TractiQ format varies - adjust patterns as needed
    date_rate_pattern = r"(\w+\s+\d{4}).*?\$?([\d.]+)"

    matches = re.findall(date_rate_pattern, pdf_text)

    for date_str, rate_str in matches:
        try:
            # Parse date
            dt = datetime.strptime(date_str, "%B %Y")
            date_formatted = dt.strftime("%Y-%m")

            rate = float(rate_str)
            if rate <= 0 or rate > 10:  # Sanity check
                continue

            # Assume 10x10 non-CC as benchmark
            data_points.append(RateDataPoint(
                date=date_formatted,
                unit_size="10x10",
                climate_controlled=False,
                rate=rate * 100,  # Assuming PSF rate
                rate_psf=rate,
                source="TractiQ PDF"
            ))
        except (ValueError, AttributeError):
            continue

    return data_points


# ============================================================================
# RATE TREND CALCULATIONS
# ============================================================================

def calculate_rate_trends(data_points: List[RateDataPoint]) -> Dict[str, RateTrendMetrics]:
    """
    Calculate rate trend metrics for each unit type.

    Args:
        data_points: List of rate observations

    Returns:
        Dict of RateTrendMetrics by unit type key
    """
    # Group by unit type
    grouped = {}
    for dp in data_points:
        key = f"{'CC' if dp.climate_controlled else 'NC'}_{dp.unit_size}"
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(dp)

    # Calculate metrics for each group
    results = {}

    for key, points in grouped.items():
        # Sort by date
        points.sort(key=lambda x: x.date)

        # Parse unit info
        cc_str, size = key.split("_")
        is_cc = cc_str == "CC"

        metrics = RateTrendMetrics(
            unit_size=size,
            climate_controlled=is_cc,
            data_points=points,
            months_of_data=len(points),
        )

        if not points:
            results[key] = metrics
            continue

        # Current rate (most recent)
        metrics.current_rate = points[-1].rate
        metrics.current_rate_psf = points[-1].rate_psf

        # Calculate growth rates if we have historical data
        rates = [p.rate_psf for p in points]

        if len(rates) >= 2:
            # Simple growth from first to last
            first_rate = rates[0]
            last_rate = rates[-1]

            if first_rate > 0:
                total_growth = (last_rate - first_rate) / first_rate
                months = len(rates) - 1

                # Annualized
                if months >= 12:
                    metrics.rate_growth_12mo = total_growth / (months / 12) * 100
                else:
                    metrics.rate_growth_12mo = total_growth * (12 / months) * 100

            # Recent growth (last 6 months if available)
            if len(rates) >= 6:
                recent_first = rates[-6]
                if recent_first > 0:
                    recent_growth = (last_rate - recent_first) / recent_first
                    metrics.rate_growth_6mo_annualized = recent_growth * 2 * 100

            # Very recent (last 3 months)
            if len(rates) >= 3:
                very_recent_first = rates[-3]
                if very_recent_first > 0:
                    very_recent_growth = (last_rate - very_recent_first) / very_recent_first
                    metrics.rate_growth_3mo_annualized = very_recent_growth * 4 * 100

        # Volatility
        if len(rates) >= 3:
            # Monthly changes
            changes = [(rates[i] - rates[i-1]) / rates[i-1] * 100
                      for i in range(1, len(rates)) if rates[i-1] > 0]
            if changes:
                metrics.rate_volatility = stdev(changes) if len(changes) > 1 else 0
                # Stability score: lower volatility = higher stability
                metrics.rate_stability_score = max(0, 100 - metrics.rate_volatility * 10)

        # Trend direction
        if metrics.rate_growth_12mo > 5:
            if metrics.rate_growth_3mo_annualized > metrics.rate_growth_12mo:
                metrics.trend_direction = "accelerating"
            else:
                metrics.trend_direction = "growing"
        elif metrics.rate_growth_12mo > 1:
            metrics.trend_direction = "stable"
        elif metrics.rate_growth_12mo > -2:
            metrics.trend_direction = "flat"
        else:
            metrics.trend_direction = "declining"

        # Trend strength (0-1)
        metrics.trend_strength = min(1.0, abs(metrics.rate_growth_12mo) / 10)

        results[key] = metrics

    return results


# ============================================================================
# COMPETITIVE POSITIONING
# ============================================================================

def calculate_market_position(
    proposed_rate_psf: float,
    competitor_rates: List[float],
) -> MarketRatePosition:
    """
    Calculate competitive rate positioning.

    Args:
        proposed_rate_psf: Proposed rate per SF
        competitor_rates: List of competitor rates per SF

    Returns:
        MarketRatePosition analysis
    """
    position = MarketRatePosition()
    position.proposed_rate_psf = proposed_rate_psf

    if not competitor_rates:
        return position

    # Filter valid rates
    valid_rates = [r for r in competitor_rates if r > 0]
    if not valid_rates:
        return position

    # Market statistics
    position.market_avg_rate_psf = mean(valid_rates)
    position.market_min_rate_psf = min(valid_rates)
    position.market_max_rate_psf = max(valid_rates)

    # Median
    sorted_rates = sorted(valid_rates)
    mid = len(sorted_rates) // 2
    if len(sorted_rates) % 2 == 0:
        position.market_median_rate_psf = (sorted_rates[mid-1] + sorted_rates[mid]) / 2
    else:
        position.market_median_rate_psf = sorted_rates[mid]

    # Percentile rank
    below_count = sum(1 for r in valid_rates if r < proposed_rate_psf)
    position.percentile_rank = (below_count / len(valid_rates)) * 100

    # Premium/discount vs average
    if position.market_avg_rate_psf > 0:
        position.premium_discount_pct = (
            (proposed_rate_psf - position.market_avg_rate_psf)
            / position.market_avg_rate_psf * 100
        )

    # Positioning tier
    if position.percentile_rank >= 75:
        position.positioning_tier = "premium"
    elif position.percentile_rank >= 40:
        position.positioning_tier = "standard"
    else:
        position.positioning_tier = "value"

    return position


# ============================================================================
# RATE FORECASTING
# ============================================================================

def forecast_rates(
    current_rate_psf: float,
    historical_growth_rate: float,
    market_conditions: str = "neutral",
) -> RateForecast:
    """
    Forecast future rates.

    Args:
        current_rate_psf: Current rate per SF
        historical_growth_rate: Historical annual growth rate (decimal)
        market_conditions: "strong", "neutral", or "weak"

    Returns:
        RateForecast with projections
    """
    forecast = RateForecast()
    forecast.current_rate_psf = current_rate_psf

    # Adjust growth assumption based on market conditions
    base_growth = historical_growth_rate if historical_growth_rate else 0.03

    market_adjustments = {
        "strong": 0.01,   # Add 1%
        "neutral": 0,
        "weak": -0.01,    # Subtract 1%
    }
    adjustment = market_adjustments.get(market_conditions, 0)

    # Cap growth assumption between -2% and 6%
    forecast.annual_growth_assumption = max(-0.02, min(0.06, base_growth + adjustment))

    # Project rates
    forecast.forecast_12mo_rate_psf = current_rate_psf * (1 + forecast.annual_growth_assumption)
    forecast.forecast_24mo_rate_psf = current_rate_psf * (1 + forecast.annual_growth_assumption) ** 2
    forecast.forecast_36mo_rate_psf = current_rate_psf * (1 + forecast.annual_growth_assumption) ** 3

    # Confidence
    if abs(historical_growth_rate - forecast.annual_growth_assumption) < 0.01:
        forecast.forecast_confidence = "high"
    elif abs(historical_growth_rate - forecast.annual_growth_assumption) < 0.02:
        forecast.forecast_confidence = "medium"
    else:
        forecast.forecast_confidence = "low"

    # Rationale
    growth_pct = forecast.annual_growth_assumption * 100
    forecast.forecast_rationale = (
        f"Projecting {growth_pct:.1f}% annual rate growth based on "
        f"historical trends and {market_conditions} market outlook."
    )

    return forecast


# ============================================================================
# MAIN ANALYSIS FUNCTION
# ============================================================================

def analyze_rate_trends(
    tractiq_data: Dict,
    proposed_rate_psf: Optional[float] = None,
    market_conditions: str = "neutral",
) -> RateTrendAnalysis:
    """
    Run complete rate trend analysis.

    Args:
        tractiq_data: TractiQ cache data
        proposed_rate_psf: Optional proposed rate for positioning analysis
        market_conditions: Market outlook for forecasting

    Returns:
        Complete RateTrendAnalysis
    """
    analysis = RateTrendAnalysis(
        market_name=tractiq_data.get("market_name", "Unknown"),
        analysis_date=datetime.now().strftime("%Y-%m-%d"),
    )

    # Extract rate data
    data_points = extract_rates_from_tractiq(tractiq_data)

    if not data_points:
        analysis.rate_environment = "insufficient_data"
        return analysis

    # Calculate trends
    analysis.rate_trends = calculate_rate_trends(data_points)

    # Overall metrics (weighted by 10x10 benchmark)
    benchmark_key = "NC_10x10"
    if benchmark_key in analysis.rate_trends:
        benchmark = analysis.rate_trends[benchmark_key]
        analysis.overall_rate_growth_12mo = benchmark.rate_growth_12mo
        analysis.overall_trend_direction = benchmark.trend_direction
    else:
        # Average across all
        growths = [t.rate_growth_12mo for t in analysis.rate_trends.values()]
        analysis.overall_rate_growth_12mo = mean(growths) if growths else 0
        analysis.overall_trend_direction = "stable"

    # Competitive positioning
    if proposed_rate_psf:
        competitor_rates = [dp.rate_psf for dp in data_points if dp.unit_size == "10x10"]
        analysis.market_position = calculate_market_position(proposed_rate_psf, competitor_rates)

    # Forecast
    current_avg = mean([t.current_rate_psf for t in analysis.rate_trends.values() if t.current_rate_psf > 0])
    historical_growth = analysis.overall_rate_growth_12mo / 100
    analysis.forecast = forecast_rates(current_avg, historical_growth, market_conditions)

    # Rate environment assessment
    if analysis.overall_rate_growth_12mo > 4:
        analysis.rate_environment = "strong"
        analysis.pricing_power = "strong"
    elif analysis.overall_rate_growth_12mo > 1:
        analysis.rate_environment = "neutral"
        analysis.pricing_power = "moderate"
    elif analysis.overall_rate_growth_12mo > -2:
        analysis.rate_environment = "soft"
        analysis.pricing_power = "limited"
    else:
        analysis.rate_environment = "weak"
        analysis.pricing_power = "minimal"

    return analysis


def format_rate_trend_report(analysis: RateTrendAnalysis) -> str:
    """
    Format rate trend analysis as markdown.

    Args:
        analysis: Complete rate trend analysis

    Returns:
        Markdown formatted report
    """
    lines = [
        f"# Rate Trend Analysis: {analysis.market_name}",
        f"*Analysis Date: {analysis.analysis_date}*",
        "",
        "## Market Overview",
        "",
        f"- **Rate Environment:** {analysis.rate_environment.title()}",
        f"- **12-Month Rate Growth:** {analysis.overall_rate_growth_12mo:.1f}%",
        f"- **Trend Direction:** {analysis.overall_trend_direction.title()}",
        f"- **Pricing Power:** {analysis.pricing_power.title()}",
        "",
        "## Rate Trends by Unit Type",
        "",
        "| Unit Type | Current Rate | 12-Mo Growth | Trend |",
        "|-----------|--------------|--------------|-------|",
    ]

    for key, metrics in analysis.rate_trends.items():
        cc_label = "CC" if metrics.climate_controlled else "NC"
        lines.append(
            f"| {metrics.unit_size} ({cc_label}) | ${metrics.current_rate_psf:.2f}/SF | "
            f"{metrics.rate_growth_12mo:.1f}% | {metrics.trend_direction} |"
        )

    lines.extend([
        "",
        "## Rate Forecast",
        "",
        f"- **Current Average:** ${analysis.forecast.current_rate_psf:.2f}/SF",
        f"- **12-Month Forecast:** ${analysis.forecast.forecast_12mo_rate_psf:.2f}/SF",
        f"- **24-Month Forecast:** ${analysis.forecast.forecast_24mo_rate_psf:.2f}/SF",
        f"- **Growth Assumption:** {analysis.forecast.annual_growth_assumption*100:.1f}%/year",
        f"- **Confidence:** {analysis.forecast.forecast_confidence.title()}",
        "",
    ])

    if analysis.market_position.proposed_rate_psf > 0:
        pos = analysis.market_position
        lines.extend([
            "## Competitive Positioning",
            "",
            f"- **Proposed Rate:** ${pos.proposed_rate_psf:.2f}/SF",
            f"- **Market Average:** ${pos.market_avg_rate_psf:.2f}/SF",
            f"- **Premium/Discount:** {pos.premium_discount_pct:+.1f}%",
            f"- **Percentile Rank:** {pos.percentile_rank:.0f}th percentile",
            f"- **Positioning:** {pos.positioning_tier.title()}",
        ])

    return "\n".join(lines)


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=== Rate Trend Analyzer Test ===\n")

    # Simulate TractiQ data
    tractiq_data = {
        "market_name": "Nashville, TN",
        "competitors": [
            {
                "name": "Storage A",
                "cached_date": "2026-01-15",
                "rate_noncc-5x10": 1.80,
                "rate_noncc-10x10": 1.35,
                "rate_noncc-10x20": 1.15,
                "rate_cc-5x10": 2.20,
                "rate_cc-10x10": 1.65,
            },
            {
                "name": "Storage B",
                "cached_date": "2026-01-15",
                "rate_noncc-5x10": 1.90,
                "rate_noncc-10x10": 1.40,
                "rate_noncc-10x20": 1.20,
                "rate_cc-5x10": 2.30,
                "rate_cc-10x10": 1.70,
            },
            {
                "name": "Storage C",
                "cached_date": "2026-01-15",
                "rate_noncc-5x10": 1.70,
                "rate_noncc-10x10": 1.30,
                "rate_noncc-10x20": 1.10,
                "rate_cc-5x10": 2.10,
                "rate_cc-10x10": 1.55,
            },
        ]
    }

    # Run analysis
    analysis = analyze_rate_trends(
        tractiq_data=tractiq_data,
        proposed_rate_psf=1.45,
        market_conditions="neutral"
    )

    print(format_rate_trend_report(analysis))
