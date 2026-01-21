"""
Competitor Intelligence Module
Automatically infers competitor quality and pricing position from scraped data
"""

from typing import List, Dict
import statistics


def infer_competitor_quality(competitors: List[Dict]) -> str:
    """
    Infer overall competitor quality from facility data

    Looks at:
    - Facility age (if available)
    - Amenities/features
    - Average ratings (if available)
    - NRSF (larger = typically newer/better)

    Returns:
        'Aging/Poor', 'Average', or 'Modern/Strong'
    """

    if not competitors:
        return 'Average'

    quality_scores = []

    for comp in competitors:
        score = 0

        # Check for climate control (modern amenity)
        if comp.get('has_climate_control'):
            score += 2

        # Check for size (larger facilities often newer)
        nrsf = comp.get('nrsf', 0)
        if nrsf > 80000:
            score += 2
        elif nrsf > 50000:
            score += 1

        # Check for online presence/tech (modern operators)
        if comp.get('has_online_reservations'):
            score += 1

        # Check for security features
        if comp.get('has_video_surveillance') or comp.get('has_security'):
            score += 1

        quality_scores.append(score)

    # Calculate average quality
    if quality_scores:
        avg_score = statistics.mean(quality_scores)

        if avg_score >= 4.5:
            return 'Modern/Strong'
        elif avg_score >= 2.5:
            return 'Average'
        else:
            return 'Aging/Poor'

    return 'Average'


def calculate_pricing_position(your_rate_psf: float, comp_avg_rate_psf: float) -> str:
    """
    Calculate pricing position relative to market

    Args:
        your_rate_psf: Your projected rate per SF
        comp_avg_rate_psf: Competitor average rate per SF

    Returns:
        'Above Market', 'At Market', or 'Below Market'
    """

    if comp_avg_rate_psf <= 0 or your_rate_psf <= 0:
        return 'At Market'

    ratio = your_rate_psf / comp_avg_rate_psf

    if ratio >= 1.10:
        return 'Above Market'
    elif ratio >= 0.90:
        return 'At Market'
    else:
        return 'Below Market'


def analyze_competitor_landscape(competitors: List[Dict],
                                 your_proposed_rate_psf: float = None) -> Dict[str, any]:
    """
    Complete competitor analysis

    Args:
        competitors: List of competitor dicts from scraper
        your_proposed_rate_psf: Your projected average rate/SF

    Returns:
        Dict with count, quality, pricing, and insights
    """

    count = len(competitors)

    # Infer quality
    quality = infer_competitor_quality(competitors)

    # Calculate avg competitor rate
    rates = []
    for comp in competitors:
        rate_10x10 = comp.get('rate_10x10_cc')
        if rate_10x10:
            # Convert 10x10 rate to PSF (100 SF unit)
            rate_psf = rate_10x10 / 100
            rates.append(rate_psf)

    avg_comp_rate_psf = statistics.mean(rates) if rates else 1.20

    # Determine pricing position
    if your_proposed_rate_psf:
        pricing = calculate_pricing_position(your_proposed_rate_psf, avg_comp_rate_psf)
    else:
        pricing = 'At Market'  # Default

    # Generate insights
    insights = []

    if count <= 2:
        insights.append("Limited competition presents strong market entry opportunity")
    elif count >= 8:
        insights.append("Saturated market requires differentiation strategy")

    if quality == 'Aging/Poor':
        insights.append("Aging competitor base allows for premium positioning")
    elif quality == 'Modern/Strong':
        insights.append("Strong competition requires best-in-class execution")

    if pricing == 'Above Market':
        insights.append("Premium pricing strategy feasible given market conditions")
    elif pricing == 'Below Market':
        insights.append("Aggressive pricing needed to compete with established operators")

    return {
        'count': count,
        'quality': quality,
        'pricing': pricing,
        'avg_comp_rate_psf': avg_comp_rate_psf,
        'insights': insights
    }


# Convenience function for easy integration
def get_competitor_intelligence(competitors: List[Dict],
                               your_rate_psf: float = None) -> Dict[str, str]:
    """
    Easy-to-use function that returns competitor scoring attributes

    Usage:
        comp_intel = get_competitor_intelligence(competitors, 1.30)
        print(comp_intel['quality'])   # "Average"
        print(comp_intel['pricing'])   # "Above Market"
    """

    analysis = analyze_competitor_landscape(competitors, your_rate_psf)

    return {
        'count': analysis['count'],
        'quality': analysis['quality'],
        'pricing': analysis['pricing']
    }
