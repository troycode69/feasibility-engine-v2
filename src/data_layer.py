"""
Centralized Data Layer for Feasibility Engine

Single source of truth for all market data, competitor counts, and analysis results.
Ensures consistency across all pages by caching calculations in session state.
"""

import streamlit as st
from typing import Dict, Optional, List, Any
from datetime import datetime


# Distance tolerance for competitor counting (matches TractiQ methodology)
DISTANCE_TOLERANCE = 0.35
MIN_COMPETITOR_DISTANCE = 0.05  # Exclude subject site


class FeasibilityDataLayer:
    """
    Single source of truth for all feasibility data.
    All data access goes through this layer to ensure consistency across pages.
    """

    @staticmethod
    def get_competitor_count(radius: int, force_recalculate: bool = False) -> int:
        """
        Get competitor count for a given radius. Returns cached value if available.

        Args:
            radius: Analysis radius in miles (1, 3, or 5)
            force_recalculate: If True, recalculates even if cached

        Returns:
            Number of competitors within the radius
        """
        # Initialize cache if needed
        if 'competitor_counts' not in st.session_state:
            st.session_state.competitor_counts = {}

        cache_key = f"{radius}mi"

        # Return cached value if available and not forcing recalculation
        if not force_recalculate and cache_key in st.session_state.competitor_counts:
            return st.session_state.competitor_counts[cache_key]

        # Calculate from market data
        count = FeasibilityDataLayer._calculate_competitor_count(radius)
        st.session_state.competitor_counts[cache_key] = count
        return count

    @staticmethod
    def _calculate_competitor_count(radius: int) -> int:
        """Internal method to calculate competitor count from market data."""
        # Get full market data from cache
        from src.tractiq_cache import TractIQCache

        project_address = st.session_state.get('property_data', {}).get('address', '')
        if not project_address:
            return 0

        cache = TractIQCache()
        full_market_data = cache.get_market_data(project_address)

        if not full_market_data:
            return 0

        all_comps = full_market_data.get('aggregated_data', {}).get('competitors', [])
        count = len([c for c in all_comps
                     if c.get('distance_miles') is not None
                     and c.get('distance_miles') > MIN_COMPETITOR_DISTANCE
                     and c.get('distance_miles') <= (radius + DISTANCE_TOLERANCE)])

        return count

    @staticmethod
    def get_sf_per_capita(radius: int) -> Optional[float]:
        """
        Get SF per capita for a given radius.

        Args:
            radius: Analysis radius in miles (1, 3, or 5)

        Returns:
            SF per capita value or None if not available
        """
        # Initialize cache if needed
        if 'sf_per_capita_cache' not in st.session_state:
            st.session_state.sf_per_capita_cache = {}

        cache_key = f"{radius}mi"

        # Return cached value if available
        if cache_key in st.session_state.sf_per_capita_cache:
            return st.session_state.sf_per_capita_cache[cache_key]

        # Get from market data
        from src.tractiq_cache import TractIQCache

        project_address = st.session_state.get('property_data', {}).get('address', '')
        if not project_address:
            return None

        cache = TractIQCache()
        full_market_data = cache.get_market_data(project_address)

        if not full_market_data:
            return None

        sf_analysis = full_market_data.get('aggregated_data', {}).get('sf_per_capita_analysis', {})
        value = sf_analysis.get(f'sf_per_capita_{radius}mi')

        if value is not None:
            st.session_state.sf_per_capita_cache[cache_key] = value

        return value

    @staticmethod
    def get_demographics(radius: int) -> Dict[str, Any]:
        """
        Get demographics data for a given radius.

        Args:
            radius: Analysis radius in miles (1, 3, or 5)

        Returns:
            Dictionary with population, median_income, etc.
        """
        from src.tractiq_cache import TractIQCache

        project_address = st.session_state.get('property_data', {}).get('address', '')
        if not project_address:
            return {}

        cache = TractIQCache()
        full_market_data = cache.get_market_data(project_address)

        if not full_market_data:
            return {}

        demographics = full_market_data.get('aggregated_data', {}).get('demographics', {})

        return {
            'population': demographics.get(f'population_{radius}mi'),
            'median_income': demographics.get(f'median_income_{radius}mi'),
            'households': demographics.get(f'households_{radius}mi'),
            'median_age': demographics.get(f'median_age_{radius}mi'),
        }

    @staticmethod
    def get_analysis_results() -> Optional[Any]:
        """
        Get the complete analysis results from session state.

        Returns:
            AnalyticsResults object or None
        """
        return st.session_state.get('analysis_results')

    @staticmethod
    def get_market_data() -> Optional[Dict]:
        """
        Get full market data for the current project address.

        Returns:
            Market data dictionary or None
        """
        from src.tractiq_cache import TractIQCache

        project_address = st.session_state.get('property_data', {}).get('address', '')
        if not project_address:
            return None

        cache = TractIQCache()
        return cache.get_market_data(project_address)

    @staticmethod
    def get_competitors(radius: int) -> List[Dict]:
        """
        Get list of competitors within a given radius.

        Args:
            radius: Analysis radius in miles

        Returns:
            List of competitor dictionaries
        """
        from src.tractiq_cache import TractIQCache

        project_address = st.session_state.get('property_data', {}).get('address', '')
        if not project_address:
            return []

        cache = TractIQCache()
        full_market_data = cache.get_market_data(project_address)

        if not full_market_data:
            return []

        all_comps = full_market_data.get('aggregated_data', {}).get('competitors', [])

        # Filter by radius with tolerance
        filtered = [c for c in all_comps
                    if c.get('distance_miles') is not None
                    and c.get('distance_miles') > MIN_COMPETITOR_DISTANCE
                    and c.get('distance_miles') <= (radius + DISTANCE_TOLERANCE)]

        # Sort by distance
        filtered.sort(key=lambda x: x.get('distance_miles', 999))

        return filtered

    @staticmethod
    def clear_cache():
        """Clear all cached data. Call when switching to a new project."""
        st.session_state.competitor_counts = {}
        st.session_state.sf_per_capita_cache = {}
        st.session_state.analysis_results = None
        st.session_state.analysis_complete = False
        st.session_state.generated_report = None
        st.session_state.report_sections = {}
        st.session_state.pdf_bytes = None

    @staticmethod
    def is_analysis_complete() -> bool:
        """Check if analysis has been completed."""
        return st.session_state.get('analysis_complete', False)

    @staticmethod
    def get_data_quality_score() -> int:
        """
        Calculate data quality score based on available data.

        Returns:
            Score from 0-100
        """
        score = 0

        # Check TractiQ data
        market_data = FeasibilityDataLayer.get_market_data()
        if market_data:
            score += 40

        # Check competitor count
        comp_count = FeasibilityDataLayer.get_competitor_count(3, force_recalculate=False)
        if comp_count > 0:
            score += 10
        if comp_count > 5:
            score += 10
        if comp_count > 10:
            score += 10

        # Check demographics
        demo = FeasibilityDataLayer.get_demographics(3)
        if demo.get('population'):
            score += 15
        if demo.get('median_income'):
            score += 15

        return min(score, 100)


# Convenience alias
FDL = FeasibilityDataLayer
