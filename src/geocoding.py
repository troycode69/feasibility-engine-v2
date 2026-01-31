"""
Geocoding utilities for address-to-coordinates conversion
Uses ArcGIS geocoder (free, reliable, no API key required)
"""
from typing import Optional, Tuple
from geopy.geocoders import ArcGIS


# Initialize ArcGIS geocoder (free, reliable, no rate limits)
_geolocator = None
_geocode_cache = {}  # In-memory cache for session

def _get_geolocator():
    """Get or create ArcGIS geolocator instance"""
    global _geolocator
    if _geolocator is None:
        _geolocator = ArcGIS(timeout=10)
    return _geolocator


def get_coordinates(address: str) -> Optional[Tuple[float, float]]:
    """
    Get lat/lon coordinates for an address using ArcGIS geocoder.
    Results are cached in memory to avoid repeated API calls.

    Args:
        address: Street address to geocode

    Returns:
        Tuple of (latitude, longitude) or None if geocoding fails
    """
    # Check cache first
    if address in _geocode_cache:
        return _geocode_cache[address]

    try:
        geolocator = _get_geolocator()
        location = geolocator.geocode(address)

        if location:
            result = (location.latitude, location.longitude)
            _geocode_cache[address] = result  # Cache the result
            return result

        _geocode_cache[address] = None  # Cache negative results too
        return None

    except Exception as e:
        print(f"Geocoding failed for '{address}': {e}")
        _geocode_cache[address] = None  # Cache the failure
        return None


def get_coordinates_rate_limited(address: str) -> Optional[Tuple[float, float]]:
    """
    Same as get_coordinates (ArcGIS has no rate limits).
    Kept for backward compatibility.
    """
    return get_coordinates(address)
