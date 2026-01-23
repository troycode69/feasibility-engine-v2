"""
Industry Benchmarks Database for Self-Storage Feasibility Analysis

This module contains industry-standard benchmarks, occupancy curves, expense ratios,
construction costs, and other reference data used in the scoring and financial analysis.

Data sources:
- Self-Storage Almanac (industry averages)
- Radius+ (construction cost data)
- FRED (Federal Reserve Economic Data)
- STR (Self-Storage Market Insights)
"""

from typing import Dict, List, Tuple
from datetime import datetime

# ============================================================================
# OCCUPANCY STABILIZATION CURVES
# ============================================================================

# Standard occupancy ramp-up for new facilities (by month)
# Based on industry averages for well-located, properly marketed facilities
OCCUPANCY_CURVE_STANDARD = {
    "months": list(range(0, 37)),  # 0-36 months (3 years)
    "occupancy_pct": [
        0, 8, 15, 22, 28, 34, 40, 45, 50, 55, 60, 64,  # Year 1: Months 0-11
        68, 71, 74, 76, 78, 80, 82, 83, 84, 85, 86, 87,  # Year 2: Months 12-23
        88, 89, 90, 91, 91, 92, 92, 93, 93, 93, 94, 94, 95  # Year 3: Months 24-36
    ],
    "stabilization_month": 36,
    "stabilized_occupancy": 95,
    "break_even_occupancy": 60  # Typical break-even point
}

# Aggressive occupancy curve (strong market, excellent location, strong marketing)
OCCUPANCY_CURVE_AGGRESSIVE = {
    "months": list(range(0, 25)),  # 0-24 months (2 years)
    "occupancy_pct": [
        0, 12, 20, 28, 35, 42, 48, 54, 60, 65, 70, 74,  # Year 1
        78, 81, 84, 86, 88, 90, 91, 92, 93, 94, 95, 96, 97  # Year 2
    ],
    "stabilization_month": 24,
    "stabilized_occupancy": 97,
    "break_even_occupancy": 55
}

# Conservative occupancy curve (weaker market, challenged location, or high competition)
OCCUPANCY_CURVE_CONSERVATIVE = {
    "months": list(range(0, 49)),  # 0-48 months (4 years)
    "occupancy_pct": [
        0, 5, 10, 14, 18, 22, 26, 30, 34, 37, 40, 43,  # Year 1
        46, 49, 52, 55, 58, 60, 62, 64, 66, 68, 70, 72,  # Year 2
        74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85,  # Year 3
        86, 87, 87, 88, 88, 89, 89, 90, 90, 91, 91, 92, 92  # Year 4
    ],
    "stabilization_month": 48,
    "stabilized_occupancy": 92,
    "break_even_occupancy": 65
}


# ============================================================================
# OPERATING EXPENSE RATIOS
# ============================================================================

# Operating expenses as % of Gross Potential Revenue (GPR)
# Industry benchmarks by facility size
OPERATING_EXPENSE_RATIOS = {
    "small": {  # < 40,000 NRSF
        "property_taxes": 0.08,  # 8% of GPR
        "insurance": 0.02,
        "utilities": 0.04,
        "management_fee": 0.06,
        "on_site_labor": 0.12,
        "marketing": 0.05,
        "maintenance_repairs": 0.03,
        "administrative": 0.02,
        "total": 0.42  # 42% total operating expenses
    },
    "medium": {  # 40,000 - 80,000 NRSF
        "property_taxes": 0.07,
        "insurance": 0.015,
        "utilities": 0.035,
        "management_fee": 0.06,
        "on_site_labor": 0.10,
        "marketing": 0.04,
        "maintenance_repairs": 0.025,
        "administrative": 0.015,
        "total": 0.36  # 36% total
    },
    "large": {  # > 80,000 NRSF
        "property_taxes": 0.06,
        "insurance": 0.012,
        "utilities": 0.03,
        "management_fee": 0.05,
        "on_site_labor": 0.08,
        "marketing": 0.035,
        "maintenance_repairs": 0.02,
        "administrative": 0.012,
        "total": 0.30  # 30% total (economies of scale)
    }
}


# ============================================================================
# CONSTRUCTION COSTS
# ============================================================================

# Base construction costs per NRSF (Net Rentable Square Foot)
# Updated Q4 2025 estimates
BASE_CONSTRUCTION_COSTS = {
    "climate_controlled": {
        "low": 85,  # $/NRSF - Basic construction, suburban location
        "mid": 105,  # $/NRSF - Standard quality
        "high": 135  # $/NRSF - High-end finishes, urban location
    },
    "non_climate_controlled": {
        "low": 55,
        "mid": 70,
        "high": 90
    },
    "mixed": {  # Typical mix: 70% climate, 30% non-climate
        "low": 76,
        "mid": 95,
        "high": 122
    }
}

# Regional cost multipliers (base = 1.0 for Southeast)
REGIONAL_COST_MULTIPLIERS = {
    "northeast": 1.25,  # NY, NJ, CT, MA, PA, etc.
    "mid_atlantic": 1.15,  # MD, VA, DC, DE
    "southeast": 1.0,  # Base region: NC, SC, GA, FL, TN, AL, MS
    "midwest": 1.05,  # OH, IN, IL, MI, WI, MN, IA, MO
    "southwest": 1.08,  # TX, OK, AR, LA, NM
    "mountain": 1.12,  # CO, UT, AZ, NV, ID, MT, WY
    "west_coast": 1.35,  # CA, OR, WA
    "pacific": 1.45  # HI, AK
}

# State-specific mappings for regional multipliers
STATE_TO_REGION = {
    # Northeast
    "NY": "northeast", "NJ": "northeast", "CT": "northeast", "MA": "northeast",
    "PA": "northeast", "RI": "northeast", "VT": "northeast", "NH": "northeast", "ME": "northeast",
    # Mid-Atlantic
    "MD": "mid_atlantic", "VA": "mid_atlantic", "DC": "mid_atlantic", "DE": "mid_atlantic", "WV": "mid_atlantic",
    # Southeast
    "NC": "southeast", "SC": "southeast", "GA": "southeast", "FL": "southeast",
    "TN": "southeast", "AL": "southeast", "MS": "southeast", "KY": "southeast",
    # Midwest
    "OH": "midwest", "IN": "midwest", "IL": "midwest", "MI": "midwest", "WI": "midwest",
    "MN": "midwest", "IA": "midwest", "MO": "midwest", "KS": "midwest", "NE": "midwest",
    "SD": "midwest", "ND": "midwest",
    # Southwest
    "TX": "southwest", "OK": "southwest", "AR": "southwest", "LA": "southwest", "NM": "southwest",
    # Mountain
    "CO": "mountain", "UT": "mountain", "AZ": "mountain", "NV": "mountain",
    "ID": "mountain", "MT": "mountain", "WY": "mountain",
    # West Coast
    "CA": "west_coast", "OR": "west_coast", "WA": "west_coast",
    # Pacific
    "HI": "pacific", "AK": "pacific"
}

# Soft costs as % of hard costs
SOFT_COST_FACTORS = {
    "architectural_engineering": 0.05,
    "permits_fees": 0.03,
    "legal_closing": 0.02,
    "financing_costs": 0.025,
    "contingency": 0.10,
    "total": 0.225  # 22.5% of hard costs
}


# ============================================================================
# UNIT MIX BENCHMARKS
# ============================================================================

# Industry standard unit mix percentages (% of total NRSF)
STANDARD_UNIT_MIX = {
    "5x5": {"pct_of_nrsf": 0.10, "avg_rate_psf": 2.80},
    "5x10": {"pct_of_nrsf": 0.20, "avg_rate_psf": 2.20},
    "10x10": {"pct_of_nrsf": 0.25, "avg_rate_psf": 1.60},
    "10x15": {"pct_of_nrsf": 0.15, "avg_rate_psf": 1.30},
    "10x20": {"pct_of_nrsf": 0.15, "avg_rate_psf": 1.10},
    "10x25": {"pct_of_nrsf": 0.10, "avg_rate_psf": 0.95},
    "10x30": {"pct_of_nrsf": 0.05, "avg_rate_psf": 0.85}
}


# ============================================================================
# FINANCING BENCHMARKS
# ============================================================================

# Typical loan terms for self-storage (as of Q4 2025)
FINANCING_TERMS = {
    "conventional": {
        "ltc_max": 0.75,  # Loan-to-cost: 75%
        "ltv_max": 0.80,  # Loan-to-value: 80%
        "min_dscr": 1.25,  # Debt Service Coverage Ratio
        "typical_rate_spread": 2.50,  # Spread over 10-year Treasury
        "amortization_years": 25,
        "term_years": 10  # Typical balloon at year 10
    },
    "sba_504": {
        "ltc_max": 0.90,  # 90% LTC possible with SBA
        "typical_rate": 6.25,  # Fixed rate
        "amortization_years": 25,
        "term_years": 25  # Fully amortizing
    },
    "construction": {
        "ltc_max": 0.75,
        "typical_rate_spread": 3.00,  # Higher spread during construction
        "term_months": 24,  # Typical 2-year construction loan
        "interest_reserve": 0.08  # 8% of loan amount reserved for interest
    }
}


# ============================================================================
# MARKET METRICS & SCORING THRESHOLDS
# ============================================================================

# Demographics scoring thresholds (for 25-point category)
DEMOGRAPHICS_THRESHOLDS = {
    "population_3mi": {
        "excellent": (75000, float('inf'), 5),  # >75k = 5 points
        "good": (50000, 75000, 4),
        "fair": (30000, 50000, 3),
        "weak": (20000, 30000, 2),
        "poor": (0, 20000, 1)
    },
    "growth_rate": {  # Annual population growth %
        "excellent": (2.0, float('inf'), 5),  # >2% = 5 points
        "good": (1.0, 2.0, 4),
        "fair": (0.5, 1.0, 3),
        "weak": (0, 0.5, 2),
        "poor": (-float('inf'), 0, 1)  # Negative growth = 1 point
    },
    "median_income": {
        "excellent": (90000, float('inf'), 5),
        "good": (75000, 90000, 4),
        "fair": (60000, 75000, 3),
        "weak": (45000, 60000, 2),
        "poor": (0, 45000, 1)
    },
    "renter_occupied_pct": {  # % of housing units renter-occupied
        "excellent": (40, 100, 5),  # >40% = 5 points
        "good": (35, 40, 4),
        "fair": (30, 35, 3),
        "weak": (25, 30, 2),
        "poor": (0, 25, 1)
    },
    "age_demographics": {  # Median age (prime storage users: 30-45)
        "excellent": (30, 45, 5),
        "good": (25, 50, 4),
        "fair": (20, 55, 3),
        "weak": (18, 60, 2),
        "poor": (0, 100, 1)  # Very young or very old = 1 point
    }
}

# Supply/Demand scoring thresholds (for 25-point category)
SUPPLY_DEMAND_THRESHOLDS = {
    "sf_per_capita": {  # Industry benchmark: 5-7 SF per capita is balanced
        "excellent": (0, 4.0, 5),  # Undersupplied = excellent
        "good": (4.0, 5.5, 4),
        "fair": (5.5, 7.0, 3),  # Balanced market
        "weak": (7.0, 9.0, 2),
        "poor": (9.0, float('inf'), 1)  # Oversupplied
    },
    "existing_occupancy_avg": {  # Average occupancy of existing competitors
        "excellent": (90, 100, 5),
        "good": (85, 90, 4),
        "fair": (80, 85, 3),
        "weak": (75, 80, 2),
        "poor": (0, 75, 1)
    },
    "distance_to_nearest": {  # Miles to nearest competitor
        "excellent": (3.0, float('inf'), 5),  # >3 miles = excellent
        "good": (2.0, 3.0, 4),
        "fair": (1.0, 2.0, 3),
        "weak": (0.5, 1.0, 2),
        "poor": (0, 0.5, 1)  # <0.5 miles = very competitive
    },
    "market_rate_trend": {  # % change in average market rates (past 12 months)
        "excellent": (3.0, float('inf'), 5),  # Rates increasing >3%
        "good": (1.0, 3.0, 4),
        "fair": (-1.0, 1.0, 3),  # Flat rates
        "weak": (-3.0, -1.0, 2),
        "poor": (-float('inf'), -3.0, 1)  # Rates declining
    },
    "development_pipeline": {  # Number of facilities in planning/construction (5-mile)
        "excellent": (0, 1, 5),  # No competition coming
        "good": (1, 2, 4),
        "fair": (2, 3, 3),
        "weak": (3, 4, 2),
        "poor": (4, float('inf'), 1)  # Heavy development
    }
}

# Site Attributes scoring thresholds (for 25-point category)
SITE_ATTRIBUTES_THRESHOLDS = {
    "visibility": {  # Subjective: 1-5 scale
        "excellent": (5, 5, 5),
        "good": (4, 4, 4),
        "fair": (3, 3, 3),
        "weak": (2, 2, 2),
        "poor": (1, 1, 1)
    },
    "traffic_count": {  # Average Daily Traffic (ADT)
        "excellent": (20000, float('inf'), 5),
        "good": (15000, 20000, 4),
        "fair": (10000, 15000, 3),
        "weak": (5000, 10000, 2),
        "poor": (0, 5000, 1)
    },
    "access_quality": {  # Ingress/egress: 1-5 scale
        "excellent": (5, 5, 5),
        "good": (4, 4, 4),
        "fair": (3, 3, 3),
        "weak": (2, 2, 2),
        "poor": (1, 1, 1)
    },
    "lot_size_adequacy": {  # Lot size vs. planned NRSF ratio
        "excellent": (4.0, float('inf'), 5),  # >4:1 land-to-building
        "good": (3.5, 4.0, 4),
        "fair": (3.0, 3.5, 3),
        "weak": (2.5, 3.0, 2),
        "poor": (0, 2.5, 1)
    },
    "zoning_status": {  # 1=Approved, 2=Conditional, 3=Needs variance, 4=Not allowed
        "excellent": (1, 1, 5),
        "good": (2, 2, 4),
        "fair": (3, 3, 2),
        "poor": (4, 4, 1)
    }
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_occupancy_curve(market_strength: str = "standard") -> Dict:
    """
    Returns the appropriate occupancy curve based on market strength assessment.

    Args:
        market_strength: "aggressive", "standard", or "conservative"

    Returns:
        Dictionary with months, occupancy_pct, and stabilization info
    """
    curves = {
        "aggressive": OCCUPANCY_CURVE_AGGRESSIVE,
        "standard": OCCUPANCY_CURVE_STANDARD,
        "conservative": OCCUPANCY_CURVE_CONSERVATIVE
    }
    return curves.get(market_strength.lower(), OCCUPANCY_CURVE_STANDARD)


def get_expense_ratio(nrsf: int) -> Dict[str, float]:
    """
    Returns operating expense ratios based on facility size.

    Args:
        nrsf: Net Rentable Square Feet

    Returns:
        Dictionary of expense categories and their % of GPR
    """
    if nrsf < 40000:
        return OPERATING_EXPENSE_RATIOS["small"]
    elif nrsf < 80000:
        return OPERATING_EXPENSE_RATIOS["medium"]
    else:
        return OPERATING_EXPENSE_RATIOS["large"]


def calculate_construction_cost(nrsf: int, state: str, quality: str = "mid",
                                climate_mix: str = "mixed") -> Dict[str, float]:
    """
    Calculates total construction cost including regional adjustments.

    Args:
        nrsf: Net Rentable Square Feet
        state: Two-letter state code (e.g., "TN", "NY")
        quality: "low", "mid", or "high"
        climate_mix: "climate_controlled", "non_climate_controlled", or "mixed"

    Returns:
        Dictionary with hard_cost, soft_cost, and total_cost
    """
    # Get base cost per SF
    base_cost_psf = BASE_CONSTRUCTION_COSTS[climate_mix][quality]

    # Apply regional multiplier
    region = STATE_TO_REGION.get(state.upper(), "southeast")
    regional_multiplier = REGIONAL_COST_MULTIPLIERS[region]

    adjusted_cost_psf = base_cost_psf * regional_multiplier
    hard_cost = nrsf * adjusted_cost_psf

    # Calculate soft costs
    soft_cost = hard_cost * SOFT_COST_FACTORS["total"]

    total_cost = hard_cost + soft_cost

    return {
        "hard_cost": round(hard_cost, 2),
        "soft_cost": round(soft_cost, 2),
        "total_cost": round(total_cost, 2),
        "cost_per_nrsf": round(total_cost / nrsf, 2),
        "base_cost_psf": base_cost_psf,
        "regional_multiplier": regional_multiplier,
        "region": region
    }


def score_demographic_metric(metric_name: str, value: float) -> Tuple[int, str]:
    """
    Scores a demographic metric based on thresholds.

    Args:
        metric_name: Key from DEMOGRAPHICS_THRESHOLDS
        value: The metric value to score

    Returns:
        Tuple of (points, tier_name)
    """
    if metric_name not in DEMOGRAPHICS_THRESHOLDS:
        return (0, "unknown")

    thresholds = DEMOGRAPHICS_THRESHOLDS[metric_name]

    for tier_name, (min_val, max_val, points) in thresholds.items():
        if min_val <= value < max_val:
            return (points, tier_name)

    return (0, "unknown")


def score_supply_demand_metric(metric_name: str, value: float) -> Tuple[int, str]:
    """Scores a supply/demand metric based on thresholds."""
    if metric_name not in SUPPLY_DEMAND_THRESHOLDS:
        return (0, "unknown")

    thresholds = SUPPLY_DEMAND_THRESHOLDS[metric_name]

    for tier_name, (min_val, max_val, points) in thresholds.items():
        if min_val <= value < max_val:
            return (points, tier_name)

    return (0, "unknown")


def score_site_attribute(metric_name: str, value: float) -> Tuple[int, str]:
    """Scores a site attribute metric based on thresholds."""
    if metric_name not in SITE_ATTRIBUTES_THRESHOLDS:
        return (0, "unknown")

    thresholds = SITE_ATTRIBUTES_THRESHOLDS[metric_name]

    for tier_name, (min_val, max_val, points) in thresholds.items():
        if min_val <= value <= max_val:
            return (points, tier_name)

    return (0, "unknown")


# ============================================================================
# MODULE INFO
# ============================================================================

BENCHMARK_VERSION = "1.0.0"
LAST_UPDATED = "2026-01-23"

if __name__ == "__main__":
    # Test the module
    print(f"Benchmarks Module v{BENCHMARK_VERSION}")
    print(f"Last updated: {LAST_UPDATED}\n")

    # Test construction cost calculation
    print("=== Construction Cost Example ===")
    cost = calculate_construction_cost(60000, "TN", "mid", "mixed")
    print(f"60,000 NRSF facility in Tennessee:")
    print(f"  Hard Cost: ${cost['hard_cost']:,.0f}")
    print(f"  Soft Cost: ${cost['soft_cost']:,.0f}")
    print(f"  Total Cost: ${cost['total_cost']:,.0f}")
    print(f"  Cost/NRSF: ${cost['cost_per_nrsf']:.2f}")
    print(f"  Region: {cost['region']} (multiplier: {cost['regional_multiplier']})\n")

    # Test demographic scoring
    print("=== Demographic Scoring Example ===")
    pop_score, pop_tier = score_demographic_metric("population_3mi", 61297)
    print(f"Population 61,297: {pop_score}/5 points ({pop_tier})")

    income_score, income_tier = score_demographic_metric("median_income", 77883)
    print(f"Median Income $77,883: {income_score}/5 points ({income_tier})")

    renter_score, renter_tier = score_demographic_metric("renter_occupied_pct", 46.1)
    print(f"Renter-Occupied 46.1%: {renter_score}/5 points ({renter_tier})\n")

    # Test occupancy curves
    print("=== Occupancy Curve Example ===")
    std_curve = get_occupancy_curve("standard")
    print(f"Standard curve stabilizes at {std_curve['stabilized_occupancy']}% in month {std_curve['stabilization_month']}")
    print(f"Break-even at {std_curve['break_even_occupancy']}% occupancy")
