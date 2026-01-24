"""
Rate Data Merger
Combines TractiQ and scraper rate data by unit size and climate control
"""

from typing import Dict, List, Optional
from collections import defaultdict
import statistics


def extract_unit_size(size_str: str) -> Optional[str]:
    """
    Normalize unit size strings to standard format.

    Examples:
        "5x5" -> "5x5"
        "5 x 5" -> "5x5"
        "rate_5x5" -> "5x5"
        "5X5" -> "5x5"
    """
    if not size_str:
        return None

    # Remove common prefixes
    size_str = size_str.replace('rate_', '').replace('Rate_', '')

    # Normalize spacing and case
    size_str = size_str.lower().replace(' ', '').strip()

    # Check if it matches pattern like "5x5", "10x10", etc.
    if 'x' in size_str:
        parts = size_str.split('x')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return f"{parts[0]}x{parts[1]}"

    return None


def parse_rate(rate_value) -> Optional[float]:
    """
    Parse rate from various formats to float.

    Examples:
        "$150" -> 150.0
        "150.00" -> 150.0
        150 -> 150.0
        "Call for Rate" -> None
    """
    if rate_value is None:
        return None

    if isinstance(rate_value, (int, float)):
        return float(rate_value) if rate_value > 0 else None

    # String processing
    rate_str = str(rate_value).strip()

    # Check for non-numeric indicators
    if any(word in rate_str.lower() for word in ['call', 'contact', 'n/a', 'none', '-']):
        return None

    # Remove currency symbols and commas
    rate_str = rate_str.replace('$', '').replace(',', '').strip()

    try:
        rate = float(rate_str)
        return rate if rate > 0 else None
    except ValueError:
        return None


def merge_competitor_rates(tractiq_data: Dict, scraper_competitors: List[Dict]) -> Dict:
    """
    Merge rate data from TractiQ uploads and scraper results.

    Args:
        tractiq_data: Cached TractiQ data dict with competitors list
        scraper_competitors: List of competitor dicts from scraper

    Returns:
        Dict with structure:
        {
            "by_unit_size": {
                "5x5": {
                    "climate": {"min": X, "max": Y, "avg": Z, "median": M, "count": N, "rates": [...]},
                    "non_climate": {...}
                },
                ...
            },
            "all_competitors": [...],  # Merged list with duplicates removed
            "summary": {
                "total_competitors": N,
                "tractiq_count": X,
                "scraper_count": Y,
                "unit_sizes": [...],
                "rate_range": {"min": X, "max": Y}
            }
        }
    """
    # Standard unit sizes to track
    standard_sizes = ["5x5", "5x10", "10x10", "10x15", "10x20", "10x30"]

    # Initialize data structures
    rates_by_size = {
        size: {
            "climate": [],
            "non_climate": []
        } for size in standard_sizes
    }

    all_competitors = []
    seen_names = set()  # For deduplication

    # Process TractiQ data
    tractiq_count = 0
    if tractiq_data:
        for pdf_data in tractiq_data.values():
            competitors = pdf_data.get('competitors', [])
            for comp in competitors:
                name = comp.get('name', '').lower().strip()

                # Skip if duplicate
                if name in seen_names:
                    continue

                seen_names.add(name)
                tractiq_count += 1

                # Extract rates by unit size
                for key, value in comp.items():
                    if key.startswith('rate_'):
                        unit_size = extract_unit_size(key)
                        rate = parse_rate(value)

                        if unit_size in standard_sizes and rate:
                            # Determine climate control (TractiQ data might have this info)
                            climate_type = "climate" if comp.get(f'{key}_climate', False) else "non_climate"
                            rates_by_size[unit_size][climate_type].append(rate)

                # Add to all competitors
                all_competitors.append({
                    **comp,
                    "source": "TractiQ"
                })

    # Process scraper data
    scraper_count = 0
    for comp in scraper_competitors:
        name = comp.get('Name', '').lower().strip()

        # Skip if duplicate
        if name in seen_names:
            continue

        seen_names.add(name)
        scraper_count += 1

        # Extract rate (scrapers usually have a single rate field)
        rate = parse_rate(comp.get('Rate'))

        # Try to infer unit size from additional fields
        # This is basic - might need enhancement based on scraper output
        unit_size = extract_unit_size(comp.get('UnitSize', '10x10'))

        if unit_size and unit_size in standard_sizes and rate:
            # Default to non-climate for scraper data unless specified
            climate_type = "climate" if comp.get('Climate', False) else "non_climate"
            rates_by_size[unit_size][climate_type].append(rate)

        # Add to all competitors
        all_competitors.append({
            **comp,
            "source": "Scraper"
        })

    # Calculate statistics for each unit size and climate type
    by_unit_size = {}
    all_rates = []

    for size in standard_sizes:
        by_unit_size[size] = {}

        for climate_type in ["climate", "non_climate"]:
            rates = rates_by_size[size][climate_type]

            if rates:
                all_rates.extend(rates)
                by_unit_size[size][climate_type] = {
                    "min": min(rates),
                    "max": max(rates),
                    "avg": statistics.mean(rates),
                    "median": statistics.median(rates),
                    "count": len(rates),
                    "rates": sorted(rates)
                }
            else:
                by_unit_size[size][climate_type] = {
                    "min": None,
                    "max": None,
                    "avg": None,
                    "median": None,
                    "count": 0,
                    "rates": []
                }

    # Build summary
    summary = {
        "total_competitors": len(all_competitors),
        "tractiq_count": tractiq_count,
        "scraper_count": scraper_count,
        "unit_sizes": standard_sizes,
        "rate_range": {
            "min": min(all_rates) if all_rates else None,
            "max": max(all_rates) if all_rates else None
        }
    }

    return {
        "by_unit_size": by_unit_size,
        "all_competitors": all_competitors,
        "summary": summary
    }
