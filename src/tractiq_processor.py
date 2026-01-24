"""
TractiQ File Processor
Processes uploaded TractiQ PDF, CSV, and Excel files to extract competitor data
"""

from typing import Dict, List, Optional
from datetime import datetime
import io


def process_tractiq_files(uploaded_files) -> Dict:
    """
    Process uploaded TractiQ files (PDF, CSV, Excel) to extract competitor data.

    Args:
        uploaded_files: List of uploaded file objects from Streamlit file_uploader

    Returns:
        Dict containing extracted competitors, rates, unit mix, and trends
    """
    all_competitors = []
    all_rates = []
    unit_mix = {}
    historical_trends = []

    for file in uploaded_files:
        try:
            # Get file extension
            file_ext = file.name.lower().split('.')[-1]

            if file_ext == 'pdf':
                # Process PDF file
                data = process_pdf(file)
            elif file_ext == 'csv':
                # Process CSV file
                data = process_csv(file)
            elif file_ext in ['xlsx', 'xls']:
                # Process Excel file
                data = process_excel(file)
            else:
                continue

            # Merge extracted data
            if data.get('competitors'):
                all_competitors.extend(data['competitors'])
            if data.get('extracted_rates'):
                all_rates.extend(data['extracted_rates'])
            if data.get('unit_mix'):
                for size, count in data['unit_mix'].items():
                    unit_mix[size] = unit_mix.get(size, 0) + count
            if data.get('historical_trends'):
                historical_trends.extend(data['historical_trends'])

        except Exception as e:
            print(f"Error processing {file.name}: {str(e)}")
            continue

    # Deduplicate rates
    all_rates = sorted(list(set(all_rates)))

    return {
        "competitors": all_competitors,
        "extracted_rates": all_rates,
        "unit_mix": unit_mix,
        "historical_trends": historical_trends,
        "extraction_date": datetime.now().isoformat()
    }


def process_pdf(file) -> Dict:
    """
    Process TractiQ PDF file to extract competitor data.

    For now, this is a placeholder that returns empty data.
    Future implementation will use PDF parsing libraries.
    """
    # TODO: Implement PDF parsing with PyPDF2 or pdfplumber
    # For now, return empty structure
    return {
        "competitors": [],
        "extracted_rates": [],
        "unit_mix": {},
        "historical_trends": []
    }


def process_csv(file) -> Dict:
    """
    Process TractiQ CSV file to extract competitor data.
    """
    try:
        import pandas as pd

        # Read CSV
        df = pd.read_csv(file)

        competitors = []
        rates = []
        unit_mix = {}

        # Look for common TractiQ CSV columns
        # This is a basic implementation - may need adjustment based on actual format

        for idx, row in df.iterrows():
            # Try to extract competitor info
            competitor = {}

            # Common field mappings
            if 'Name' in df.columns or 'Facility Name' in df.columns:
                competitor['name'] = row.get('Name') or row.get('Facility Name', '')

            if 'Address' in df.columns:
                competitor['address'] = row.get('Address', '')

            if 'Distance' in df.columns or 'Distance (mi)' in df.columns:
                try:
                    dist = row.get('Distance') or row.get('Distance (mi)', 0)
                    competitor['distance'] = float(str(dist).replace('mi', '').strip())
                except:
                    competitor['distance'] = 0

            if 'Occupancy' in df.columns or 'Occupancy %' in df.columns:
                try:
                    occ = row.get('Occupancy') or row.get('Occupancy %', 0)
                    competitor['occupancy'] = float(str(occ).replace('%', '').strip())
                except:
                    competitor['occupancy'] = 0

            # Extract rates by unit size
            for col in df.columns:
                if 'x' in col.lower() and any(char.isdigit() for char in col):
                    # Looks like a unit size column (e.g., "5x10", "10x10")
                    try:
                        rate = float(str(row.get(col, 0)).replace('$', '').replace(',', '').strip())
                        if rate > 0:
                            size_key = col.lower().replace(' ', '')
                            competitor[f'rate_{size_key}'] = rate
                            rates.append(rate)

                            # Add to unit mix
                            if size_key not in unit_mix:
                                unit_mix[size_key] = 1
                            else:
                                unit_mix[size_key] += 1
                    except:
                        continue

            if competitor:
                competitors.append(competitor)

        return {
            "competitors": competitors,
            "extracted_rates": rates,
            "unit_mix": unit_mix,
            "historical_trends": []
        }

    except Exception as e:
        print(f"Error processing CSV: {str(e)}")
        return {
            "competitors": [],
            "extracted_rates": [],
            "unit_mix": {},
            "historical_trends": []
        }


def process_excel(file) -> Dict:
    """
    Process TractiQ Excel file to extract competitor data.
    """
    try:
        import pandas as pd

        # Read Excel (try first sheet)
        df = pd.read_excel(file, sheet_name=0)

        # Use same logic as CSV processing
        competitors = []
        rates = []
        unit_mix = {}

        for idx, row in df.iterrows():
            competitor = {}

            # Common field mappings
            if 'Name' in df.columns or 'Facility Name' in df.columns:
                competitor['name'] = row.get('Name') or row.get('Facility Name', '')

            if 'Address' in df.columns:
                competitor['address'] = row.get('Address', '')

            if 'Distance' in df.columns or 'Distance (mi)' in df.columns:
                try:
                    dist = row.get('Distance') or row.get('Distance (mi)', 0)
                    competitor['distance'] = float(str(dist).replace('mi', '').strip())
                except:
                    competitor['distance'] = 0

            if 'Occupancy' in df.columns or 'Occupancy %' in df.columns:
                try:
                    occ = row.get('Occupancy') or row.get('Occupancy %', 0)
                    competitor['occupancy'] = float(str(occ).replace('%', '').strip())
                except:
                    competitor['occupancy'] = 0

            # Extract rates by unit size
            for col in df.columns:
                if 'x' in str(col).lower() and any(char.isdigit() for char in str(col)):
                    try:
                        rate = float(str(row.get(col, 0)).replace('$', '').replace(',', '').strip())
                        if rate > 0:
                            size_key = str(col).lower().replace(' ', '')
                            competitor[f'rate_{size_key}'] = rate
                            rates.append(rate)

                            # Add to unit mix
                            if size_key not in unit_mix:
                                unit_mix[size_key] = 1
                            else:
                                unit_mix[size_key] += 1
                    except:
                        continue

            if competitor:
                competitors.append(competitor)

        return {
            "competitors": competitors,
            "extracted_rates": rates,
            "unit_mix": unit_mix,
            "historical_trends": []
        }

    except Exception as e:
        print(f"Error processing Excel: {str(e)}")
        return {
            "competitors": [],
            "extracted_rates": [],
            "unit_mix": {},
            "historical_trends": []
        }
