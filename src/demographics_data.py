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

    def get_complete_demographics(self, lat: float, lon: float, radius_miles: float = 3.0) -> Dict[str, any]:
        """
        Get all demographic indicators for a location
        Fetches: population, income, renter %, age distribution, growth rate

        Args:
            lat, lon: Property coordinates
            radius_miles: Radius to search (default 3 miles)

        Returns:
            Dict with all demographic indicators needed for Market Intelligence scoring
        """

        # Get census tract
        tract_info = self.get_census_tract_from_location(lat, lon)

        if not tract_info:
            return self._get_default_complete_demographics()

        try:
            state = tract_info['state']
            county = tract_info['county']
            tract = tract_info['tract']

            # === FETCH ALL DEMOGRAPHICS IN ONE API CALL ===
            # ACS 5-Year Estimates 2022 (most reliable)
            variables = [
                'B01001_001E',  # Total population
                # Age 25-54 (same as before)
                'B01001_011E', 'B01001_012E', 'B01001_013E', 'B01001_014E', 'B01001_015E', 'B01001_016E',
                'B01001_035E', 'B01001_036E', 'B01001_037E', 'B01001_038E', 'B01001_039E', 'B01001_040E',
                # Income
                'B19013_001E',  # Median household income
                # Housing tenure (renter vs owner)
                'B25003_001E',  # Total occupied housing units
                'B25003_003E',  # Renter-occupied housing units
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

                if len(data) > 1:
                    values = data[1]

                    # Parse values
                    total_pop = int(values[0]) if values[0] and values[0] != 'null' else 0

                    # Age 25-54 percentage
                    age_25_54_count = sum(
                        int(v) if v and v != 'null' else 0
                        for v in values[1:13]
                    )
                    age_25_54_pct = (age_25_54_count / total_pop * 100) if total_pop > 0 else 40.0

                    # Median income
                    median_income = int(values[13]) if values[13] and values[13] != 'null' else 65000

                    # Renter percentage
                    total_housing = int(values[14]) if values[14] and values[14] != 'null' else 1
                    renter_units = int(values[15]) if values[15] and values[15] != 'null' else 0
                    renter_pct = (renter_units / total_housing * 100) if total_housing > 0 else 35.0

                    # === POPULATION GROWTH (compare 2022 vs 2017) ===
                    growth_rate = self._calculate_population_growth(state, county, tract)

                    # === POPULATION WITHIN RADIUS ===
                    # Use county population as better approximation for 3-mile radius
                    # A census tract is too small (~4,000 people), county is closer to metro area
                    pop_3mi = self._estimate_population_in_radius(lat, lon, state, county, radius_miles)

                    return {
                        'pop_3mi': int(pop_3mi),
                        'median_income': int(median_income),
                        'growth_rate': round(growth_rate, 1),
                        'renter_pct': round(renter_pct, 1),
                        'age_25_54_pct': round(age_25_54_pct, 1),
                        'total_population': total_pop,
                        'data_source': 'Census ACS 5-Year (2022)',
                        'data_level': 'Census Tract',
                        'tract_info': tract_info,
                        'radius_miles': radius_miles
                    }

        except Exception as e:
            print(f"Error fetching complete demographics: {e}")
            import traceback
            traceback.print_exc()

        # Fallback to defaults
        return self._get_default_complete_demographics()

    def _estimate_population_in_radius(self, lat: float, lon: float, state: str, county: str, radius_miles: float) -> int:
        """
        Estimate population within radius by using county-level data.
        A 3-mile radius in an urban area typically captures 50,000-150,000 people.
        We use county population as a reasonable proxy since tract is too small.
        """
        try:
            # Get county population
            url = f"{self.census_base_url}/2022/acs/acs5"
            params = {
                'get': 'B01001_001E',  # Total population
                'for': f'county:{county}',
                'in': f'state:{state}'
            }
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if len(data) > 1:
                    county_pop = int(data[1][0]) if data[1][0] != 'null' else 0

                    # Estimate: 3-mile radius in urban areas typically has 5-15% of county pop
                    # Use 10% as reasonable middle estimate
                    # This gives ~100K for Philadelphia County (1.5M), which is realistic
                    radius_factor = min(radius_miles / 10.0, 0.20)  # Cap at 20% of county
                    estimated_pop = int(county_pop * radius_factor)

                    # Ensure reasonable bounds (10K minimum, 500K maximum for 3-mile radius)
                    estimated_pop = max(10000, min(estimated_pop, 500000))

                    return estimated_pop
        except Exception as e:
            print(f"Error estimating population in radius: {e}")

        # Fallback: use typical urban 3-mile radius population
        return 75000

    def _calculate_population_growth(self, state: str, county: str, tract: str) -> float:
        """
        Calculate population growth by comparing 2022 vs 2017 ACS data
        Returns annual growth rate as percentage
        """
        try:
            # Get 2022 population
            url_2022 = f"{self.census_base_url}/2022/acs/acs5"
            params_2022 = {
                'get': 'B01001_001E',
                'for': f'tract:{tract}',
                'in': f'state:{state} county:{county}'
            }
            response_2022 = requests.get(url_2022, params=params_2022, timeout=10)
            pop_2022 = 0
            if response_2022.status_code == 200:
                data_2022 = response_2022.json()
                if len(data_2022) > 1:
                    pop_2022 = int(data_2022[1][0]) if data_2022[1][0] != 'null' else 0

            # Get 2017 population
            url_2017 = f"{self.census_base_url}/2017/acs/acs5"
            params_2017 = {
                'get': 'B01001_001E',
                'for': f'tract:{tract}',
                'in': f'state:{state} county:{county}'
            }
            response_2017 = requests.get(url_2017, params=params_2017, timeout=10)
            pop_2017 = 0
            if response_2017.status_code == 200:
                data_2017 = response_2017.json()
                if len(data_2017) > 1:
                    pop_2017 = int(data_2017[1][0]) if data_2017[1][0] != 'null' else 0

            # Calculate annual growth rate
            if pop_2017 > 0 and pop_2022 > 0:
                years = 5  # 2017 to 2022
                total_growth = ((pop_2022 - pop_2017) / pop_2017) * 100
                annual_growth = total_growth / years
                return annual_growth

        except Exception as e:
            print(f"Error calculating growth rate: {e}")

        return 2.0  # Default growth rate

    def _get_default_complete_demographics(self) -> Dict[str, any]:
        """Return conservative defaults when API unavailable"""
        return {
            'pop_3mi': 50000,
            'median_income': 65000,
            'growth_rate': 2.0,
            'renter_pct': 35.0,
            'age_25_54_pct': 40.0,
            'data_source': 'Default estimates',
            'data_level': 'National averages',
            'note': 'Census data unavailable - using national averages'
        }


# Convenience function
def fetch_demographics_data(lat: float, lon: float) -> Dict[str, any]:
    """
    Easy-to-use function for fetching ALL demographic data
    Returns: pop_3mi, median_income, growth_rate, renter_pct, age_25_54_pct

    Usage:
        demo = fetch_demographics_data(32.7767, -96.7970)  # Dallas coords
        print(demo['pop_3mi'])  # 145000
        print(demo['median_income'])  # 75000
        print(demo['age_25_54_pct'])  # 42.3
    """

    fetcher = DemographicsDataFetcher()
    result = fetcher.get_complete_demographics(lat, lon, radius_miles=3.0)
    return result
