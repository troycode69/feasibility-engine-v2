"""
Test script for FeasibilityAnalyzer
"""

import sys
sys.path.append('src')

from feasibility_analyzer import FeasibilityAnalyzer


def test_strong_market():
    """Test PURSUE recommendation scenario"""
    print("\n" + "="*60)
    print("TEST 1: STRONG MARKET - Should recommend PURSUE")
    print("="*60)

    analyzer = FeasibilityAnalyzer()

    # Strong demographics
    demographics = {
        'population': 85000,  # 5 points
        'income': 78000,      # 5 points
        'growth': 3.5,        # 5 points
        'renter_pct': 52,     # 5 points
        'age_pct': 46         # 5 points
    }  # Total: 25/25

    # Strong supply
    supply = {
        'sf_per_capita': 3.8,       # 8 points
        'occupancy': 92,            # 8 points
        'absorption_trend': 'Strong',  # 5 points
        'pipeline': 0.4             # 4 points
    }  # Total: 25/25

    # Good site
    site = {
        'visibility': 'Excellent',  # 7 points
        'access': 'Excellent',      # 7 points
        'zoning': 'Permitted',      # 6 points
        'size': 'Ideal'             # 5 points
    }  # Total: 25/25

    # Low competition
    competitor = {
        'count': 2,                # 5 points
        'quality': 'Aging/Poor',   # 5 points
        'pricing': 'Above Market'  # 5 points
    }  # Total: 15/15

    # Strong economy
    economic = {
        'unemployment': 3.2,        # 4 points
        'business_growth': 'Strong', # 3 points
        'stability': 'Stable'       # 3 points
    }  # Total: 10/10

    # Run market analysis
    market = analyzer.analyze_market(demographics, supply, site, competitor, economic)
    print(f"\n📊 Market Score: {market['total']}/100")

    # Run financial analysis (strong returns)
    financials = analyzer.analyze_financials(
        land_cost=1_200_000,
        construction_cost_psf=48,
        rentable_sqft=65000,
        avg_rent_psf=1.35
    )

    print(f"💰 Yield on Cost: {financials['yield_on_cost']:.1f}%")
    print(f"💰 Equity Multiple: {financials['equity_multiple']:.1f}x")

    # Get recommendation
    rec = analyzer.get_recommendation()
    print(f"\n🎯 DECISION: {rec['decision']}")
    print(f"📈 CONFIDENCE: {rec['confidence']}")
    print("\nKEY REASONS:")
    for reason in rec['key_reasons']:
        print(f"  • {reason}")


def test_moderate_market():
    """Test CAUTION recommendation scenario"""
    print("\n" + "="*60)
    print("TEST 2: MODERATE MARKET - Should recommend CAUTION")
    print("="*60)

    analyzer = FeasibilityAnalyzer()

    # Moderate demographics
    demographics = {
        'population': 45000,  # 3 points
        'income': 58000,      # 3 points
        'growth': 1.5,        # 3 points
        'renter_pct': 35,     # 3 points
        'age_pct': 38         # 3 points
    }  # Total: 15/25

    # Moderate supply
    supply = {
        'sf_per_capita': 6.5,      # 4 points
        'occupancy': 83,           # 4 points
        'absorption_trend': 'Moderate', # 3 points
        'pipeline': 1.2            # 2 points
    }  # Total: 13/25

    # Fair site
    site = {
        'visibility': 'Good',      # 5 points
        'access': 'Fair',          # 3 points
        'zoning': 'Conditional',   # 4 points
        'size': 'Adequate'         # 4 points
    }  # Total: 16/25

    # Moderate competition
    competitor = {
        'count': 5,              # 3 points
        'quality': 'Average',    # 3 points
        'pricing': 'At Market'   # 3 points
    }  # Total: 9/15

    # Moderate economy
    economic = {
        'unemployment': 4.8,          # 3 points
        'business_growth': 'Moderate', # 2 points
        'stability': 'Moderate'       # 2 points
    }  # Total: 7/10

    # Run analysis
    market = analyzer.analyze_market(demographics, supply, site, competitor, economic)
    print(f"\n📊 Market Score: {market['total']}/100")

    financials = analyzer.analyze_financials(
        land_cost=800_000,
        construction_cost_psf=42,
        rentable_sqft=55000,
        avg_rent_psf=1.10
    )

    print(f"💰 Yield on Cost: {financials['yield_on_cost']:.1f}%")
    print(f"💰 Equity Multiple: {financials['equity_multiple']:.1f}x")

    rec = analyzer.get_recommendation()
    print(f"\n🎯 DECISION: {rec['decision']}")
    print(f"📈 CONFIDENCE: {rec['confidence']}")
    print("\nKEY REASONS:")
    for reason in rec['key_reasons']:
        print(f"  • {reason}")


def test_weak_market():
    """Test PASS recommendation scenario"""
    print("\n" + "="*60)
    print("TEST 3: WEAK MARKET - Should recommend PASS")
    print("="*60)

    analyzer = FeasibilityAnalyzer()

    # Weak demographics
    demographics = {
        'population': 22000,  # 1 point
        'income': 38000,      # 1 point
        'growth': 0.3,        # 1 point
        'renter_pct': 18,     # 1 point
        'age_pct': 28         # 1 point
    }  # Total: 5/25

    # Oversupplied
    supply = {
        'sf_per_capita': 9.2,      # 0 points
        'occupancy': 72,           # 0 points
        'absorption_trend': 'Weak', # 2 points
        'pipeline': 2.5            # 0 points
    }  # Total: 2/25

    # Poor site
    site = {
        'visibility': 'Fair',           # 3 points
        'access': 'Poor',               # 1 point
        'zoning': 'Requires Variance',  # 2 points
        'size': 'Marginal'              # 2 points
    }  # Total: 8/25

    # Heavy competition
    competitor = {
        'count': 9,                  # 1 point
        'quality': 'Modern/Strong',  # 1 point
        'pricing': 'Below Market'    # 1 point
    }  # Total: 3/15

    # Weak economy
    economic = {
        'unemployment': 7.2,       # 1 point
        'business_growth': 'Weak',  # 1 point
        'stability': 'Volatile'    # 1 point
    }  # Total: 3/10

    # Run analysis
    market = analyzer.analyze_market(demographics, supply, site, competitor, economic)
    print(f"\n📊 Market Score: {market['total']}/100")

    financials = analyzer.analyze_financials(
        land_cost=600_000,
        construction_cost_psf=38,
        rentable_sqft=45000,
        avg_rent_psf=0.85
    )

    print(f"💰 Yield on Cost: {financials['yield_on_cost']:.1f}%")
    print(f"💰 Equity Multiple: {financials['equity_multiple']:.1f}x")

    rec = analyzer.get_recommendation()
    print(f"\n🎯 DECISION: {rec['decision']}")
    print(f"📈 CONFIDENCE: {rec['confidence']}")
    print("\nKEY REASONS:")
    for reason in rec['key_reasons']:
        print(f"  • {reason}")


if __name__ == "__main__":
    test_strong_market()
    test_moderate_market()
    test_weak_market()

    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60)
