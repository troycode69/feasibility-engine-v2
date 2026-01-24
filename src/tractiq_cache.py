"""
TractIQ Data Cache Manager
Persistently stores market intelligence from uploaded TractIQ PDFs for reuse across analyses
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path


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
        # Normalize: lowercase, remove special chars, replace spaces with underscores
        market_id = market_name.lower().strip()
        market_id = ''.join(c if c.isalnum() or c == ' ' else '' for c in market_id)
        market_id = market_id.replace(' ', '_')
        return market_id

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
        """Aggregate data from multiple PDF extractions"""
        all_competitors = []
        all_rates = []
        all_trends = []
        unit_mix_data = {}
        market_metrics = {}

        for pdf_name, ext_data in pdf_extractions.items():
            # Collect competitors
            if ext_data.get('competitors'):
                for comp in ext_data['competitors']:
                    comp['source_pdf'] = pdf_name
                    comp['cached_date'] = ext_data.get('extraction_date', datetime.now().isoformat())
                    all_competitors.append(comp)

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

        # Deduplicate and sort
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
            "market_metrics": market_metrics
        }

    def get_market_data(self, market_identifier: str) -> Optional[Dict]:
        """
        Retrieve cached market data.

        Args:
            market_identifier: Either market_id or market_name

        Returns:
            Market data dict or None if not found
        """
        # Try as market_id first
        market_id = self._generate_market_id(market_identifier)
        cache_file = self.cache_dir / f"{market_id}.json"

        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)

        return None

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


def get_cached_tractiq_data(market_name: str) -> Dict:
    """Retrieve cached TractIQ data for a market"""
    cache = TractIQCache()
    return cache.get_cached_data_for_report(market_name)


def list_cached_markets() -> List[Dict]:
    """List all cached markets"""
    cache = TractIQCache()
    return cache.list_markets()


def get_market_stats(market_name: str) -> Optional[Dict]:
    """Get aggregated stats for a market"""
    cache = TractIQCache()
    return cache.get_aggregated_stats(market_name)
