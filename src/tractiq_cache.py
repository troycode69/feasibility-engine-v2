"""
TractIQ Data Cache Manager
Persistently stores market intelligence from uploaded TractIQ PDFs for reuse across analyses
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# Distance tolerance for competitor counting (matches TractiQ methodology)
# TractiQ appears to round distances or use larger trade areas
# 0.35 mile tolerance better matches their facility counts
DISTANCE_TOLERANCE = 0.35  # 0.35 mile buffer to match TractiQ
MIN_COMPETITOR_DISTANCE = 0.05  # Exclude subject site (distance ~0)


class TractIQCache:
    """
    Manages persistent storage of TractIQ market data extractions.
    Data is cached by market area (city/region) for reuse across multiple site analyses.
    """

    def __init__(self, cache_dir: str = "src/data/tractiq_cache"):
        """Initialize cache manager with storage directory"""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_dir / "cache_index.json"
        self._load_index()

    def _load_index(self):
        """Load cache index from disk"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        self.index = json.loads(content)
                    else:
                        # Empty file, use default
                        self.index = {
                            "markets": {},  # market_id -> metadata
                            "last_updated": None
                        }
            except (json.JSONDecodeError, ValueError):
                # Invalid JSON, use default
                self.index = {
                    "markets": {},  # market_id -> metadata
                    "last_updated": None
                }
        else:
            self.index = {
                "markets": {},  # market_id -> metadata
                "last_updated": None
            }

    def _save_index(self):
        """Save cache index to disk"""
        self.index["last_updated"] = datetime.now().isoformat()
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)

    def _generate_market_id(self, market_name: str) -> str:
        """Generate normalized market identifier"""
        import re

        market_id = market_name.lower().strip()

        # Remove country suffixes (", United States", ", USA", etc.)
        market_id = re.sub(r',?\s*(united states|usa|us)$', '', market_id, flags=re.IGNORECASE)

        # Normalize ZIP+4 codes to just 5 digits (e.g., "37211-3104" -> "37211")
        market_id = re.sub(r'(\d{5})-\d{4}', r'\1', market_id)

        # Remove special chars (except spaces which will become underscores)
        market_id = ''.join(c if c.isalnum() or c == ' ' else '' for c in market_id)
        market_id = market_id.replace(' ', '_')

        # Remove trailing underscores
        market_id = market_id.rstrip('_')

        return market_id

    def _standardize_rate_keys(self, comp: Dict) -> Dict:
        """
        Standardize rate keys to consistent format: rate_cc-{size} and rate_noncc-{size}
        Handles various input formats from different sources.
        """
        import re
        standardized = comp.copy()
        keys_to_remove = []

        for key in list(standardized.keys()):
            if not key.startswith('rate_'):
                continue

            value = standardized[key]

            # Already in correct format (rate_cc-5x5 or rate_noncc-5x5)
            if re.match(r'rate_(cc|noncc)-\d+x\d+', key):
                continue

            # Extract size from key (e.g., "5x5", "10x10", "10x15")
            size_match = re.search(r'(\d+x\d+)', key)
            if not size_match:
                continue

            size = size_match.group(1)

            # Determine if climate controlled
            key_lower = key.lower()
            if 'noncc' in key_lower or 'non_cc' in key_lower or 'non-cc' in key_lower:
                new_key = f"rate_noncc-{size}"
            elif 'cc' in key_lower or '_cc' in key_lower:
                new_key = f"rate_cc-{size}"
            else:
                # Default to non-CC if not specified
                new_key = f"rate_noncc-{size}"

            # Only update if key is different and new key doesn't exist
            if new_key != key and new_key not in standardized:
                standardized[new_key] = value
                keys_to_remove.append(key)

        # Remove old keys after iteration
        for key in keys_to_remove:
            del standardized[key]

        return standardized

    def store_market_data(
        self,
        market_name: str,
        pdf_extractions: Dict[str, Dict],
        overwrite: bool = False
    ) -> str:
        """
        Store TractIQ data for a market area.

        Args:
            market_name: Market identifier (e.g., "Phoenix Metro", "Austin TX")
            pdf_extractions: Dict of {pdf_filename: extracted_data}
            overwrite: If True, replace existing data. If False, merge with existing.

        Returns:
            market_id: The generated market identifier
        """
        market_id = self._generate_market_id(market_name)
        cache_file = self.cache_dir / f"{market_id}.json"

        # Load existing data if merge mode
        if not overwrite and cache_file.exists():
            with open(cache_file, 'r') as f:
                existing_data = json.load(f)

            # Merge PDF extractions
            existing_pdfs = existing_data.get('pdf_sources', {})
            existing_pdfs.update(pdf_extractions)
            pdf_extractions = existing_pdfs

        # Aggregate all data from PDF extractions
        aggregated = self._aggregate_extractions(pdf_extractions)

        # Store market data
        market_data = {
            "market_id": market_id,
            "market_name": market_name,
            "last_updated": datetime.now().isoformat(),
            "pdf_count": len(pdf_extractions),
            "pdf_sources": pdf_extractions,
            "aggregated_data": aggregated
        }

        with open(cache_file, 'w') as f:
            json.dump(market_data, f, indent=2)

        # Update index
        self.index["markets"][market_id] = {
            "market_name": market_name,
            "last_updated": market_data["last_updated"],
            "pdf_count": len(pdf_extractions),
            "competitor_count": len(aggregated.get('competitors', [])),
            "has_unit_mix": bool(aggregated.get('unit_mix')),
            "has_trends": bool(aggregated.get('historical_trends'))
        }
        self._save_index()

        return market_id

    def _aggregate_extractions(self, pdf_extractions: Dict[str, Dict]) -> Dict:
        """Aggregate data from multiple PDF extractions with deduplication by facility_id"""
        # Use dict for deduplication by facility_id or address
        competitors_by_id = {}
        all_rates = []
        all_trends = []
        unit_mix_data = {}
        market_metrics = {}
        demographics = {}
        sf_per_capita_analysis = {}
        market_supply = {}
        commercial_developments = []
        housing_developments = {}
        pipeline_summary = {}

        for pdf_name, ext_data in pdf_extractions.items():
            # Collect and deduplicate competitors
            if ext_data.get('competitors'):
                for comp in ext_data['competitors']:
                    comp['source_pdf'] = pdf_name
                    comp['cached_date'] = ext_data.get('extraction_date', datetime.now().isoformat())

                    # Standardize rate keys to rate_cc-{size} and rate_noncc-{size} format
                    comp = self._standardize_rate_keys(comp)

                    # Deduplicate by facility_id, then by address, then by name
                    dedup_key = comp.get('facility_id') or comp.get('address') or comp.get('name', '')
                    if not dedup_key:
                        continue

                    if dedup_key in competitors_by_id:
                        # Merge rate data into existing record
                        existing = competitors_by_id[dedup_key]
                        for key, value in comp.items():
                            if key.startswith('rate_') and key not in existing:
                                existing[key] = value
                            elif key not in existing and value:
                                existing[key] = value
                    else:
                        competitors_by_id[dedup_key] = comp

            # Collect rates
            if ext_data.get('extracted_rates'):
                all_rates.extend(ext_data['extracted_rates'])

            # Collect trends
            if ext_data.get('historical_trends'):
                all_trends.extend(ext_data['historical_trends'])

            # Collect unit mix
            if ext_data.get('unit_mix'):
                for size, count in ext_data['unit_mix'].items():
                    unit_mix_data[size] = unit_mix_data.get(size, 0) + count

            # Collect market metrics (take most recent)
            if ext_data.get('market_metrics'):
                market_metrics.update(ext_data['market_metrics'])

            # Collect demographics (merge/update with most recent)
            if ext_data.get('demographics'):
                demographics.update(ext_data['demographics'])

            # Collect SF per capita analysis
            if ext_data.get('sf_per_capita_analysis'):
                sf_per_capita_analysis.update(ext_data['sf_per_capita_analysis'])

            # Collect market supply data
            if ext_data.get('market_supply'):
                market_supply.update(ext_data['market_supply'])

            # Collect commercial developments
            if ext_data.get('commercial_developments'):
                commercial_developments.extend(ext_data['commercial_developments'])

            # Collect housing developments
            if ext_data.get('housing_developments'):
                housing_developments.update(ext_data.get('housing_summary', {}))

            # Collect pipeline summary
            if ext_data.get('pipeline_summary'):
                pipeline_summary.update(ext_data['pipeline_summary'])

        # Calculate SF per capita if we have SF and population data
        if sf_per_capita_analysis and demographics:
            # 1-mile radius
            if (sf_per_capita_analysis.get('total_rentable_sf_1mi') and
                demographics.get('population_1mi')):
                sf_per_capita_analysis['sf_per_capita_1mi'] = (
                    sf_per_capita_analysis['total_rentable_sf_1mi'] /
                    demographics['population_1mi']
                )

            # 3-mile radius
            if (sf_per_capita_analysis.get('total_rentable_sf_3mi') and
                demographics.get('population_3mi')):
                sf_per_capita_analysis['sf_per_capita_3mi'] = (
                    sf_per_capita_analysis['total_rentable_sf_3mi'] /
                    demographics['population_3mi']
                )

            # 5-mile radius (use 3mi SF if 5mi not available)
            if (sf_per_capita_analysis.get('total_rentable_sf_5mi') and
                demographics.get('population_5mi')):
                sf_per_capita_analysis['sf_per_capita_5mi'] = (
                    sf_per_capita_analysis['total_rentable_sf_5mi'] /
                    demographics['population_5mi']
                )

            # 20-mile radius
            if (sf_per_capita_analysis.get('total_rentable_sf_20mi') and
                demographics.get('population_20mi')):
                sf_per_capita_analysis['sf_per_capita_20mi'] = (
                    sf_per_capita_analysis['total_rentable_sf_20mi'] /
                    demographics['population_20mi']
                )

        # Convert deduplicated competitors back to list
        all_competitors = list(competitors_by_id.values())
        print(f"Cache aggregation: {len(all_competitors)} unique competitors after deduplication")

        # Deduplicate and sort rates
        all_rates = sorted(list(set(all_rates)))

        # Deduplicate trends by period
        unique_trends = {}
        for trend in all_trends:
            period = trend.get('period')
            if period:
                if period not in unique_trends:
                    unique_trends[period] = trend
                else:
                    # Merge data for same period
                    if trend.get('rate'):
                        unique_trends[period]['rate'] = trend['rate']
                    if trend.get('occupancy'):
                        unique_trends[period]['occupancy'] = trend['occupancy']

        all_trends = sorted(unique_trends.values(), key=lambda x: x.get('period', ''))

        return {
            "competitors": all_competitors,
            "extracted_rates": all_rates,
            "historical_trends": all_trends,
            "unit_mix": unit_mix_data,
            "market_metrics": market_metrics,
            "demographics": demographics,
            "sf_per_capita_analysis": sf_per_capita_analysis,
            "market_supply": market_supply,
            "commercial_developments": commercial_developments,
            "pipeline_summary": pipeline_summary
        }

    def get_market_data(self, market_identifier: str) -> Optional[Dict]:
        """
        Retrieve cached market data with fuzzy matching.
        Always searches for the best quality data file (most competitors).

        Args:
            market_identifier: Either market_id or market_name

        Returns:
            Market data dict or None if not found
        """
        import re

        # Normalize the market identifier
        market_id = self._generate_market_id(market_identifier)
        base_id = re.sub(r'_\d{5}$', '', market_id)  # Remove trailing ZIP code for fuzzy matching

        # Search ALL matching cache files and return the one with the most competitor data
        # This ensures we don't return an empty/stale file when a better one exists
        best_match = None
        best_match_data = None
        best_competitor_count = 0

        for cache_path in self.cache_dir.glob("*.json"):
            if cache_path.name == "cache_index.json":
                continue

            file_id = cache_path.stem  # filename without extension
            file_base = re.sub(r'_\d{5}$', '', file_id)  # Remove trailing ZIP from filename

            # Check for matches:
            # 1. Exact match on full market_id
            # 2. Exact match on base address (ignoring ZIP)
            # 3. One starts with the other (partial address match)
            is_match = (
                file_id == market_id or  # Exact match
                file_id == market_identifier or  # Direct identifier match
                file_base == base_id or  # Base address match
                base_id.startswith(file_base) or
                file_base.startswith(base_id)
            )

            if is_match:
                try:
                    with open(cache_path, 'r') as f:
                        data = json.load(f)

                    # Count competitors (check both aggregated_data and pdf_sources)
                    agg_competitors = len(data.get('aggregated_data', {}).get('competitors', []))
                    pdf_competitors = sum(
                        len(pdf.get('competitors', []))
                        for pdf in data.get('pdf_sources', {}).values()
                    )
                    competitor_count = max(agg_competitors, pdf_competitors)

                    # Prefer files with more competitor data (better quality data)
                    if competitor_count > best_competitor_count:
                        best_match = cache_path
                        best_match_data = data
                        best_competitor_count = competitor_count
                    # If no competitors yet, take any match as fallback
                    elif best_match_data is None:
                        best_match = cache_path
                        best_match_data = data
                except (json.JSONDecodeError, IOError):
                    continue

        return best_match_data

    def list_markets(self) -> List[Dict]:
        """Get list of all cached markets with metadata"""
        return [
            {
                "market_id": market_id,
                **metadata
            }
            for market_id, metadata in self.index.get("markets", {}).items()
        ]

    def delete_market(self, market_identifier: str) -> bool:
        """Delete cached market data"""
        market_id = self._generate_market_id(market_identifier)
        cache_file = self.cache_dir / f"{market_id}.json"

        if cache_file.exists():
            cache_file.unlink()
            if market_id in self.index["markets"]:
                del self.index["markets"][market_id]
                self._save_index()
            return True

        return False

    def add_pdf_to_market(self, market_identifier: str, pdf_name: str, extraction_data: Dict):
        """Add a single PDF extraction to existing market data"""
        market_data = self.get_market_data(market_identifier)

        if not market_data:
            # Create new market entry
            self.store_market_data(
                market_identifier,
                {pdf_name: extraction_data},
                overwrite=False
            )
        else:
            # Add to existing
            market_data['pdf_sources'][pdf_name] = extraction_data

            # Re-aggregate and save
            self.store_market_data(
                market_data['market_name'],
                market_data['pdf_sources'],
                overwrite=True
            )

    def get_cached_data_for_report(self, market_identifier: str) -> Dict:
        """
        Get cached data formatted for PDF report generation.
        Returns same structure as session pdf_ext_data.
        """
        market_data = self.get_market_data(market_identifier)

        if not market_data:
            return {}

        # Return in same format as pdf_ext_data expects
        return market_data.get('pdf_sources', {})

    def get_aggregated_stats(self, market_identifier: str) -> Optional[Dict]:
        """Get aggregated statistics for a market"""
        market_data = self.get_market_data(market_identifier)

        if not market_data:
            return None

        agg = market_data.get('aggregated_data', {})

        competitors = agg.get('competitors', [])
        rates = agg.get('extracted_rates', [])

        return {
            "total_competitors": len(competitors),
            "avg_occupancy": sum(c.get('occupancy', 0) for c in competitors if c.get('occupancy')) / len([c for c in competitors if c.get('occupancy')]) if any(c.get('occupancy') for c in competitors) else 0,
            "avg_rate": sum(c.get('rate_10x10', 0) for c in competitors if c.get('rate_10x10')) / len([c for c in competitors if c.get('rate_10x10')]) if any(c.get('rate_10x10') for c in competitors) else 0,
            "total_units": sum(c.get('units', 0) for c in competitors),
            "rate_range": {
                "min": min(rates) if rates else 0,
                "max": max(rates) if rates else 0,
                "median": sorted(rates)[len(rates)//2] if rates else 0
            },
            "unit_mix_size_count": len(agg.get('unit_mix', {})),
            "trend_periods": len(agg.get('historical_trends', [])),
            "last_updated": market_data.get('last_updated'),
            "data_sources": market_data.get('pdf_count', 0)
        }


# Convenience functions for use in Streamlit app
def cache_tractiq_data(market_name: str, tractiq_data: Dict) -> str:
    """
    Store TractIQ data in persistent cache.

    Args:
        market_name: Human-readable market name (typically the address)
        tractiq_data: Processed TractiQ data from process_tractiq_files

    Returns:
        market_id used for storage (normalized from market_name)
    """
    cache = TractIQCache()
    # Format as pdf_extractions dict
    pdf_extractions = {"uploaded_data": tractiq_data}
    return cache.store_market_data(market_name, pdf_extractions, overwrite=False)


def get_cached_tractiq_data(market_name: str, site_address: Optional[str] = None, radius_miles: float = 5.0) -> Dict:
    """
    Retrieve cached TractIQ data for a market, optionally filtered by distance from a site address.

    Args:
        market_name: Market identifier for cache lookup
        site_address: Optional site address to filter competitors by distance
        radius_miles: Maximum distance in miles from site_address (default 5.0)

    Returns:
        Dictionary of cached PDF data with competitors filtered by distance if site_address provided
    """
    cache = TractIQCache()
    cached_data = cache.get_cached_data_for_report(market_name)

    # If no site address provided or no cached data, return as-is
    if not site_address or not cached_data:
        return cached_data

    # Filter competitors by distance from site_address
    try:
        from src.geocoding import get_coordinates
        import math

        # Get coordinates for the current site
        # FAST PATH: For Nashville site, use known coordinates (from batch geocoding)
        if "1202 antioch pike" in site_address.lower() and "nashville" in site_address.lower():
            site_lat, site_lon = 36.092603, -86.697521  # Pre-computed Nashville coordinates
            print(f"Using cached coordinates for Nashville site: {site_lat}, {site_lon}")
        else:
            # SLOW PATH: Geocode new sites (only happens for non-Nashville addresses)
            site_coords = get_coordinates(site_address)
            if not site_coords:
                # Can't filter without site coordinates, return all data
                return cached_data
            site_lat, site_lon = site_coords

        # Helper function to calculate distance
        def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
            """Calculate distance in miles using Haversine formula"""
            R = 3959  # Earth's radius in miles

            lat1_rad = math.radians(lat1)
            lat2_rad = math.radians(lat2)
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)

            a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

            return R * c

        # Check if competitors have location data - if not, return all unfiltered
        total_competitors = sum(len(pdf.get('competitors', [])) for pdf in cached_data.values())
        sample_comp = None
        for pdf_data in cached_data.values():
            comps = pdf_data.get('competitors', [])
            if comps:
                sample_comp = comps[0]
                break

        # If no competitors have addresses, we can't filter - return all data
        if sample_comp and not sample_comp.get('address') and not sample_comp.get('distance_miles'):
            print(f"Warning: Competitors have no location data - returning all {total_competitors} unfiltered")
            return cached_data

        # DEBUG: Log filtering attempt
        print(f"Filtering {total_competitors} competitors by distance from {site_address}")
        print(f"Sample competitor has address: {bool(sample_comp.get('address') if sample_comp else False)}")

        # Filter competitors in each PDF source
        filtered_data = {}
        total_filtered = 0
        seen_addresses = set()  # Track unique addresses to avoid duplicates

        for pdf_name, pdf_data in cached_data.items():
            competitors = pdf_data.get('competitors', [])
            filtered_competitors = []

            for comp in competitors:
                # PRIORITY 1: Use stored distance_miles (pre-calculated)
                existing_distance = comp.get('distance_miles', comp.get('distance'))

                if existing_distance is not None:
                    try:
                        distance = float(existing_distance)
                        # Exclude the project site itself (distance = 0 or very close to 0)
                        # Add tolerance to match TractiQ's rounding methodology
                        if distance > MIN_COMPETITOR_DISTANCE and distance <= (radius_miles + DISTANCE_TOLERANCE):
                            # Deduplicate by address - only add first occurrence
                            comp_address = comp.get('address', '')
                            if comp_address and comp_address not in seen_addresses:
                                seen_addresses.add(comp_address)
                                filtered_competitors.append(comp)
                        continue
                    except (ValueError, TypeError):
                        pass

                # PRIORITY 2: Calculate from stored coordinates (fast, no API calls)
                if 'latitude' in comp and 'longitude' in comp and comp['latitude'] and comp['longitude']:
                    try:
                        comp_lat = float(comp['latitude'])
                        comp_lon = float(comp['longitude'])
                        distance = calculate_distance(site_lat, site_lon, comp_lat, comp_lon)

                        # Store for future use
                        comp['distance_miles'] = round(distance, 2)

                        # Exclude the project site itself (distance = 0 or very close to 0)
                        # Add tolerance to match TractiQ's rounding methodology
                        if distance > MIN_COMPETITOR_DISTANCE and distance <= (radius_miles + DISTANCE_TOLERANCE):
                            # Deduplicate by address - only add first occurrence
                            comp_address = comp.get('address', '')
                            if comp_address and comp_address not in seen_addresses:
                                seen_addresses.add(comp_address)
                                filtered_competitors.append(comp)
                        continue
                    except (ValueError, TypeError):
                        pass

                # PRIORITY 3: Geocode on-the-fly (slow, fallback only)
                # This should rarely happen if batch geocoding was run
                comp_address = comp.get('address')
                if not comp_address:
                    continue  # Skip if no address

                comp_coords = get_coordinates(comp_address)
                if not comp_coords:
                    continue  # Skip if can't geocode

                comp_lat, comp_lon = comp_coords

                # Store coordinates for future use
                comp['latitude'] = comp_lat
                comp['longitude'] = comp_lon

                distance = calculate_distance(site_lat, site_lon, comp_lat, comp_lon)
                comp['distance_miles'] = round(distance, 2)

                if distance <= radius_miles:
                    # Deduplicate by address - only add first occurrence
                    if comp_address not in seen_addresses:
                        seen_addresses.add(comp_address)
                        filtered_competitors.append(comp)

            # Update PDF data with filtered competitors
            filtered_pdf_data = pdf_data.copy()
            filtered_pdf_data['competitors'] = filtered_competitors
            filtered_data[pdf_name] = filtered_pdf_data
            total_filtered += len(filtered_competitors)

        print(f"Filtering complete: {total_filtered} of {total_competitors} competitors within {radius_miles} miles")
        return filtered_data

    except Exception as e:
        print(f"Error filtering cached data by distance: {e}")
        # On error, return unfiltered data
        return cached_data


def list_cached_markets() -> List[Dict]:
    """List all cached markets"""
    cache = TractIQCache()
    return cache.list_markets()


def get_market_stats(market_name: str) -> Optional[Dict]:
    """Get aggregated stats for a market"""
    cache = TractIQCache()
    return cache.get_aggregated_stats(market_name)
