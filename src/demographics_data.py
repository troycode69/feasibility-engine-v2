"""
Demographics Data Module
Fetches detailed age demographics from Census Bureau ACS API
Eliminates the need for default age percentage estimates
"""

import requests
from typing import Dict, Optional


class DemographicsDataFetcher:
    """
    Fetches detailed demographics from Census Bureau American Community Survey (ACS)
    """

    def __init__(self):
        self.census_base_url = "https://api.census.gov/data"
        self.geocoder_url = "https://geocoding.geo.census.gov/geocoder"

    def get_census_tract_from_location(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Get Census tract information from coordinates
        Uses Census Geocoder API (free, no key required)

        Returns:
            Dict with state, county, tract codes or None
        """
        try:
            url = f"{self.geocoder_url}/geographies/coordinates"
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

                if 'result' in data and 'geographies' in data['result']:
                    # Extract Census Tracts
                    tracts = data['result']['geographies'].get('Census Tracts', [])
                    if tracts:
                        tract = tracts[0]
                        return {
                            'state': tract.get('STATE'),
                            'county': tract.get('COUNTY'),
                            'tract': tract.get('TRACT'),
                            'tract_name': tract.get('NAME')
                        }

        except Exception as e:
            print(f"Error getting census tract: {e}")

        return None

    def get_age_demographics(self, lat: float, lon: float) -> Dict[str, any]:
        """
        Get age demographics from Census ACS API

        Uses Table B01001: Sex by Age
        Calculates percentage of population aged 25-54 (prime storage user demographic)

        Args:
            lat, lon: Property coordinates

        Returns:
            Dict with age_25_54_pct and detailed breakdown
        """

        # Get census tract
        tract_info = self.get_census_tract_from_location(lat, lon)

        if not tract_info:
            return self._get_default_age_demographics()

        try:
            # ACS 5-Year Estimates (most reliable)
            # Table B01001: Sex by Age
            # We need to sum specific age groups

            state = tract_info['state']
            county = tract_info['county']
            tract = tract_info['tract']

            # Build query for age groups
            # B01001_001E = Total population
            # Males 25-29: B01001_011E
            # Males 30-34: B01001_012E
            # Males 35-39: B01001_013E
            # Males 40-44: B01001_014E
            # Males 45-49: B01001_015E
            # Males 50-54: B01001_016E
            # Females 25-29: B01001_035E
            # Females 30-34: B01001_036E
            # Females 35-39: B01001_037E
            # Females 40-44: B01001_038E
            # Females 45-49: B01001_039E
            # Females 50-54: B01001_040E

            variables = [
                'B01001_001E',  # Total
                'B01001_011E', 'B01001_012E', 'B01001_013E', 'B01001_014E', 'B01001_015E', 'B01001_016E',  # Males 25-54
                'B01001_035E', 'B01001_036E', 'B01001_037E', 'B01001_038E', 'B01001_039E', 'B01001_040E'   # Females 25-54
            ]

            url = f"{self.census_base_url}/2022/acs/acs5"
            params = {
                'get': ','.join(variables),
                'for': f'tract:{tract}',
                'in': f'state:{state} county:{county}'
            }

            response = requests.get(url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()

                if len(data) > 1:  # First row is headers
                    values = data[1]

                    # Parse values (skip header row)
                    total_pop = int(values[0]) if values[0] and values[0] != 'null' else 0

                    if total_pop > 0:
                        # Sum all age 25-54 categories
                        age_25_54_count = sum(
                            int(v) if v and v != 'null' else 0
                            for v in values[1:13]  # All the age group variables
                        )

                        age_25_54_pct = (age_25_54_count / total_pop) * 100

                        return {
                            'age_25_54_pct': round(age_25_54_pct, 1),
                            'age_25_54_count': age_25_54_count,
                            'total_population': total_pop,
                            'data_source': 'Census ACS 5-Year (2022)',
                            'data_level': 'Census Tract',
                            'tract_info': tract_info
                        }

        except Exception as e:
            print(f"Error fetching age demographics: {e}")

        # Fallback to defaults
        return self._get_default_age_demographics()

    def _get_default_age_demographics(self) -> Dict[str, any]:
        """Return conservative defaults when API unavailable"""
        return {
            'age_25_54_pct': 40.0,
            'data_source': 'Default estimate',
            'data_level': 'National average',
            'note': 'Census data unavailable - using national average'
        }

    def get_complete_demographics(self, lat: float, lon: float) -> Dict[str, any]:
        """
        Get all demographic indicators for a location
        Future: Can expand to include income, population, etc. from ACS

        Args:
            lat, lon: Property coordinates

        Returns:
            Dict with all demographic indicators
        """

        age_data = self.get_age_demographics(lat, lon)

        # Future enhancement: Add more demographic pulls here
        # - Median income (B19013_001E)
        # - Renter occupied % (B25003_003E / B25003_001E)
        # - Population growth (compare ACS years)

        return {
            'age_demographics': age_data,
            # Future: 'income_data': income_data,
            # Future: 'housing_data': housing_data,
        }


# Convenience function
def fetch_demographics_data(lat: float, lon: float) -> Dict[str, any]:
    """
    Easy-to-use function for fetching demographic data

    Usage:
        demo = fetch_demographics_data(32.7767, -96.7970)  # Dallas coords
        print(demo['age_25_54_pct'])  # 42.3
    """

    fetcher = DemographicsDataFetcher()
    result = fetcher.get_age_demographics(lat, lon)
    return result
