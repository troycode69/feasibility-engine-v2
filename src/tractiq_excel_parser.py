"""
TractIQ Excel Data Parser
Parses all TractIQ export formats: Demographics, SF per Capita, Rental Comps,
Storage Facilities, Commercial/Housing Developments
"""

import pandas as pd
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path


def parse_tractiq_excel(file_path: str) -> Dict[str, Any]:
    """
    Parse a TractIQ Excel file and extract structured data.
    Auto-detects file type based on content.

    Returns dict with extracted data keyed by data type.
    """
    file_name = Path(file_path).name.lower()

    # Detect file type and route to appropriate parser
    if 'demograph' in file_name:
        return parse_demographics_excel(file_path)
    elif 'square foot' in file_name or 'sf per capita' in file_name or 'sqft' in file_name:
        return parse_sf_per_capita_excel(file_path)
    elif 'rental' in file_name or 'comps' in file_name:
        return parse_rental_comps_excel(file_path)
    elif 'storage' in file_name and 'facilities' in file_name:
        return parse_storage_facilities_excel(file_path)
    elif 'commercial' in file_name:
        return parse_commercial_developments_excel(file_path)
    elif 'housing' in file_name:
        return parse_housing_developments_excel(file_path)
    else:
        # Try to auto-detect by reading first few rows
        return auto_detect_and_parse(file_path)


def parse_demographics_excel(file_path: str) -> Dict[str, Any]:
    """Parse TractIQ Demographics Excel export."""
    df = pd.read_excel(file_path, header=None)

    data = {
        "source_type": "TractIQ Demographics",
        "extraction_date": datetime.now().isoformat(),
        "demographics": {},
        "demographics_by_radius": {
            "1mi": {},
            "3mi": {},
            "5mi": {}
        }
    }

    # Column mapping: 1=1mi, 3=3mi, 5=5mi (0-indexed: cols 1, 3, 5)
    radius_cols = {0: "1mi", 2: "3mi", 4: "5mi"}  # Adjusted for actual data columns

    current_section = None

    for idx, row in df.iterrows():
        values = row.tolist()

        # Skip empty rows
        if all(pd.isna(v) for v in values):
            continue

        # Get first non-null value as label
        label = None
        for v in values:
            if pd.notna(v) and isinstance(v, str):
                label = str(v).strip()
                break

        if not label:
            continue

        # Detect section headers
        if label.startswith('SE:'):
            current_section = label
            continue

        # Parse data rows - extract values for each radius
        try:
            # Get numeric values from columns 1, 3, 5 (1mi, 3mi, 5mi)
            val_1mi = values[1] if len(values) > 1 and pd.notna(values[1]) else None
            val_3mi = values[3] if len(values) > 3 and pd.notna(values[3]) else None
            val_5mi = values[5] if len(values) > 5 and pd.notna(values[5]) else None

            # Clean and convert values
            def clean_value(v):
                if v is None or pd.isna(v):
                    return None
                if isinstance(v, (int, float)):
                    return float(v)
                v_str = str(v).replace(',', '').replace('%', '').strip()
                try:
                    return float(v_str)
                except:
                    return v_str

            val_1mi = clean_value(val_1mi)
            val_3mi = clean_value(val_3mi)
            val_5mi = clean_value(val_5mi)

            # Normalize label to snake_case key
            key = label.lower().replace(' ', '_').replace('-', '_')
            key = re.sub(r'[^a-z0-9_]', '', key)

            # Store by radius
            if val_1mi is not None:
                data["demographics_by_radius"]["1mi"][key] = val_1mi
            if val_3mi is not None:
                data["demographics_by_radius"]["3mi"][key] = val_3mi
            if val_5mi is not None:
                data["demographics_by_radius"]["5mi"][key] = val_5mi

            # Also store key metrics in flat demographics dict
            label_lower = label.lower()
            if '2025 total population' in label_lower:
                data["demographics"]["population_1mi"] = val_1mi
                data["demographics"]["population_3mi"] = val_3mi
                data["demographics"]["population_5mi"] = val_5mi
            elif 'median household income' in label_lower and 'current' in label_lower:
                data["demographics"]["median_income_1mi"] = val_1mi
                data["demographics"]["median_income_3mi"] = val_3mi
                data["demographics"]["median_income_5mi"] = val_5mi
            elif 'renter occupied' in label_lower:
                # Convert to percentage if decimal
                if val_1mi and val_1mi < 1:
                    val_1mi *= 100
                if val_3mi and val_3mi < 1:
                    val_3mi *= 100
                if val_5mi and val_5mi < 1:
                    val_5mi *= 100
                data["demographics"]["renter_pct_1mi"] = val_1mi
                data["demographics"]["renter_pct_3mi"] = val_3mi
                data["demographics"]["renter_pct_5mi"] = val_5mi
            elif '2025 households' in label_lower:
                data["demographics"]["households_1mi"] = val_1mi
                data["demographics"]["households_3mi"] = val_3mi
                data["demographics"]["households_5mi"] = val_5mi

        except Exception as e:
            continue

    print(f"Demographics parsed: {len(data['demographics'])} key metrics")
    return data


def parse_sf_per_capita_excel(file_path: str) -> Dict[str, Any]:
    """Parse TractIQ Square Foot per Capita Excel export."""
    df = pd.read_excel(file_path, header=None)

    data = {
        "source_type": "TractIQ SF per Capita",
        "extraction_date": datetime.now().isoformat(),
        "sf_per_capita_analysis": {},
        "market_supply": {},
        "demographics": {}
    }

    for idx, row in df.iterrows():
        values = row.tolist()

        if all(pd.isna(v) for v in values):
            continue

        label = None
        for v in values:
            if pd.notna(v) and isinstance(v, str):
                label = str(v).strip()
                break

        if not label:
            continue

        try:
            val_1mi = values[1] if len(values) > 1 and pd.notna(values[1]) else None
            val_3mi = values[3] if len(values) > 3 and pd.notna(values[3]) else None
            val_5mi = values[5] if len(values) > 5 and pd.notna(values[5]) else None

            def clean_value(v):
                if v is None or pd.isna(v):
                    return None
                if isinstance(v, (int, float)):
                    return float(v)
                v_str = str(v).replace(',', '').replace('%', '').strip()
                try:
                    return float(v_str)
                except:
                    return None

            val_1mi = clean_value(val_1mi)
            val_3mi = clean_value(val_3mi)
            val_5mi = clean_value(val_5mi)

            label_lower = label.lower()

            # Key metrics extraction
            if 'current population' in label_lower:
                data["demographics"]["population_1mi"] = val_1mi
                data["demographics"]["population_3mi"] = val_3mi
                data["demographics"]["population_5mi"] = val_5mi

            elif 'current number of facilities' in label_lower and 'climate' not in label_lower:
                data["market_supply"]["facility_count_1mi"] = int(val_1mi) if val_1mi else 0
                data["market_supply"]["facility_count_3mi"] = int(val_3mi) if val_3mi else 0
                data["market_supply"]["facility_count_5mi"] = int(val_5mi) if val_5mi else 0

            elif 'current rentable square footage' in label_lower:
                data["sf_per_capita_analysis"]["total_rentable_sf_1mi"] = val_1mi
                data["sf_per_capita_analysis"]["total_rentable_sf_3mi"] = val_3mi
                data["sf_per_capita_analysis"]["total_rentable_sf_5mi"] = val_5mi

            elif 'incoming' in label_lower and 'facilities' in label_lower:
                data["market_supply"]["incoming_facilities_1mi"] = int(val_1mi) if val_1mi else 0
                data["market_supply"]["incoming_facilities_3mi"] = int(val_3mi) if val_3mi else 0
                data["market_supply"]["incoming_facilities_5mi"] = int(val_5mi) if val_5mi else 0

            elif 'renter occupied' in label_lower:
                if val_1mi and val_1mi < 1:
                    val_1mi *= 100
                if val_3mi and val_3mi < 1:
                    val_3mi *= 100
                if val_5mi and val_5mi < 1:
                    val_5mi *= 100
                data["demographics"]["renter_pct_1mi"] = val_1mi
                data["demographics"]["renter_pct_3mi"] = val_3mi
                data["demographics"]["renter_pct_5mi"] = val_5mi

            elif 'median household income' in label_lower:
                data["demographics"]["median_income_1mi"] = val_1mi
                data["demographics"]["median_income_3mi"] = val_3mi
                data["demographics"]["median_income_5mi"] = val_5mi

        except Exception as e:
            continue

    # Calculate SF per capita if we have population and SF data
    for radius in ["1mi", "3mi", "5mi"]:
        pop_key = f"population_{radius}"
        sf_key = f"total_rentable_sf_{radius}"
        if data["demographics"].get(pop_key) and data["sf_per_capita_analysis"].get(sf_key):
            pop = data["demographics"][pop_key]
            sf = data["sf_per_capita_analysis"][sf_key]
            if pop > 0:
                data["sf_per_capita_analysis"][f"sf_per_capita_{radius}"] = round(sf / pop, 2)

    print(f"SF per Capita parsed: {len(data['sf_per_capita_analysis'])} metrics, {len(data['market_supply'])} supply metrics")
    return data


def parse_rental_comps_excel(file_path: str) -> Dict[str, Any]:
    """Parse TractIQ Rental Comps Excel export - returns competitor data."""
    df = pd.read_excel(file_path)

    data = {
        "source_type": "TractIQ Rental Comps",
        "extraction_date": datetime.now().isoformat(),
        "competitors": [],
        "extracted_rates": []
    }

    # Normalize column names
    df.columns = [str(c).lower().strip() for c in df.columns]

    # Standard unit sizes
    standard_sizes = ['5x5', '5x10', '10x10', '10x15', '10x20', '10x30']

    # Group by Facility ID to deduplicate
    facilities = {}

    for idx, row in df.iterrows():
        facility_id = row.get('facility id')
        if pd.isna(facility_id):
            continue

        # Skip non-numeric facility IDs (like 'Average' row)
        try:
            facility_id = str(int(float(facility_id)))
        except (ValueError, TypeError):
            continue

        if facility_id not in facilities:
            # Safely extract numeric fields
            nrsf = None
            try:
                sq_val = row.get('square ft.')
                if pd.notna(sq_val):
                    nrsf = int(float(sq_val))
            except (ValueError, TypeError):
                pass

            distance = None
            try:
                dist_val = row.get('distance (miles)')
                if pd.notna(dist_val):
                    distance = float(dist_val)
            except (ValueError, TypeError):
                pass

            occupancy = None
            try:
                occ_val = row.get('aggregate')
                if pd.notna(occ_val):
                    occupancy = float(occ_val)
            except (ValueError, TypeError):
                pass

            facilities[facility_id] = {
                "facility_id": facility_id,
                "name": row.get('facility', ''),
                "address": row.get('address', ''),
                "nrsf": nrsf,
                "distance_miles": distance,
                "occupancy": occupancy,
                "source": "TractIQ"
            }

        # Extract rates for each unit size
        comp = facilities[facility_id]
        for size in standard_sizes:
            # Climate controlled
            cc_col = f'cc - {size}'
            if cc_col in df.columns:
                val = row.get(cc_col)
                if pd.notna(val) and val != 'N/A':
                    try:
                        rate = float(str(val).replace('$', '').replace(',', ''))
                        if 0.1 <= rate <= 50:  # Per SF rate
                            comp[f"rate_cc-{size}"] = rate
                            data["extracted_rates"].append(rate)
                    except:
                        pass

            # Non-climate controlled
            noncc_col = f'non cc - {size}'
            if noncc_col in df.columns:
                val = row.get(noncc_col)
                if pd.notna(val) and val != 'N/A':
                    try:
                        rate = float(str(val).replace('$', '').replace(',', ''))
                        if 0.1 <= rate <= 50:
                            comp[f"rate_noncc-{size}"] = rate
                            data["extracted_rates"].append(rate)
                    except:
                        pass

    data["competitors"] = list(facilities.values())
    data["extracted_rates"] = sorted(list(set(data["extracted_rates"])))

    print(f"Rental Comps parsed: {len(data['competitors'])} facilities, {len(data['extracted_rates'])} unique rates")
    return data


def parse_storage_facilities_excel(file_path: str) -> Dict[str, Any]:
    """Parse TractIQ Storage Facilities Excel export - detailed facility data."""
    df = pd.read_excel(file_path)

    data = {
        "source_type": "TractIQ Storage Facilities",
        "extraction_date": datetime.now().isoformat(),
        "competitors": []
    }

    # Normalize column names
    col_map = {str(c).lower().strip(): c for c in df.columns}

    for idx, row in df.iterrows():
        comp = {"source": "TractIQ Facilities"}

        # Map columns
        if 'facility id' in col_map:
            comp["facility_id"] = str(int(row[col_map['facility id']])) if pd.notna(row[col_map['facility id']]) else None
        if 'company' in col_map:
            comp["name"] = row[col_map['company']]
        if 'full address' in col_map:
            comp["address"] = row[col_map['full address']]
        if 'management type' in col_map:
            comp["management_type"] = row[col_map['management type']]
        if 'phone' in col_map:
            comp["phone"] = row[col_map['phone']]

        # Extract numeric fields
        for field in ['total rentable square footage', 'units', 'physical occupancy']:
            for col in col_map:
                if field in col:
                    val = row[col_map[col]]
                    if pd.notna(val):
                        try:
                            if 'occupancy' in col:
                                comp["occupancy"] = float(str(val).replace('%', ''))
                            elif 'square' in col:
                                comp["nrsf"] = int(float(val))
                            elif 'unit' in col:
                                comp["units"] = int(float(val))
                        except:
                            pass

        # Extract lat/lon
        if 'latitude' in col_map:
            val = row[col_map['latitude']]
            if pd.notna(val):
                comp["latitude"] = float(val)
        if 'longitude' in col_map:
            val = row[col_map['longitude']]
            if pd.notna(val):
                comp["longitude"] = float(val)

        if comp.get("name") or comp.get("address"):
            data["competitors"].append(comp)

    print(f"Storage Facilities parsed: {len(data['competitors'])} facilities")
    return data


def parse_commercial_developments_excel(file_path: str) -> Dict[str, Any]:
    """Parse TractIQ Commercial Developments Excel export - pipeline/development data."""
    df = pd.read_excel(file_path)

    data = {
        "source_type": "TractIQ Commercial Developments",
        "extraction_date": datetime.now().isoformat(),
        "commercial_developments": [],
        "pipeline_summary": {
            "total_projects": 0,
            "total_cost": 0,
            "storage_related": 0
        }
    }

    col_map = {str(c).lower().strip(): c for c in df.columns}

    for idx, row in df.iterrows():
        project = {}

        if 'name' in col_map:
            project["name"] = row[col_map['name']]
        if 'address' in col_map:
            project["address"] = row[col_map['address']]
        if 'project description' in col_map:
            project["description"] = row[col_map['project description']]
        if 'cost' in col_map:
            val = row[col_map['cost']]
            if pd.notna(val):
                try:
                    project["cost"] = float(str(val).replace('$', '').replace(',', ''))
                    data["pipeline_summary"]["total_cost"] += project["cost"]
                except:
                    pass
        if 'project stage' in col_map:
            project["stage"] = row[col_map['project stage']]
        if 'building uses' in col_map:
            project["building_uses"] = row[col_map['building uses']]
            # Check if storage-related
            if pd.notna(project.get("building_uses")):
                if 'storage' in str(project["building_uses"]).lower():
                    data["pipeline_summary"]["storage_related"] += 1

        if project.get("name"):
            data["commercial_developments"].append(project)
            data["pipeline_summary"]["total_projects"] += 1

    print(f"Commercial Developments parsed: {data['pipeline_summary']['total_projects']} projects")
    return data


def parse_housing_developments_excel(file_path: str) -> Dict[str, Any]:
    """Parse TractIQ Housing Developments Excel export."""
    df = pd.read_excel(file_path)

    data = {
        "source_type": "TractIQ Housing Developments",
        "extraction_date": datetime.now().isoformat(),
        "housing_developments": [],
        "housing_summary": {
            "total_projects": 0,
            "total_units": 0
        }
    }

    if len(df) == 0:
        print("Housing Developments: No data")
        return data

    col_map = {str(c).lower().strip(): c for c in df.columns}

    for idx, row in df.iterrows():
        project = {}

        if 'name' in col_map:
            project["name"] = row[col_map['name']]
        if 'address' in col_map:
            project["address"] = row[col_map['address']]
        if 'number of units' in col_map:
            val = row[col_map['number of units']]
            if pd.notna(val):
                try:
                    project["units"] = int(float(val))
                    data["housing_summary"]["total_units"] += project["units"]
                except:
                    pass

        if project.get("name"):
            data["housing_developments"].append(project)
            data["housing_summary"]["total_projects"] += 1

    print(f"Housing Developments parsed: {data['housing_summary']['total_projects']} projects, {data['housing_summary']['total_units']} units")
    return data


def auto_detect_and_parse(file_path: str) -> Dict[str, Any]:
    """Auto-detect file type by content and parse accordingly."""
    df = pd.read_excel(file_path, header=None, nrows=5)

    # Check first few cells for indicators
    content = ' '.join(str(v) for row in df.values for v in row if pd.notna(v))
    content_lower = content.lower()

    if 'demographic' in content_lower:
        return parse_demographics_excel(file_path)
    elif 'square foot per capita' in content_lower or 'sf per capita' in content_lower:
        return parse_sf_per_capita_excel(file_path)
    elif 'facility id' in content_lower and ('cc -' in content_lower or 'rate' in content_lower):
        return parse_rental_comps_excel(file_path)
    elif 'facility id' in content_lower:
        return parse_storage_facilities_excel(file_path)
    else:
        # Default to rental comps parser
        return parse_rental_comps_excel(file_path)


def process_all_tractiq_files(input_dir: str = "src/data/input") -> Dict[str, Any]:
    """
    Process all TractIQ Excel files in the input directory.
    Merges all data into a single comprehensive market data structure.
    """
    input_path = Path(input_dir)

    combined_data = {
        "source_type": "TractIQ Combined",
        "extraction_date": datetime.now().isoformat(),
        "demographics": {},
        "sf_per_capita_analysis": {},
        "market_supply": {},
        "competitors": [],
        "extracted_rates": [],
        "commercial_developments": [],
        "housing_developments": [],
        "pipeline_summary": {},
        "files_processed": []
    }

    excel_files = list(input_path.glob("*.xlsx")) + list(input_path.glob("*.xls"))

    for file_path in excel_files:
        print(f"\nProcessing: {file_path.name}")
        try:
            file_data = parse_tractiq_excel(str(file_path))
            combined_data["files_processed"].append(file_path.name)

            # Merge data
            if file_data.get("demographics"):
                combined_data["demographics"].update(file_data["demographics"])
            if file_data.get("sf_per_capita_analysis"):
                combined_data["sf_per_capita_analysis"].update(file_data["sf_per_capita_analysis"])
            if file_data.get("market_supply"):
                combined_data["market_supply"].update(file_data["market_supply"])
            if file_data.get("competitors"):
                combined_data["competitors"].extend(file_data["competitors"])
            if file_data.get("extracted_rates"):
                combined_data["extracted_rates"].extend(file_data["extracted_rates"])
            if file_data.get("commercial_developments"):
                combined_data["commercial_developments"].extend(file_data["commercial_developments"])
            if file_data.get("housing_developments"):
                combined_data["housing_developments"].extend(file_data["housing_developments"])
            if file_data.get("pipeline_summary"):
                combined_data["pipeline_summary"].update(file_data["pipeline_summary"])

        except Exception as e:
            print(f"  Error processing {file_path.name}: {e}")

    # Deduplicate competitors by facility_id
    seen_ids = {}
    for comp in combined_data["competitors"]:
        fid = comp.get("facility_id") or comp.get("address") or comp.get("name")
        if fid and fid not in seen_ids:
            seen_ids[fid] = comp
        elif fid in seen_ids:
            # Merge rate data
            for k, v in comp.items():
                if k.startswith("rate_") and k not in seen_ids[fid]:
                    seen_ids[fid][k] = v

    combined_data["competitors"] = list(seen_ids.values())
    combined_data["extracted_rates"] = sorted(list(set(combined_data["extracted_rates"])))

    print(f"\n=== COMBINED RESULTS ===")
    print(f"Files processed: {len(combined_data['files_processed'])}")
    print(f"Demographics metrics: {len(combined_data['demographics'])}")
    print(f"SF per Capita metrics: {len(combined_data['sf_per_capita_analysis'])}")
    print(f"Market supply metrics: {len(combined_data['market_supply'])}")
    print(f"Unique competitors: {len(combined_data['competitors'])}")
    print(f"Commercial developments: {len(combined_data['commercial_developments'])}")

    return combined_data


# Test
if __name__ == "__main__":
    result = process_all_tractiq_files()
    print("\n=== DEMOGRAPHICS ===")
    for k, v in result["demographics"].items():
        print(f"  {k}: {v}")
    print("\n=== SF PER CAPITA ===")
    for k, v in result["sf_per_capita_analysis"].items():
        print(f"  {k}: {v}")
    print("\n=== MARKET SUPPLY ===")
    for k, v in result["market_supply"].items():
        print(f"  {k}: {v}")
