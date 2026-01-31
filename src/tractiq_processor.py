"""
TractiQ File Processor
Processes uploaded TractiQ PDF, CSV, and Excel files to extract competitor data
"""

from typing import Dict, List, Optional
from datetime import datetime
import io


def process_tractiq_files(uploaded_files) -> Dict:
    """
    Process uploaded TractiQ files (PDF, CSV, Excel) to extract competitor data and demographics.

    Args:
        uploaded_files: List of uploaded file objects from Streamlit file_uploader

    Returns:
        Dict containing extracted competitors, rates, unit_mix, trends, demographics, and SF analysis
    """
    all_competitors = []
    all_rates = []
    unit_mix = {}
    historical_trends = []
    demographics = {}
    sf_per_capita_analysis = {}
    commercial_developments = []
    housing_developments = []

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
            if data.get('demographics'):
                # Merge demographics (later data overwrites earlier)
                demographics.update(data['demographics'])
            if data.get('sf_per_capita_analysis'):
                # Merge SF per capita analysis
                sf_per_capita_analysis.update(data['sf_per_capita_analysis'])
            if data.get('commercial_developments'):
                commercial_developments.extend(data['commercial_developments'])
            if data.get('housing_developments'):
                housing_developments.extend(data['housing_developments'])

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
        "demographics": demographics,
        "sf_per_capita_analysis": sf_per_capita_analysis,
        "commercial_developments": commercial_developments,
        "housing_developments": housing_developments,
        "extraction_date": datetime.now().isoformat()
    }


def process_pdf(file) -> Dict:
    """
    Process TractiQ PDF file to extract competitor data and demographics.

    Handles:
    - Demographic Profile PDFs (population, income, renter %)
    - Square Foot Per Capita Analysis PDFs (SF per capita, total SF)
    - Rate Trends PDFs (pricing data)
    - Storage Site Report PDFs (competitor details)
    """
    try:
        import pdfplumber
        import re

        # Read PDF content
        pdf_content = file.read()
        file_name = file.name.lower()

        result = {
            "competitors": [],
            "extracted_rates": [],
            "unit_mix": {},
            "historical_trends": [],
            "demographics": {}
        }

        # Determine PDF type and extract accordingly
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            full_text = ""
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"

            # DEMOGRAPHIC PROFILE PDF
            if "demographic profile" in file_name:
                demo_data = extract_demographics_from_pdf(full_text)
                result["demographics"] = demo_data

            # SQUARE FOOT PER CAPITA ANALYSIS PDF
            elif "square foot per capita" in file_name or "sf per capita" in file_name:
                sf_data = extract_sf_per_capita_from_pdf(full_text)
                result["sf_per_capita_analysis"] = sf_data

            # RATE TRENDS REPORT PDF
            elif "rate trends" in file_name:
                rate_data = extract_rate_trends_from_pdf(full_text)
                result["extracted_rates"] = rate_data.get("rates", [])
                result["historical_trends"] = rate_data.get("trends", [])

            # STORAGE SITE REPORT PDF
            elif "storage site report" in file_name:
                competitor_data = extract_competitors_from_pdf(full_text)
                result["competitors"] = competitor_data

        return result

    except Exception as e:
        print(f"Error processing PDF {file.name}: {str(e)}")
        return {
            "competitors": [],
            "extracted_rates": [],
            "unit_mix": {},
            "historical_trends": [],
            "demographics": {}
        }


def extract_demographics_from_pdf(text: str) -> Dict:
    """
    Extract demographic data from TractiQ Demographic Profile PDF.

    TractiQ PDFs use a column-based layout where data is organized as:
    Header: "1 mile    3 miles    20 miles"
    Data rows with values aligned in columns

    Extracts:
    - Population by radius (1mi, 3mi, 20mi)
    - Households by radius
    - Median income by radius
    - Renter-occupied % by radius
    - Growth projections
    """
    import re

    demographics = {}

    try:
        # Extract population - Format: "Total Population" followed by 3 numbers in columns
        # Example line: "10,354 87,131 1,274,953"
        pop_match = re.search(r'Total Population.*?\n\s*([\d,]+)\s+([\d,]+)\s+([\d,]+)', text, re.IGNORECASE)
        if pop_match:
            demographics['population_1mi'] = int(pop_match.group(1).replace(',', ''))
            demographics['population_3mi'] = int(pop_match.group(2).replace(',', ''))
            demographics['population_20mi'] = int(pop_match.group(3).replace(',', ''))

        # Extract households - Format: "Number of Households" then "Current" then 3 numbers
        household_match = re.search(r'Number of Households.*?Current\s+Current\s+Current\s*\n\s*([\d,]+)\s+([\d,]+)\s+([\d,]+)', text, re.IGNORECASE | re.DOTALL)
        if household_match:
            demographics['households_1mi'] = int(household_match.group(1).replace(',', ''))
            demographics['households_3mi'] = int(household_match.group(2).replace(',', ''))
            demographics['households_20mi'] = int(household_match.group(3).replace(',', ''))

        # Extract projected households
        household_proj_match = re.search(r'Projected \(5 years\)\s+Projected \(5 years\)\s+Projected \(5 years\)\s*\n\s*([\d,]+)\s+([\d,]+)\s+([\d,]+)', text, re.IGNORECASE | re.DOTALL)
        if household_proj_match:
            demographics['households_3mi_projected'] = int(household_proj_match.group(2).replace(',', ''))

        # Extract median income - Format: "Household Income (Median)"
        # Line 1: Projected values: $49,496 $61,298 $101,224
        # Line 2: Chart labels + Current values: $50k $46,597 $56,412 $100k $93,305
        # We want the current values: $46,597 (1mi), $56,412 (3mi), $93,305 (20mi)
        income_section = re.search(r'Household Income \(Median\).{0,300}Current', text, re.IGNORECASE | re.DOTALL)
        if income_section:
            income_text = income_section.group(0)
            # Find all dollar amounts (filter out chart axis labels like $50k, $100k)
            amounts = re.findall(r'\$?([\d,]{5,})', income_text)  # At least 5 chars (filters out $50k, $25k)
            if len(amounts) >= 6:
                # Current values are at positions 3, 4, 5 (after projected values)
                demographics['median_income_1mi'] = int(amounts[3].replace(',', ''))
                demographics['median_income_3mi'] = int(amounts[4].replace(',', ''))
                demographics['median_income_20mi'] = int(amounts[5].replace(',', ''))

        # Extract renter-occupied percentage - Format: percentages in "Renter Occupied" row
        # The format shows: 54.27% for 3 miles
        # Layout: Owner Occupied current (3 values), Owner projected (3 values),
        #         Renter current (3 values), Renter projected (3 values)
        # We want Renter current values at indices 12, 14, 16
        tenure_section = re.search(r'Tenure \(Current and Projected\).*?Renter Occupied', text, re.IGNORECASE | re.DOTALL)
        if tenure_section:
            tenure_text = tenure_section.group(0)
            # Find ALL percentage values
            percentages = re.findall(r'([\d.]+)%', tenure_text)
            if len(percentages) >= 16:
                # Renter current percentages: 58.70% (1mi), 54.27% (3mi), 37.66% (20mi)
                demographics['renter_occupied_pct_1mi'] = float(percentages[12])
                demographics['renter_occupied_pct_3mi'] = float(percentages[14])
                demographics['renter_occupied_pct_20mi'] = float(percentages[16])

        # Extract population growth projection
        pop_proj_match = re.search(r'Based on Census\s+Based on Census\s+Based on Census\s*\n\s*([\d,]+)\s+([\d,]+)\s+([\d,]+)', text, re.IGNORECASE | re.DOTALL)
        if pop_proj_match:
            demographics['population_3mi_projected'] = int(pop_proj_match.group(2).replace(',', ''))

        # Calculate growth rate if we have current and projected
        if 'population_3mi' in demographics and 'population_3mi_projected' in demographics:
            current = demographics['population_3mi']
            projected = demographics['population_3mi_projected']
            if current > 0:
                # 5-year growth rate annualized
                demographics['population_growth_rate_annual'] = ((projected / current) ** (1/5) - 1) * 100

        if demographics:
            print(f"✓ Extracted demographics: {len(demographics)} data points")
        else:
            print("⚠ No demographic data extracted")

    except Exception as e:
        print(f"Error extracting demographics: {str(e)}")
        import traceback
        traceback.print_exc()

    return demographics


def extract_sf_per_capita_from_pdf(text: str) -> Dict:
    """
    Extract square footage per capita analysis from TractiQ PDF.

    Strategy: Extract rentable SF from page 4 which has clear tabular format.
    Format on page 4:
    - Line: "Gross Gross Gross"
    - Line: "223,506.00 706,815.00 11,517,779.00"  (1mi, 3mi, 20mi)
    - Line: "Rentable Rentable Rentable"
    - Line: "215,210.00 676,149.00 10,128,071.00"  (1mi, 3mi, 20mi)
    """
    import re

    sf_data = {}

    try:
        # Extract the line with 3 Gross SF numbers
        # Pattern: 3 numbers with commas after "Gross Gross Gross"
        gross_line_pattern = r'Gross\s+Gross\s+Gross\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)'
        gross_match = re.search(gross_line_pattern, text, re.IGNORECASE)

        if gross_match:
            sf_data['total_gross_sf_1mi'] = float(gross_match.group(1).replace(',', ''))
            sf_data['total_gross_sf_3mi'] = float(gross_match.group(2).replace(',', ''))
            sf_data['total_gross_sf_20mi'] = float(gross_match.group(3).replace(',', ''))

        # Extract the line with 3 Rentable SF numbers
        # Pattern: 3 numbers with commas after "Rentable Rentable Rentable"
        rentable_line_pattern = r'Rentable\s+Rentable\s+Rentable\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)'
        rentable_match = re.search(rentable_line_pattern, text, re.IGNORECASE)

        if rentable_match:
            sf_data['total_rentable_sf_1mi'] = float(rentable_match.group(1).replace(',', ''))
            sf_data['total_rentable_sf_3mi'] = float(rentable_match.group(2).replace(',', ''))
            sf_data['total_rentable_sf_20mi'] = float(rentable_match.group(3).replace(',', ''))

        # Now calculate SF per capita using population from demographics
        # We'll need to do this calculation after merging with demographics data
        # For now, we just extract the SF values

        print(f"✓ Extracted SF per capita data: {len(sf_data)} metrics")

    except Exception as e:
        print(f"Error extracting SF data: {str(e)}")

    return sf_data


def extract_rate_trends_from_pdf(text: str) -> Dict:
    """
    Extract rate trends and pricing data from TractiQ Rate Trends Report PDF.
    """
    import re

    rate_data = {
        "rates": [],
        "trends": []
    }

    try:
        # Extract rates by unit size
        # Format: "5x5: $45" or "10x10 Climate: $125"
        rate_pattern = r'(\d+x\d+(?:\s+Climate)?)\s*[:\-]\s*\$?([\d,]+(?:\.\d{2})?)'
        matches = re.findall(rate_pattern, text, re.IGNORECASE)

        for unit_size, rate in matches:
            try:
                rate_value = float(rate.replace(',', ''))
                if rate_value > 0:
                    rate_data["rates"].append({
                        "unit_size": unit_size.strip(),
                        "rate": rate_value
                    })
            except:
                continue

        # Extract unique rate values
        unique_rates = sorted(list(set([r["rate"] for r in rate_data["rates"]])))

        print(f"✓ Extracted {len(rate_data['rates'])} rate entries ({len(unique_rates)} unique values)")

    except Exception as e:
        print(f"Error extracting rates: {str(e)}")

    return rate_data


def extract_competitors_from_pdf(text: str) -> List[Dict]:
    """
    Extract competitor facility data from TractiQ Storage Site Report PDF.
    """
    import re

    competitors = []

    try:
        # This is more complex - Storage Site Reports contain tables with competitor details
        # For now, extract basic facility information

        # Extract facility names and addresses (pattern may vary)
        facility_pattern = r'([A-Z][A-Za-z\s&\']+Storage[A-Za-z\s]*)\s+([\d]+[^\n]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd)[^\n]*)'
        matches = re.findall(facility_pattern, text)

        for name, address in matches:
            competitors.append({
                "name": name.strip(),
                "address": address.strip()
            })

        print(f"✓ Extracted {len(competitors)} competitor facilities from Storage Site Report")

    except Exception as e:
        print(f"Error extracting competitors from PDF: {str(e)}")

    return competitors


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
            if 'Name' in df.columns or 'Facility Name' in df.columns or 'Company' in df.columns:
                competitor['name'] = row.get('Name') or row.get('Facility Name') or row.get('Company', '')

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
    Process TractiQ Excel file to extract competitor data and demographics.

    Handles:
    - Demography.xlsx: Population, households, income, renter % by radius
    - Storage Facilities.xlsx: Competitor facility data
    - Rental Comps.xlsx: Rate comparison data
    - Square Foot per Capita.xlsx: SF per capita analysis
    """
    try:
        import pandas as pd

        file_name = file.name.lower()
        result = {
            "competitors": [],
            "extracted_rates": [],
            "unit_mix": {},
            "historical_trends": [],
            "demographics": {}
        }

        # DEMOGRAPHY.XLSX - Extract demographics by radius
        if 'demography' in file_name:
            demographics = extract_demographics_from_excel(file)
            result["demographics"] = demographics
            return result

        # SQUARE FOOT PER CAPITA.XLSX - Extract SF metrics
        elif 'square foot per capita' in file_name or 'sf per capita' in file_name:
            sf_data = extract_sf_from_excel(file)
            result["sf_per_capita_analysis"] = sf_data
            return result

        # STORAGE FACILITIES.XLSX - Extract competitor data
        elif 'storage facilities' in file_name or 'facilities' in file_name:
            competitors = extract_competitors_from_excel(file)
            result["competitors"] = competitors
            return result

        # RENTAL COMPS.XLSX - Extract rate data
        elif 'rental' in file_name or 'comps' in file_name:
            rates_data = extract_rates_from_excel(file)
            result["extracted_rates"] = rates_data.get("rates", [])
            result["unit_mix"] = rates_data.get("unit_mix", {})
            # Also extract competitors from rental comps (has facility data with rates)
            if rates_data.get("competitors"):
                result["competitors"] = rates_data.get("competitors", [])
            return result

        # COMMERCIAL DEVELOPMENTS.XLSX - Extract pipeline data
        elif 'commercial' in file_name:
            developments = extract_commercial_developments(file)
            result["commercial_developments"] = developments
            return result

        # HOUSING DEVELOPMENTS.XLSX - Extract housing pipeline data
        elif 'housing' in file_name:
            developments = extract_housing_developments(file)
            result["housing_developments"] = developments
            return result

        # Generic Excel processing (fallback)
        else:
            return process_excel_generic(file)

    except Exception as e:
        print(f"Error processing Excel {file.name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "competitors": [],
            "extracted_rates": [],
            "unit_mix": {},
            "historical_trends": [],
            "demographics": {}
        }


def extract_demographics_from_excel(file) -> Dict:
    """Extract demographics from Demography.xlsx"""
    import pandas as pd
    import io

    demographics = {}

    try:
        # Read file content into BytesIO
        file_content = file.read()
        if hasattr(file, 'seek'):
            file.seek(0)  # Reset position after reading
        excel_buffer = io.BytesIO(file_content)

        # Read with header row 1
        df = pd.read_excel(excel_buffer, sheet_name=0, header=1)
        df = df.set_index('Unnamed: 0')

        # Column names
        col_1mi = [c for c in df.columns if '1 mile radius' in str(c)][0]
        col_3mi = [c for c in df.columns if '3 mile radius' in str(c)][0]
        col_5mi = [c for c in df.columns if '5 mile radius' in str(c)][0]

        # Extract population
        demographics['population_1mi'] = int(df.loc['2025 Total Population', col_1mi])
        demographics['population_3mi'] = int(df.loc['2025 Total Population', col_3mi])
        demographics['population_5mi'] = int(df.loc['2025 Total Population', col_5mi])

        # Extract households
        demographics['households_1mi'] = int(df.loc['2025 Households', col_1mi])
        demographics['households_3mi'] = int(df.loc['2025 Households', col_3mi])
        demographics['households_5mi'] = int(df.loc['2025 Households', col_5mi])

        # Extract projected households
        demographics['households_3mi_projected'] = int(df.loc['2030 Households', col_3mi])
        demographics['households_5mi_projected'] = int(df.loc['2030 Households', col_5mi])

        # Extract median income
        demographics['median_income_1mi'] = int(df.loc['2025 Median Household Income', col_1mi])
        demographics['median_income_3mi'] = int(df.loc['2025 Median Household Income', col_3mi])
        demographics['median_income_5mi'] = int(df.loc['2025 Median Household Income', col_5mi])

        # Extract renter-occupied %
        all_renter_rows = df[df.index == '      Renter Occupied']
        all_occupied_rows = df[df.index == '   Occupied Units']

        renter_1mi = all_renter_rows.iloc[0][col_1mi]
        renter_3mi = all_renter_rows.iloc[0][col_3mi]
        renter_5mi = all_renter_rows.iloc[0][col_5mi]
        occupied_1mi = all_occupied_rows.iloc[0][col_1mi]
        occupied_3mi = all_occupied_rows.iloc[0][col_3mi]
        occupied_5mi = all_occupied_rows.iloc[0][col_5mi]

        demographics['renter_occupied_pct_1mi'] = (renter_1mi / occupied_1mi) * 100
        demographics['renter_occupied_pct_3mi'] = (renter_3mi / occupied_3mi) * 100
        demographics['renter_occupied_pct_5mi'] = (renter_5mi / occupied_5mi) * 100

        # Extract median age
        demographics['median_age_1mi'] = float(df.loc['2025 Population, Median Age', col_1mi])
        demographics['median_age_3mi'] = float(df.loc['2025 Population, Median Age', col_3mi])
        demographics['median_age_5mi'] = float(df.loc['2025 Population, Median Age', col_5mi])

        # Calculate growth rate
        pop_current = demographics['population_3mi']
        pop_projected = int(df.loc['2030 Total Population', col_3mi])
        demographics['population_3mi_projected'] = pop_projected
        if pop_current > 0:
            demographics['population_growth_rate_annual'] = ((pop_projected / pop_current) ** (1/5) - 1) * 100

        print(f"✓ Extracted demographics from Excel: {len(demographics)} data points")

    except Exception as e:
        print(f"Error extracting demographics from Excel: {str(e)}")
        import traceback
        traceback.print_exc()

    return demographics


def extract_sf_from_excel(file) -> Dict:
    """
    Extract SF per capita data from Square Foot per Capita.xlsx.

    This Excel file contains detailed market metrics for 1-mile, 3-mile, and 5-mile radii including:
    - Current/Projected SF per capita
    - Total rentable/gross SF
    - Number of facilities
    - Population and demographics
    """
    import pandas as pd
    import io

    sf_data = {}

    try:
        # Read file content
        file_content = file.read()
        if hasattr(file, 'seek'):
            file.seek(0)
        excel_buffer = io.BytesIO(file_content)

        # Read the Excel file
        df = pd.read_excel(excel_buffer, sheet_name=0)

        # The file has columns for different radii
        # Column 0: Metric names
        # Column 3: 1 mile radius
        # Column 4: 3 mile radius
        # Column 5: 5 mile radius

        # Create a lookup dict for easier access
        metrics = {}
        for idx, row in df.iterrows():
            metric_name = row.iloc[0]
            if pd.notna(metric_name):
                metrics[metric_name] = {
                    '1mi': row.iloc[3] if len(row) > 3 else None,
                    '3mi': row.iloc[4] if len(row) > 4 else None,
                    '5mi': row.iloc[5] if len(row) > 5 else None
                }

        # Extract SF per capita (current)
        if 'Current Square Footage per Capita' in metrics:
            vals = metrics['Current Square Footage per Capita']
            if pd.notna(vals.get('1mi')):
                sf_data['sf_per_capita_1mi'] = float(vals['1mi'])
            if pd.notna(vals.get('3mi')):
                sf_data['sf_per_capita_3mi'] = float(vals['3mi'])
            if pd.notna(vals.get('5mi')):
                sf_data['sf_per_capita_5mi'] = float(vals['5mi'])

        # Extract total rentable SF
        if 'Current Rentable Square Footage' in metrics:
            vals = metrics['Current Rentable Square Footage']
            if pd.notna(vals.get('1mi')):
                sf_data['total_rentable_sf_1mi'] = float(vals['1mi'])
            if pd.notna(vals.get('3mi')):
                sf_data['total_rentable_sf_3mi'] = float(vals['3mi'])
            if pd.notna(vals.get('5mi')):
                sf_data['total_rentable_sf_5mi'] = float(vals['5mi'])

        # Extract total gross SF
        if 'Current Gross Square Footage' in metrics:
            vals = metrics['Current Gross Square Footage']
            if pd.notna(vals.get('1mi')):
                sf_data['total_gross_sf_1mi'] = float(vals['1mi'])
            if pd.notna(vals.get('3mi')):
                sf_data['total_gross_sf_3mi'] = float(vals['3mi'])
            if pd.notna(vals.get('5mi')):
                sf_data['total_gross_sf_5mi'] = float(vals['5mi'])

        # Extract number of facilities
        if 'Current Number of Facilities' in metrics:
            vals = metrics['Current Number of Facilities']
            if pd.notna(vals.get('1mi')):
                sf_data['facility_count_1mi'] = int(vals['1mi'])
            if pd.notna(vals.get('3mi')):
                sf_data['facility_count_3mi'] = int(vals['3mi'])
            if pd.notna(vals.get('5mi')):
                sf_data['facility_count_5mi'] = int(vals['5mi'])

        print(f"✓ Extracted SF per capita from Excel: {len(sf_data)} metrics")

        # Show what we extracted
        if 'sf_per_capita_5mi' in sf_data:
            print(f"  5-mile SF/capita: {sf_data['sf_per_capita_5mi']:.2f}")
            print(f"  5-mile facilities: {sf_data.get('facility_count_5mi', 'N/A')}")

    except Exception as e:
        print(f"Error extracting SF data from Excel: {str(e)}")
        import traceback
        traceback.print_exc()

    return sf_data


def extract_competitors_from_excel(file) -> List[Dict]:
    """Extract competitor data from Storage Facilities.xlsx"""
    import pandas as pd
    import io

    try:
        file_content = file.read()
        if hasattr(file, 'seek'):
            file.seek(0)
        excel_buffer = io.BytesIO(file_content)

        df = pd.read_excel(excel_buffer)
        col_map = {str(c).lower().strip(): c for c in df.columns}

        competitors = []
        for idx, row in df.iterrows():
            comp = {"source": "TractIQ Facilities"}

            # Map common columns
            if 'facility id' in col_map:
                comp['facility_id'] = str(row[col_map['facility id']])
            if 'facility' in col_map:
                comp['name'] = row[col_map['facility']]
            elif 'name' in col_map:
                comp['name'] = row[col_map['name']]
            if 'address' in col_map:
                comp['address'] = row[col_map['address']]
            if 'square ft.' in col_map:
                try:
                    comp['nrsf'] = int(float(row[col_map['square ft.']]))
                except:
                    pass
            if 'distance (miles)' in col_map:
                try:
                    comp['distance_miles'] = float(row[col_map['distance (miles)']])
                except:
                    pass

            if comp.get('name') or comp.get('address'):
                competitors.append(comp)

        return competitors
    except Exception as e:
        print(f"Error extracting competitors from Excel: {e}")
        return []


def extract_rates_from_excel(file) -> Dict:
    """Extract rate data from Rental Comps.xlsx with proper facility deduplication"""
    import pandas as pd
    import io

    try:
        file_content = file.read()
        if hasattr(file, 'seek'):
            file.seek(0)
        excel_buffer = io.BytesIO(file_content)

        df = pd.read_excel(excel_buffer)
        df.columns = [str(c).lower().strip() for c in df.columns]

        standard_sizes = ['5x5', '5x10', '10x10', '10x15', '10x20', '10x30']
        facilities = {}
        all_rates = []

        for idx, row in df.iterrows():
            facility_id = row.get('facility id')
            if pd.isna(facility_id):
                continue

            # Skip non-numeric IDs (like 'Average')
            try:
                facility_id = str(int(float(facility_id)))
            except (ValueError, TypeError):
                continue

            if facility_id not in facilities:
                nrsf = None
                try:
                    sq_val = row.get('square ft.')
                    if pd.notna(sq_val):
                        nrsf = int(float(sq_val))
                except:
                    pass

                distance = None
                try:
                    dist_val = row.get('distance (miles)')
                    if pd.notna(dist_val):
                        distance = float(dist_val)
                except:
                    pass

                facilities[facility_id] = {
                    "facility_id": facility_id,
                    "name": row.get('facility', ''),
                    "address": row.get('address', ''),
                    "nrsf": nrsf,
                    "distance_miles": distance,
                    "source": "TractIQ"
                }

            # Extract rates for each unit size
            comp = facilities[facility_id]
            for size in standard_sizes:
                # Climate controlled
                cc_col = f'cc - {size}'
                if cc_col in df.columns:
                    val = row.get(cc_col)
                    if pd.notna(val) and str(val) != 'N/A':
                        try:
                            rate = float(str(val).replace('$', '').replace(',', ''))
                            if 0.1 <= rate <= 50:
                                comp[f"rate_cc-{size}"] = rate
                                all_rates.append(rate)
                        except:
                            pass

                # Non-climate controlled
                noncc_col = f'non cc - {size}'
                if noncc_col in df.columns:
                    val = row.get(noncc_col)
                    if pd.notna(val) and str(val) != 'N/A':
                        try:
                            rate = float(str(val).replace('$', '').replace(',', ''))
                            if 0.1 <= rate <= 50:
                                comp[f"rate_noncc-{size}"] = rate
                                all_rates.append(rate)
                        except:
                            pass

        return {
            "rates": sorted(list(set(all_rates))),
            "unit_mix": {},
            "competitors": list(facilities.values())
        }
    except Exception as e:
        print(f"Error extracting rates from Excel: {e}")
        import traceback
        traceback.print_exc()
        return {"rates": [], "unit_mix": {}, "competitors": []}


def extract_commercial_developments(file) -> List[Dict]:
    """Extract commercial development pipeline from Commercial Developments.xlsx"""
    import pandas as pd
    import io

    try:
        file_content = file.read()
        if hasattr(file, 'seek'):
            file.seek(0)
        excel_buffer = io.BytesIO(file_content)

        df = pd.read_excel(excel_buffer)
        df.columns = [str(c).lower().strip() for c in df.columns]

        developments = []
        for idx, row in df.iterrows():
            dev = {}

            # Map common columns
            if 'project name' in df.columns:
                dev['name'] = row.get('project name', '')
            elif 'name' in df.columns:
                dev['name'] = row.get('name', '')

            if 'address' in df.columns:
                dev['address'] = row.get('address', '')

            if 'description' in df.columns:
                dev['description'] = row.get('description', '')

            if 'estimated construction value' in df.columns:
                try:
                    dev['cost'] = float(row.get('estimated construction value', 0))
                except:
                    pass

            if 'stage' in df.columns:
                dev['stage'] = row.get('stage', '')

            if 'primary building use' in df.columns:
                dev['building_uses'] = row.get('primary building use', '')

            if dev.get('name'):
                developments.append(dev)

        print(f"Commercial developments parsed: {len(developments)} projects")
        return developments
    except Exception as e:
        print(f"Error extracting commercial developments: {e}")
        return []


def extract_housing_developments(file) -> List[Dict]:
    """Extract housing development pipeline from Housing Developments.xlsx"""
    import pandas as pd
    import io

    try:
        file_content = file.read()
        if hasattr(file, 'seek'):
            file.seek(0)
        excel_buffer = io.BytesIO(file_content)

        df = pd.read_excel(excel_buffer)
        df.columns = [str(c).lower().strip() for c in df.columns]

        developments = []
        for idx, row in df.iterrows():
            dev = {"type": "housing"}

            # Map common columns
            if 'project name' in df.columns:
                dev['name'] = row.get('project name', '')
            elif 'name' in df.columns:
                dev['name'] = row.get('name', '')

            if 'address' in df.columns:
                dev['address'] = row.get('address', '')

            if 'description' in df.columns:
                dev['description'] = row.get('description', '')

            if 'total units' in df.columns:
                try:
                    dev['units'] = int(float(row.get('total units', 0)))
                except:
                    pass

            if 'estimated construction value' in df.columns:
                try:
                    dev['cost'] = float(row.get('estimated construction value', 0))
                except:
                    pass

            if 'stage' in df.columns:
                dev['stage'] = row.get('stage', '')

            if dev.get('name'):
                developments.append(dev)

        print(f"Housing developments parsed: {len(developments)} projects")
        return developments
    except Exception as e:
        print(f"Error extracting housing developments: {e}")
        return []


def process_excel_generic(file) -> Dict:
    """Generic Excel processing (fallback for unknown files)"""
    import pandas as pd
    import io

    # Read file content into BytesIO
    file_content = file.read()
    if hasattr(file, 'seek'):
        file.seek(0)
    excel_buffer = io.BytesIO(file_content)

    # Use same logic as original CSV processing
    df = pd.read_excel(excel_buffer, sheet_name=0)

    competitors = []
    rates = []
    unit_mix = {}

    for idx, row in df.iterrows():
        competitor = {}

        # Common field mappings
        if 'Name' in df.columns or 'Facility Name' in df.columns or 'Company' in df.columns:
            competitor['name'] = row.get('Name') or row.get('Facility Name') or row.get('Company', '')

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
