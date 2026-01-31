"""
TractIQ CSV Data Processor
Handles rental comps and market data exports in CSV/Excel format
"""

import csv
import re
import pandas as pd
from typing import Dict, List
from datetime import datetime


def extract_csv_data(file) -> Dict:
    """
    Extract competitor and market data from TractIQ CSV/Excel exports.
    Handles rental comps, rate surveys, and market snapshots.

    Args:
        file: File-like object (BytesIO from Streamlit upload) - CSV or Excel

    Returns:
        Dict with extracted competitors, rates, unit mix, etc.
    """
    data = {
        "source_type": "TractIQ CSV/Excel",
        "competitors": [],
        "extracted_rates": [],
        "unit_mix": {},
        "market_metrics": {},
        "historical_trends": [],
        "pipeline_risk": "Standard",  # Default for CSV/Excel (no pipeline data typically)
        "extraction_date": datetime.now().isoformat()
    }

    try:
        # Detect file type and read into DataFrame
        file.seek(0)
        file_name = getattr(file, 'name', 'unknown.csv')
        file_ext = file_name.split('.')[-1].lower()

        if file_ext in ['xlsx', 'xls']:
            # Read Excel file
            df = pd.read_excel(file, engine='openpyxl' if file_ext == 'xlsx' else None)
        else:
            # Read CSV file
            df = pd.read_csv(file, encoding='utf-8', errors='ignore')

        # Convert DataFrame to list of dicts
        rows = df.to_dict('records')

        if not rows or len(rows) == 0:
            return data

        # Get headers (case-insensitive matching)
        headers = {str(h).lower(): h for h in rows[0].keys()}

        # === COMPETITOR EXTRACTION ===
        competitors = extract_competitors_from_csv(rows, headers)
        if competitors:
            data["competitors"] = competitors

        # === RATE EXTRACTION ===
        rates = extract_rates_from_csv(rows, headers)
        if rates:
            data["extracted_rates"] = sorted(list(set(rates)))

        # === UNIT MIX EXTRACTION ===
        unit_mix = extract_unit_mix_from_csv(rows, headers)
        if unit_mix:
            data["unit_mix"] = unit_mix

        # === MARKET METRICS ===
        metrics = calculate_market_metrics_from_csv(competitors)
        if metrics:
            data["market_metrics"] = metrics

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"CSV Analysis Error: {e}")
        print(error_details)
        data["error"] = str(e)
        data["error_details"] = error_details

    return data


def extract_competitors_from_csv(rows: List[Dict], headers: Dict) -> List[Dict]:
    """Extract competitor facility data from CSV rows, deduplicating by Facility ID."""
    # Use dict to deduplicate by facility_id - merge rate data for same facility
    facilities_by_id = {}

    # Common TractIQ CSV column mappings (case-insensitive)
    name_keys = ['facility name', 'name', 'property name', 'facility', 'property', 'facilityid']
    address_keys = ['address', 'street address', 'location', 'street', 'addr', 'full address']
    units_keys = ['units', 'unit count', 'total units', '# units', 'number of units']
    occupancy_keys = ['occupancy', 'physical occupancy', 'occ %', 'occupancy %', 'occupied %', 'aggregate']
    nrsf_keys = ['nrsf', 'rentable sf', 'total sf', 'square feet', 'square ft', 'sq ft', 'total rentable square footage']
    distance_keys = ['distance', 'distance (mi)', 'distance (miles)', 'miles', 'dist']
    facility_id_keys = ['facility id', 'facilityid', 'id']
    lat_keys = ['latitude', 'lat']
    lon_keys = ['longitude', 'lon', 'lng']

    # Standard unit sizes to look for
    standard_sizes = ['5x5', '5x10', '10x10', '10x15', '10x20', '10x30']

    # Debug: Print available columns
    print(f"CSV Columns found: {list(headers.keys())[:15]}")

    for row in rows:
        comp = {"source": "CSV"}

        # Extract facility ID for deduplication
        facility_id = find_value_in_row(row, headers, facility_id_keys)
        if facility_id:
            comp["facility_id"] = str(facility_id).strip()

        # Extract facility name
        name = find_value_in_row(row, headers, name_keys)
        if not name or str(name).strip() == "" or str(name).strip().lower() == 'nan':
            continue
        # Clean facility name (remove leading artifacts like "A\n")
        comp["name"] = str(name).strip().replace('\n', ' ').replace('A ', '', 1) if str(name).startswith('A\n') else str(name).strip()

        # Extract address
        address = find_value_in_row(row, headers, address_keys)
        if address:
            comp["address"] = str(address).strip()

        # Extract latitude/longitude for distance calculations
        lat = find_value_in_row(row, headers, lat_keys)
        lon = find_value_in_row(row, headers, lon_keys)
        if lat and lon:
            try:
                comp["latitude"] = float(lat)
                comp["longitude"] = float(lon)
            except:
                pass

        # Extract units
        units = find_value_in_row(row, headers, units_keys)
        if units:
            try:
                comp["units"] = int(re.sub(r'[^\d]', '', str(units)))
            except:
                pass

        # Extract occupancy
        occupancy = find_value_in_row(row, headers, occupancy_keys)
        if occupancy:
            try:
                occ_clean = str(occupancy).replace('%', '').strip()
                comp["occupancy"] = float(occ_clean)
            except:
                pass

        # Extract rates for ALL standard unit sizes (5x5, 5x10, 10x10, 10x15, 10x20, 10x30)
        # TractiQ Excel columns are like "CC - 5x5", "Non CC - 5x5", etc.
        for size in standard_sizes:
            # Look for climate controlled rates (CC - {size})
            for col_key, col_name in headers.items():
                col_lower = col_key.lower()
                # Match "cc - 5x5" or "cc - 5x10" etc.
                if f'cc - {size}' in col_lower or f'cc-{size}' in col_lower:
                    value = row.get(col_name, '')
                    if value and str(value).strip() and str(value).strip().lower() not in ['n/a', 'na', '-', '', 'nan']:
                        try:
                            rate_clean = str(value).replace('$', '').replace(',', '').strip()
                            rate_float = float(rate_clean)
                            if 0.1 <= rate_float <= 50:  # Per SF rates typically $0.50-$5.00
                                comp[f"rate_cc-{size}"] = rate_float
                        except:
                            pass
                # Match "non cc - 5x5" or "noncc - 5x5" etc.
                elif 'non' in col_lower and size in col_lower:
                    value = row.get(col_name, '')
                    if value and str(value).strip() and str(value).strip().lower() not in ['n/a', 'na', '-', '', 'nan']:
                        try:
                            rate_clean = str(value).replace('$', '').replace(',', '').strip()
                            rate_float = float(rate_clean)
                            if 0.1 <= rate_float <= 50:  # Per SF rates typically $0.50-$5.00
                                comp[f"rate_noncc-{size}"] = rate_float
                        except:
                            pass

        # Extract NRSF
        nrsf = find_value_in_row(row, headers, nrsf_keys)
        if nrsf:
            try:
                comp["nrsf"] = int(re.sub(r'[^\d]', '', str(nrsf)))
            except:
                pass

        # Extract distance
        distance = find_value_in_row(row, headers, distance_keys)
        if distance:
            try:
                dist_val = float(re.sub(r'[^\d.]', '', str(distance)))
                if dist_val >= 0:  # Valid distance
                    comp["distance_miles"] = dist_val
            except:
                pass

        # Only add if we have at least name + one metric
        if len(comp) > 2:
            # Use facility_id for deduplication, fallback to address
            dedup_key = comp.get("facility_id") or comp.get("address", comp["name"])

            if dedup_key in facilities_by_id:
                # Merge rate data into existing record
                existing = facilities_by_id[dedup_key]
                for key, value in comp.items():
                    if key.startswith("rate_") and key not in existing:
                        existing[key] = value
                    elif key not in existing:
                        existing[key] = value
            else:
                facilities_by_id[dedup_key] = comp

    # Return deduplicated list
    competitors = list(facilities_by_id.values())
    print(f"CSV extraction: {len(rows)} rows -> {len(competitors)} unique facilities")
    return competitors


def extract_rates_from_csv(rows: List[Dict], headers: Dict) -> List[int]:
    """Extract rate data from CSV."""
    rates = []

    # Look for any column with rate data
    rate_columns = [col for col in headers.keys() if 'rate' in col or '10x10' in col or 'street' in col]

    for row in rows:
        for col in rate_columns:
            value = row.get(headers.get(col, ''), '')
            if value and '$' in str(value):
                try:
                    rate_clean = str(value).replace('$', '').replace(',', '').strip()
                    rate = float(rate_clean)
                    if 40 <= rate <= 600:  # Reasonable range
                        rates.append(int(round(rate)))
                except:
                    pass

    return rates


def extract_unit_mix_from_csv(rows: List[Dict], headers: Dict) -> Dict[str, int]:
    """Extract unit mix data from CSV."""
    unit_mix = {}

    # Look for columns that might contain unit sizes
    size_columns = [col for col in headers.keys() if 'size' in col or 'unit type' in col or 'mix' in col]
    count_columns = [col for col in headers.keys() if 'count' in col or '# units' in col]

    # Method 1: Dedicated size/count columns
    if size_columns and count_columns:
        for row in rows:
            size = find_value_in_row(row, headers, size_columns)
            count = find_value_in_row(row, headers, count_columns)

            if size and count:
                try:
                    # Normalize size (e.g., "10 x 10" -> "10x10")
                    size_clean = re.sub(r'\s*[xX×]\s*', 'x', str(size))
                    count_int = int(re.sub(r'[^\d]', '', str(count)))

                    if size_clean in unit_mix:
                        unit_mix[size_clean] += count_int
                    else:
                        unit_mix[size_clean] = count_int
                except:
                    pass

    # Method 2: Columns named like "5x5", "10x10", etc. with unit counts
    size_pattern = re.compile(r'(\d{1,2}\s*[xX×]\s*\d{1,2})')
    for col in headers.keys():
        if size_pattern.search(col):
            size_match = size_pattern.search(col)
            if size_match:
                size = re.sub(r'\s*([xX×])\s*', 'x', size_match.group(1))

                # Sum up all values in this column
                total = 0
                for row in rows:
                    value = row.get(headers.get(col, ''), '')
                    if value:
                        try:
                            total += int(re.sub(r'[^\d]', '', str(value)))
                        except:
                            pass

                if total > 0:
                    unit_mix[size] = total

    return unit_mix


def calculate_market_metrics_from_csv(competitors: List[Dict]) -> Dict:
    """Calculate aggregate market metrics from competitor data."""
    metrics = {}

    if not competitors:
        return metrics

    # Average occupancy
    occupancies = [c['occupancy'] for c in competitors if 'occupancy' in c]
    if occupancies:
        metrics["market_occupancy"] = sum(occupancies) / len(occupancies)

    # Average rate
    rates = [c['rate_10x10'] for c in competitors if 'rate_10x10' in c]
    if rates:
        metrics["market_avg_rate"] = sum(rates) / len(rates)

    # Total supply
    total_units = sum(c.get('units', 0) for c in competitors)
    if total_units > 0:
        metrics["total_supply"] = total_units

    total_nrsf = sum(c.get('nrsf', 0) for c in competitors)
    if total_nrsf > 0:
        metrics["total_supply_sf"] = total_nrsf

    return metrics


def find_value_in_row(row: Dict, headers: Dict, key_variations: List[str]) -> str:
    """
    Find a value in a CSV row using multiple possible key variations.
    Case-insensitive matching.
    """
    for key_var in key_variations:
        # Try exact match in headers dict
        if key_var in headers:
            actual_key = headers[key_var]
            if actual_key in row:
                return row[actual_key]

        # Try direct match in row
        for row_key in row.keys():
            if key_var.lower() == row_key.lower():
                return row[row_key]

    return None
