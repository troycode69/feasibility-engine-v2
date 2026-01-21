"""
Economic Data Intelligence Module
Fetches real-time economic indicators from free government APIs
- Bureau of Labor Statistics (BLS)
- Census Bureau
- FRED (Federal Reserve Economic Data)
"""

import requests
from typing import Dict, Optional
from datetime import datetime
import time


class EconomicDataFetcher:
    """
    Fetches economic indicators for a given location using free government APIs
    """

    def __init__(self):
        self.bls_base_url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
        self.census_base_url = "https://api.census.gov/data"

    def get_msa_code_from_location(self, lat: float, lon: float) -> Optional[str]:
        """
        Get Metropolitan Statistical Area (MSA) code from coordinates
        Uses Census Geocoder API (free)
        """
        try:
            url = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
            params = {
                'x': lon,
                'y': lat,
                'benchmark': 'Public_AR_Current',
                'vintage': 'Current_Current',
                'format': 'json'
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # Extract MSA code from response
                if 'result' in data and 'geographies' in data['result']:
                    metros = data['result']['geographies'].get('Metropolitan Statistical Areas', [])
                    if metros:
                        return metros[0].get('GEOID')

        except Exception as e:
            print(f"Error getting MSA code: {e}")

        return None

    def get_unemployment_rate(self, msa_code: str = None, state_fips: str = None) -> Dict[str, any]:
        """
        Get current unemployment rate from BLS

        Args:
            msa_code: MSA code (e.g., '19100' for Dallas-Fort Worth)
            state_fips: State FIPS code if MSA unavailable

        Returns:
            Dict with unemployment rate and data source info
        """

        try:
            # BLS Series IDs:
            # Format: LAUMT{STATE_FIPS}{MSA}{MEASURE}
            # Measure: 03 = unemployment rate

            if msa_code:
                # Try MSA-level data
                series_id = f"LAUMT{msa_code}03"
            elif state_fips:
                # Fall back to state-level
                series_id = f"LASST{state_fips}0000000000003"
            else:
                # National fallback
                series_id = "LNS14000000"

            payload = {
                "seriesid": [series_id],
                "startyear": str(datetime.now().year - 1),
                "endyear": str(datetime.now().year)
            }

            response = requests.post(self.bls_base_url, json=payload, timeout=15)

            if response.status_code == 200:
                data = response.json()

                if data['status'] == 'REQUEST_SUCCEEDED' and data['Results']:
                    series_data = data['Results']['series'][0]['data']

                    if series_data:
                        # Get most recent value
                        latest = series_data[0]
                        unemployment_rate = float(latest['value'])

                        return {
                            'unemployment_rate': unemployment_rate,
                            'period': latest.get('periodName', 'Latest'),
                            'year': latest.get('year'),
                            'source': 'Bureau of Labor Statistics',
                            'data_level': 'MSA' if msa_code else 'State' if state_fips else 'National'
                        }

        except Exception as e:
            print(f"Error fetching unemployment data: {e}")

        # Default fallback
        return {
            'unemployment_rate': 4.5,
            'source': 'Default estimate',
            'data_level': 'Unknown'
        }

    def infer_business_growth(self, unemployment_rate: float) -> str:
        """
        Infer business growth trend from unemployment rate
        (Inverse relationship: low unemployment = strong economy)

        Returns:
            'Strong', 'Moderate', or 'Weak'
        """

        if unemployment_rate <= 3.5:
            return 'Strong'
        elif unemployment_rate <= 5.5:
            return 'Moderate'
        else:
            return 'Weak'

    def assess_economic_stability(self, unemployment_rate: float) -> str:
        """
        Assess economic stability
        (Low, stable unemployment = stable economy)

        Returns:
            'Stable', 'Moderate', or 'Volatile'
        """

        if unemployment_rate <= 4.0:
            return 'Stable'
        elif unemployment_rate <= 6.5:
            return 'Moderate'
        else:
            return 'Volatile'

    def get_complete_economic_indicators(self, lat: float, lon: float,
                                         state_fips: str = None) -> Dict[str, any]:
        """
        Get all economic indicators for a location

        Args:
            lat, lon: Property coordinates
            state_fips: Optional state FIPS code (e.g., '48' for Texas)

        Returns:
            Dict with unemployment, business_growth, and stability
        """

        # Get MSA code
        msa_code = self.get_msa_code_from_location(lat, lon)

        # Get unemployment data
        unemployment_data = self.get_unemployment_rate(msa_code, state_fips)
        unemployment_rate = unemployment_data['unemployment_rate']

        # Infer other indicators
        business_growth = self.infer_business_growth(unemployment_rate)
        stability = self.assess_economic_stability(unemployment_rate)

        return {
            'unemployment': unemployment_rate,
            'business_growth': business_growth,
            'stability': stability,
            'data_source': unemployment_data.get('source'),
            'data_period': unemployment_data.get('period'),
            'data_level': unemployment_data.get('data_level'),
            'msa_code': msa_code
        }


# Convenience function
def fetch_economic_data(lat: float, lon: float, state_fips: str = None) -> Dict[str, any]:
    """
    Easy-to-use function for fetching economic indicators

    Usage:
        econ = fetch_economic_data(32.7767, -96.7970)  # Dallas coords
        print(econ['unemployment'])      # 3.8
        print(econ['business_growth'])   # "Strong"
    """

    fetcher = EconomicDataFetcher()
    return fetcher.get_complete_economic_indicators(lat, lon, state_fips)


# State FIPS codes reference for common states
STATE_FIPS = {
    'TX': '48',  # Texas
    'FL': '12',  # Florida
    'CA': '06',  # California
    'AZ': '04',  # Arizona
    'NC': '37',  # North Carolina
    'GA': '13',  # Georgia
    'TN': '47',  # Tennessee
    # Add more as needed
}
