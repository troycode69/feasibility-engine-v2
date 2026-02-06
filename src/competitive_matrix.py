"""
Competitive Positioning Matrix for Self-Storage Feasibility

McKinley-level competitive analysis:
- Segment competitors into tiers (Value, Standard, Premium)
- Identify competitive advantages and risks
- Recommend positioning and rate range
- SWOT-style competitive assessment
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean, median


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class CompetitorProfile:
    """Individual competitor profile"""
    name: str
    address: str
    distance_miles: float

    # Physical
    nrsf: int = 0
    units: int = 0
    stories: int = 1
    year_built: Optional[int] = None
    climate_controlled_pct: float = 0

    # Rates
    rate_10x10_nc: float = 0
    rate_10x10_cc: float = 0
    avg_rate_psf: float = 0

    # Performance (if available)
    occupancy: Optional[float] = None

    # Quality assessment
    quality_tier: str = "standard"  # "value", "standard", "premium"
    quality_score: float = 50  # 0-100

    # Features
    has_climate_control: bool = False
    has_drive_up: bool = True
    has_rv_boat: bool = False
    has_wine_storage: bool = False
    is_multistory: bool = False
    has_elevator: bool = False

    # Ownership
    operator_type: str = "unknown"  # "reit", "regional", "independent"


@dataclass
class MarketSegment:
    """Market segment definition"""
    name: str  # "value", "standard", "premium"
    rate_range: Tuple[float, float] = (0, 0)  # Min/max rate PSF
    avg_rate_psf: float = 0
    competitor_count: int = 0
    competitors: List[CompetitorProfile] = field(default_factory=list)
    market_share_pct: float = 0  # % of total SF in this segment


@dataclass
class CompetitiveAdvantage:
    """Single competitive advantage or risk"""
    category: str  # "location", "quality", "price", "features", "brand"
    description: str
    impact: str  # "high", "medium", "low"
    is_advantage: bool = True  # False = risk/disadvantage


@dataclass
class PositioningRecommendation:
    """Strategic positioning recommendation"""
    recommended_segment: str  # "value", "standard", "premium"
    recommended_rate_range: Tuple[float, float]
    recommended_rate_10x10: float

    positioning_rationale: str
    differentiation_strategy: str

    # Rate guidance
    opening_rate_recommendation: float
    stabilized_rate_recommendation: float
    rate_growth_assumption: float


@dataclass
class CompetitiveMatrix:
    """Complete competitive matrix analysis"""
    market_name: str
    analysis_date: str
    subject_address: str

    # All competitors
    competitors: List[CompetitorProfile] = field(default_factory=list)
    total_competitor_sf: int = 0

    # Market segments
    value_segment: MarketSegment = field(default_factory=lambda: MarketSegment(name="value"))
    standard_segment: MarketSegment = field(default_factory=lambda: MarketSegment(name="standard"))
    premium_segment: MarketSegment = field(default_factory=lambda: MarketSegment(name="premium"))

    # Subject property profile
    subject_profile: CompetitorProfile = field(default_factory=lambda: CompetitorProfile(name="Subject", address="", distance_miles=0))

    # Competitive assessment
    advantages: List[CompetitiveAdvantage] = field(default_factory=list)
    risks: List[CompetitiveAdvantage] = field(default_factory=list)

    # Recommendation
    positioning: PositioningRecommendation = field(default_factory=lambda: PositioningRecommendation(
        recommended_segment="standard",
        recommended_rate_range=(0, 0),
        recommended_rate_10x10=0,
        positioning_rationale="",
        differentiation_strategy="",
        opening_rate_recommendation=0,
        stabilized_rate_recommendation=0,
        rate_growth_assumption=0.03
    ))

    # Summary
    competitive_intensity: str = "moderate"  # "low", "moderate", "high", "intense"
    market_opportunity: str = "neutral"  # "strong", "neutral", "limited"


# ============================================================================
# COMPETITOR PROFILING
# ============================================================================

def profile_competitor(comp_data: Dict) -> CompetitorProfile:
    """
    Create competitor profile from TractiQ data.

    Args:
        comp_data: Competitor dict from TractiQ

    Returns:
        CompetitorProfile
    """
    profile = CompetitorProfile(
        name=comp_data.get("name", "Unknown"),
        address=comp_data.get("address", ""),
        distance_miles=comp_data.get("distance_miles", 0),
        nrsf=comp_data.get("nrsf", 0),
        occupancy=comp_data.get("occupancy"),
    )

    # Extract rates
    rates = []
    for key, value in comp_data.items():
        if key.startswith("rate_") and value is not None:
            try:
                rate = float(value)
                if rate > 0:
                    rates.append(rate)
                    if "10x10" in key and "noncc" in key:
                        profile.rate_10x10_nc = rate
                    elif "10x10" in key and "cc" in key:
                        profile.rate_10x10_cc = rate
            except (ValueError, TypeError):
                pass

    if rates:
        profile.avg_rate_psf = mean(rates)

    # Infer features from name/data
    name_lower = profile.name.lower()
    if any(x in name_lower for x in ["extra space", "public storage", "cubesmart", "life storage"]):
        profile.operator_type = "reit"
        profile.quality_score += 15
    elif any(x in name_lower for x in ["storage", "self"]):
        profile.operator_type = "regional"

    # Infer quality from rates
    if profile.avg_rate_psf > 0:
        if profile.avg_rate_psf >= 1.60:
            profile.quality_tier = "premium"
            profile.quality_score = 75
        elif profile.avg_rate_psf >= 1.20:
            profile.quality_tier = "standard"
            profile.quality_score = 50
        else:
            profile.quality_tier = "value"
            profile.quality_score = 30

    # Check for climate control
    if profile.rate_10x10_cc > 0:
        profile.has_climate_control = True

    return profile


def segment_competitors(competitors: List[CompetitorProfile]) -> Tuple[MarketSegment, MarketSegment, MarketSegment]:
    """
    Segment competitors into value, standard, and premium tiers.

    Args:
        competitors: List of competitor profiles

    Returns:
        Tuple of (value, standard, premium) MarketSegment
    """
    # Calculate rate percentiles
    rates = [c.avg_rate_psf for c in competitors if c.avg_rate_psf > 0]

    if not rates:
        return (
            MarketSegment(name="value"),
            MarketSegment(name="standard"),
            MarketSegment(name="premium")
        )

    sorted_rates = sorted(rates)
    p33 = sorted_rates[int(len(sorted_rates) * 0.33)] if len(sorted_rates) > 2 else sorted_rates[0]
    p66 = sorted_rates[int(len(sorted_rates) * 0.66)] if len(sorted_rates) > 2 else sorted_rates[-1]

    value = MarketSegment(
        name="value",
        rate_range=(min(rates), p33),
        competitors=[c for c in competitors if c.avg_rate_psf <= p33]
    )

    standard = MarketSegment(
        name="standard",
        rate_range=(p33, p66),
        competitors=[c for c in competitors if p33 < c.avg_rate_psf <= p66]
    )

    premium = MarketSegment(
        name="premium",
        rate_range=(p66, max(rates)),
        competitors=[c for c in competitors if c.avg_rate_psf > p66]
    )

    # Calculate averages
    for segment in [value, standard, premium]:
        segment.competitor_count = len(segment.competitors)
        if segment.competitors:
            segment_rates = [c.avg_rate_psf for c in segment.competitors if c.avg_rate_psf > 0]
            segment.avg_rate_psf = mean(segment_rates) if segment_rates else 0

    # Market share
    total_sf = sum(c.nrsf for c in competitors)
    if total_sf > 0:
        value.market_share_pct = sum(c.nrsf for c in value.competitors) / total_sf * 100
        standard.market_share_pct = sum(c.nrsf for c in standard.competitors) / total_sf * 100
        premium.market_share_pct = sum(c.nrsf for c in premium.competitors) / total_sf * 100

    return value, standard, premium


# ============================================================================
# COMPETITIVE ASSESSMENT
# ============================================================================

def assess_competitive_position(
    subject: CompetitorProfile,
    competitors: List[CompetitorProfile],
    market_avg_rate: float,
) -> Tuple[List[CompetitiveAdvantage], List[CompetitiveAdvantage]]:
    """
    Assess competitive advantages and risks.

    Args:
        subject: Subject property profile
        competitors: Competitor profiles
        market_avg_rate: Market average rate PSF

    Returns:
        Tuple of (advantages, risks)
    """
    advantages = []
    risks = []

    # Location advantages
    nearby_competitors = [c for c in competitors if c.distance_miles <= 1.0]
    if len(nearby_competitors) < 3:
        advantages.append(CompetitiveAdvantage(
            category="location",
            description=f"Limited direct competition within 1 mile ({len(nearby_competitors)} facilities)",
            impact="high",
            is_advantage=True
        ))
    elif len(nearby_competitors) > 5:
        risks.append(CompetitiveAdvantage(
            category="location",
            description=f"Dense competition within 1 mile ({len(nearby_competitors)} facilities)",
            impact="high",
            is_advantage=False
        ))

    # Quality advantages
    if subject.has_climate_control:
        cc_competitors = [c for c in competitors if c.has_climate_control]
        if len(cc_competitors) < len(competitors) * 0.5:
            advantages.append(CompetitiveAdvantage(
                category="features",
                description="Climate control offering differentiates from majority of competitors",
                impact="medium",
                is_advantage=True
            ))

    # Price positioning
    if subject.avg_rate_psf > 0:
        if subject.avg_rate_psf < market_avg_rate * 0.90:
            advantages.append(CompetitiveAdvantage(
                category="price",
                description=f"Competitive pricing ({(1 - subject.avg_rate_psf/market_avg_rate)*100:.0f}% below market)",
                impact="high",
                is_advantage=True
            ))
        elif subject.avg_rate_psf > market_avg_rate * 1.10:
            risks.append(CompetitiveAdvantage(
                category="price",
                description=f"Premium pricing may limit absorption ({(subject.avg_rate_psf/market_avg_rate - 1)*100:.0f}% above market)",
                impact="medium",
                is_advantage=False
            ))

    # REIT competition
    reit_competitors = [c for c in competitors if c.operator_type == "reit"]
    if reit_competitors:
        risks.append(CompetitiveAdvantage(
            category="brand",
            description=f"{len(reit_competitors)} REIT-operated facilities in market with brand recognition",
            impact="medium",
            is_advantage=False
        ))
    else:
        advantages.append(CompetitiveAdvantage(
            category="brand",
            description="No major REIT presence in immediate market",
            impact="medium",
            is_advantage=True
        ))

    # Size advantage
    avg_competitor_size = mean([c.nrsf for c in competitors if c.nrsf > 0]) if competitors else 0
    if subject.nrsf > 0 and avg_competitor_size > 0:
        if subject.nrsf > avg_competitor_size * 1.3:
            advantages.append(CompetitiveAdvantage(
                category="scale",
                description=f"Larger facility ({subject.nrsf:,} SF vs {avg_competitor_size:,.0f} SF avg) enables economies of scale",
                impact="medium",
                is_advantage=True
            ))

    return advantages, risks


# ============================================================================
# POSITIONING RECOMMENDATION
# ============================================================================

def recommend_positioning(
    subject: CompetitorProfile,
    value_segment: MarketSegment,
    standard_segment: MarketSegment,
    premium_segment: MarketSegment,
    advantages: List[CompetitiveAdvantage],
) -> PositioningRecommendation:
    """
    Generate positioning recommendation.

    Args:
        subject: Subject property
        value_segment: Value segment analysis
        standard_segment: Standard segment analysis
        premium_segment: Premium segment analysis
        advantages: Identified advantages

    Returns:
        PositioningRecommendation
    """
    # Count advantage categories
    quality_advantages = sum(1 for a in advantages if a.category in ("features", "quality"))
    location_advantages = sum(1 for a in advantages if a.category == "location")

    # Determine recommended segment
    if quality_advantages >= 2 or (subject.has_climate_control and subject.is_multistory):
        recommended = "premium"
        segment = premium_segment
        differentiation = "Premium positioning based on modern facility features and climate control offering"
    elif quality_advantages >= 1 or location_advantages >= 1:
        recommended = "standard"
        segment = standard_segment
        differentiation = "Standard positioning with competitive features and market-rate pricing"
    else:
        recommended = "value"
        segment = value_segment
        differentiation = "Value positioning to capture price-sensitive demand and achieve faster lease-up"

    # Rate recommendation
    if segment.rate_range[0] > 0:
        rate_range = segment.rate_range
        mid_rate = (rate_range[0] + rate_range[1]) / 2

        # Opening discount
        opening_rate = mid_rate * 0.95  # 5% opening discount

        # 10x10 rate (assuming ~1.0x the PSF rate)
        rate_10x10 = mid_rate * 100
    else:
        # Default
        rate_range = (1.20, 1.50)
        mid_rate = 1.35
        opening_rate = 1.28
        rate_10x10 = 135

    rationale = (
        f"{recommended.title()} segment positioning recommended based on facility characteristics "
        f"and competitive landscape. Target rate range of ${rate_range[0]:.2f}-${rate_range[1]:.2f}/SF "
        f"aligns with comparable facilities in the market."
    )

    return PositioningRecommendation(
        recommended_segment=recommended,
        recommended_rate_range=rate_range,
        recommended_rate_10x10=rate_10x10,
        positioning_rationale=rationale,
        differentiation_strategy=differentiation,
        opening_rate_recommendation=opening_rate,
        stabilized_rate_recommendation=mid_rate,
        rate_growth_assumption=0.03
    )


# ============================================================================
# MAIN ANALYSIS FUNCTION
# ============================================================================

def build_competitive_matrix(
    subject_address: str,
    subject_nrsf: int,
    subject_features: Dict,
    competitors_data: List[Dict],
    market_name: str = "Market",
) -> CompetitiveMatrix:
    """
    Build complete competitive matrix.

    Args:
        subject_address: Subject property address
        subject_nrsf: Subject property NRSF
        subject_features: Subject property features dict
        competitors_data: List of competitor dicts from TractiQ
        market_name: Market name

    Returns:
        Complete CompetitiveMatrix
    """
    matrix = CompetitiveMatrix(
        market_name=market_name,
        analysis_date=datetime.now().strftime("%Y-%m-%d"),
        subject_address=subject_address,
    )

    # Build subject profile
    matrix.subject_profile = CompetitorProfile(
        name="Subject Property",
        address=subject_address,
        distance_miles=0,
        nrsf=subject_nrsf,
        has_climate_control=subject_features.get("climate_controlled", True),
        is_multistory=subject_features.get("multistory", False),
    )

    # Profile competitors
    matrix.competitors = [profile_competitor(c) for c in competitors_data]
    matrix.total_competitor_sf = sum(c.nrsf for c in matrix.competitors)

    # Segment competitors
    matrix.value_segment, matrix.standard_segment, matrix.premium_segment = segment_competitors(
        matrix.competitors
    )

    # Calculate market average
    all_rates = [c.avg_rate_psf for c in matrix.competitors if c.avg_rate_psf > 0]
    market_avg_rate = mean(all_rates) if all_rates else 1.35

    # Assess competitive position
    matrix.advantages, matrix.risks = assess_competitive_position(
        subject=matrix.subject_profile,
        competitors=matrix.competitors,
        market_avg_rate=market_avg_rate,
    )

    # Generate positioning recommendation
    matrix.positioning = recommend_positioning(
        subject=matrix.subject_profile,
        value_segment=matrix.value_segment,
        standard_segment=matrix.standard_segment,
        premium_segment=matrix.premium_segment,
        advantages=matrix.advantages,
    )

    # Assess competitive intensity
    nearby = [c for c in matrix.competitors if c.distance_miles <= 3.0]
    if len(nearby) > 15:
        matrix.competitive_intensity = "intense"
    elif len(nearby) > 10:
        matrix.competitive_intensity = "high"
    elif len(nearby) > 5:
        matrix.competitive_intensity = "moderate"
    else:
        matrix.competitive_intensity = "low"

    # Market opportunity
    if len(matrix.advantages) > len(matrix.risks) and matrix.competitive_intensity in ("low", "moderate"):
        matrix.market_opportunity = "strong"
    elif len(matrix.advantages) >= len(matrix.risks):
        matrix.market_opportunity = "neutral"
    else:
        matrix.market_opportunity = "limited"

    return matrix


def format_competitive_matrix_report(matrix: CompetitiveMatrix) -> str:
    """
    Format competitive matrix as markdown.

    Args:
        matrix: Complete competitive matrix

    Returns:
        Markdown formatted report
    """
    lines = [
        f"# Competitive Matrix: {matrix.market_name}",
        f"*Analysis Date: {matrix.analysis_date}*",
        "",
        f"## Market Overview",
        "",
        f"- **Competitive Intensity:** {matrix.competitive_intensity.title()}",
        f"- **Market Opportunity:** {matrix.market_opportunity.title()}",
        f"- **Total Competitors Analyzed:** {len(matrix.competitors)}",
        f"- **Total Competitor SF:** {matrix.total_competitor_sf:,}",
        "",
        "---",
        "",
        "## Market Segments",
        "",
        "| Segment | Rate Range | Avg Rate | Facilities | Market Share |",
        "|---------|------------|----------|------------|--------------|",
        f"| Value | ${matrix.value_segment.rate_range[0]:.2f}-${matrix.value_segment.rate_range[1]:.2f} | "
        f"${matrix.value_segment.avg_rate_psf:.2f} | {matrix.value_segment.competitor_count} | "
        f"{matrix.value_segment.market_share_pct:.0f}% |",
        f"| Standard | ${matrix.standard_segment.rate_range[0]:.2f}-${matrix.standard_segment.rate_range[1]:.2f} | "
        f"${matrix.standard_segment.avg_rate_psf:.2f} | {matrix.standard_segment.competitor_count} | "
        f"{matrix.standard_segment.market_share_pct:.0f}% |",
        f"| Premium | ${matrix.premium_segment.rate_range[0]:.2f}-${matrix.premium_segment.rate_range[1]:.2f} | "
        f"${matrix.premium_segment.avg_rate_psf:.2f} | {matrix.premium_segment.competitor_count} | "
        f"{matrix.premium_segment.market_share_pct:.0f}% |",
        "",
        "---",
        "",
        "## Positioning Recommendation",
        "",
        f"**Recommended Segment:** {matrix.positioning.recommended_segment.title()}",
        "",
        f"**Target Rate Range:** ${matrix.positioning.recommended_rate_range[0]:.2f} - ${matrix.positioning.recommended_rate_range[1]:.2f}/SF",
        "",
        f"**Opening Rate:** ${matrix.positioning.opening_rate_recommendation:.2f}/SF",
        "",
        f"**Stabilized Rate:** ${matrix.positioning.stabilized_rate_recommendation:.2f}/SF",
        "",
        f"*{matrix.positioning.positioning_rationale}*",
        "",
        f"**Differentiation Strategy:** {matrix.positioning.differentiation_strategy}",
        "",
    ]

    if matrix.advantages:
        lines.extend([
            "---",
            "",
            "## Competitive Advantages",
            "",
        ])
        for adv in matrix.advantages:
            lines.append(f"- **{adv.category.title()}:** {adv.description} *(Impact: {adv.impact})*")
        lines.append("")

    if matrix.risks:
        lines.extend([
            "---",
            "",
            "## Competitive Risks",
            "",
        ])
        for risk in matrix.risks:
            lines.append(f"- **{risk.category.title()}:** {risk.description} *(Impact: {risk.impact})*")
        lines.append("")

    # Top competitors table
    lines.extend([
        "---",
        "",
        "## Key Competitors (Closest 10)",
        "",
        "| Name | Distance | Size | Rate/SF | Segment |",
        "|------|----------|------|---------|---------|",
    ])

    sorted_comps = sorted(matrix.competitors, key=lambda c: c.distance_miles)[:10]
    for comp in sorted_comps:
        lines.append(
            f"| {comp.name[:25]} | {comp.distance_miles:.1f} mi | "
            f"{comp.nrsf:,} SF | ${comp.avg_rate_psf:.2f} | {comp.quality_tier} |"
        )

    return "\n".join(lines)


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=== Competitive Matrix Test ===\n")

    # Simulated competitor data
    competitors_data = [
        {"name": "CubeSmart Self Storage", "address": "123 Main", "distance_miles": 0.5, "nrsf": 85000, "rate_noncc-10x10": 1.45, "rate_cc-10x10": 1.75},
        {"name": "Public Storage", "address": "456 Oak", "distance_miles": 1.2, "nrsf": 65000, "rate_noncc-10x10": 1.55, "rate_cc-10x10": 1.85},
        {"name": "Extra Space Storage", "address": "789 Pine", "distance_miles": 1.8, "nrsf": 72000, "rate_noncc-10x10": 1.60, "rate_cc-10x10": 1.90},
        {"name": "Local Storage", "address": "321 Elm", "distance_miles": 0.8, "nrsf": 35000, "rate_noncc-10x10": 1.15},
        {"name": "Budget Storage", "address": "654 Oak", "distance_miles": 2.1, "nrsf": 28000, "rate_noncc-10x10": 0.95},
        {"name": "SecureStore", "address": "987 Maple", "distance_miles": 2.5, "nrsf": 42000, "rate_noncc-10x10": 1.25, "rate_cc-10x10": 1.55},
    ]

    matrix = build_competitive_matrix(
        subject_address="1202 Antioch Pike, Nashville, TN",
        subject_nrsf=60000,
        subject_features={"climate_controlled": True, "multistory": False},
        competitors_data=competitors_data,
        market_name="Nashville, TN",
    )

    print(format_competitive_matrix_report(matrix))
