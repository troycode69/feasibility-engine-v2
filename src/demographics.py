import requests
import pandas as pd
import io
import zipfile
import os
import math
from geopy.distance import geodesic

# Cache directory for Gazetteer files
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def get_fips_from_lat_lon(lat, lon):
    """
    Uses FCC API to get Block/Tract/County FIPS.
    Returns: state_fips, county_fips
    """
    url = "https://geo.fcc.gov/api/census/block/find"
    params = {
        'latitude': lat,
        'longitude': lon,
        'showall': 'true',
        'format': 'json'
    }
    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        county_fips = data['County']['FIPS'] # e.g. '36015'
        state_code = data['State']['FIPS']
        return state_code, county_fips[2:]
    except Exception as e:
        print(f"Error getting FIPS: {e}")
        return None, None

def get_acs_data(year, variables, state, county):
    """
    Fetches ACS 5-Year Data for all tracts in a county.
    variables: dict of {code: nice_name}
    """
    base_url = f"https://api.census.gov/data/{year}/acs/acs5"
    
    # Construct comma-separated string of variables
    var_list = list(variables.keys())
    cols = "NAME," + ",".join(var_list)
    
    params = {
        'get': cols,
        'for': 'tract:*',
        'in': f'state:{state} county:{county}'
    }
    
    try:
        r = requests.get(base_url, params=params, timeout=10)
        if r.status_code != 200: return None
        
        data = r.json()
        # First row is headers. We need to map them to our nice names.
        headers = data[0]
        rows = data[1:]
        
        df = pd.DataFrame(rows, columns=headers)
        
        # Rename columns based on the variables dict
        df = df.rename(columns=variables)
        
        # Create full GEOID
        df['GEOID'] = df['state'] + df['county'] + df['tract']
        
        # Convert numeric columns
        for col in variables.values():
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        return df
    except:
        return None

def get_gazetteer_coords(state_fips):
    """
    Downloads or reads cached 2020 Gazetteer file for the state to get Tract Coordinates.
    Returns DataFrame: [GEOID, LAT, LON]
    """
    filename = f"2020_gaz_tracts_{state_fips}.txt"
    filepath = os.path.join(CACHE_DIR, filename)
    
    # Download if not exists
    if not os.path.exists(filepath):
        print(f"Downloading Gazetteer for State {state_fips}...")
        url = f"https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/2020_gaz_tracts_{state_fips}.txt"
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(r.content)
            else:
                return None
        except:
            return None

    try:
        df = pd.read_csv(filepath, sep='\t', dtype={'GEOID': str})
        df.columns = df.columns.str.strip()
        lat_col = [c for c in df.columns if 'INTPTLAT' in c][0]
        lon_col = [c for c in df.columns if 'INTPTLONG' in c][0]
        df = df.rename(columns={lat_col: 'LAT', lon_col: 'LON'})
        df['GEOID'] = df['GEOID'].astype(str).str.zfill(11) 
        return df[['GEOID', 'LAT', 'LON']]
    except Exception as e:
        print(f"Error parsing Gazetteer: {e}")
        return None

def calculate_demographic_score(stats):
    """
    Calculates a 5-point score for each metric and a total score /25.
    """
    
    scores = {}
    
    # 1. Population (3-mile basis, but we score whatever the user passed)
    # The rubric assumes a general "strong market" baseline.
    pop = stats['total_population']
    if pop > 75000: s_pop = 5
    elif pop >= 50000: s_pop = 4
    elif pop >= 35000: s_pop = 3
    elif pop >= 25000: s_pop = 2
    else: s_pop = 1
    scores['Population'] = s_pop
    
    # 2. Population Growth Rate (Annualized)
    growth = stats['growth_rate_annual'] * 100 # Convert to %
    if growth > 3: s_growth = 5
    elif growth >= 2: s_growth = 4
    elif growth >= 1: s_growth = 3
    elif growth >= 0: s_growth = 2
    else: s_growth = 1
    scores['Growth'] = s_growth
    
    # 3. Median Household Income
    inc = stats['median_household_income']
    if inc > 90000: s_inc = 5
    elif inc >= 75000: s_inc = 4
    elif inc >= 60000: s_inc = 3
    elif inc >= 50000: s_inc = 2
    else: s_inc = 1
    scores['Income'] = s_inc
    
    # 4. Renter Occupied %
    renter_pct = stats['renter_pct'] * 100
    if renter_pct > 40: s_rent = 5
    elif renter_pct >= 30: s_rent = 4
    elif renter_pct >= 25: s_rent = 3
    elif renter_pct >= 20: s_rent = 2
    else: s_rent = 1
    scores['Renter Demand'] = s_rent
    
    # 5. Age Demographics
    # Prime: 30-45
    age = stats['median_age']
    if 30 <= age <= 45: s_age = 5
    elif (25 <= age < 30) or (45 < age <= 50): s_age = 4
    elif (50 < age <= 60): s_age = 3
    elif (18 <= age < 25) or (60 < age): s_age = 2
    else: s_age = 1
    scores['Age'] = s_age
    
    scores['Total'] = sum(scores.values())
    return scores

def get_demographics_in_radius(lat, lon, radius_miles):
    state, county = get_fips_from_lat_lon(lat, lon)
    if not state: return None

    # --- 1. Fetch Current Data (2021 ACS) ---
    # B01003_001E: Total Pop
    # B19013_001E: Median Income
    # B01002_001E: Median Age
    # B25003_001E: Total Occupied Housing Units
    # B25003_003E: Renter Occupied
    vars_current = {
        'B01003_001E': 'POP_2021',
        'B19013_001E': 'INCOME',
        'B01002_001E': 'AGE',
        'B25003_001E': 'HOUSING_TOTAL',
        'B25003_003E': 'HOUSING_RENTER'
    }
    df_current = get_acs_data(2021, vars_current, state, county)
    
    # --- 2. Fetch Historical Data (2016 ACS) for Growth ---
    vars_hist = {'B01003_001E': 'POP_2016'}
    df_hist = get_acs_data(2016, vars_hist, state, county)
    
    # --- 3. Get Coords ---
    df_geo = get_gazetteer_coords(state)
    
    if df_current is None or df_geo is None:
        return {"total_population": 0, "error": "API Failure"}

    # --- 4. Merge All ---
    # Merge current with geo
    merged = pd.merge(df_current, df_geo, on='GEOID', how='inner')
    
    # Merge with history (optional, might have missing tracts)
    if df_hist is not None:
        merged = pd.merge(merged, df_hist[['GEOID', 'POP_2016']], on='GEOID', how='left')
    else:
        merged['POP_2016'] = merged['POP_2021'] # No growth assumed if API fails
        
    # --- 5. Filter & Aggregate ---
    total_pop_2021 = 0
    total_pop_2016 = 0
    
    weighted_income_sum = 0
    weighted_age_sum = 0
    
    total_households = 0
    total_renters = 0
    
    pop_for_avg = 0 # Denom for Age
    households_for_inc = 0 # Denom for Income
    
    center = (lat, lon)
    
    covered_tracts = []
    
    for _, row in merged.iterrows():
        try:
            dist = geodesic(center, (row['LAT'], row['LON'])).miles
            if dist <= radius_miles:
                p21 = row['POP_2021']
                p16 = row['POP_2016'] if pd.notnull(row['POP_2016']) else p21
                
                total_pop_2021 += p21
                total_pop_2016 += p16
                
                # Weighted Income
                inc = row['INCOME']
                hh = row['HOUSING_TOTAL']
                renters = row['HOUSING_RENTER']
                
                if inc > 0 and hh > 0:
                    weighted_income_sum += (inc * hh)
                    households_for_inc += hh
                    
                total_households += hh
                total_renters += renters
                
                # Weighted Age
                age = row['AGE']
                if age > 0 and p21 > 0:
                    weighted_age_sum += (age * p21)
                    pop_for_avg += p21
                    
                covered_tracts.append(row['GEOID'])
        except: continue
        
    # --- 6. Derived Metrics ---
    
    # Growth
    growth_5yr = 0
    if total_pop_2016 > 0:
        growth_5yr = (total_pop_2021 - total_pop_2016) / total_pop_2016
    growth_annual = growth_5yr / 5
    
    # Avg Income
    avg_income = 0
    if households_for_inc > 0:
        avg_income = weighted_income_sum / households_for_inc
        
    # Avg Age
    avg_age = 0
    if pop_for_avg > 0:
        avg_age = weighted_age_sum / pop_for_avg
        
    # Renter %
    renter_pct = 0
    if total_households > 0:
        renter_pct = total_renters / total_households
        
    results = {
        "total_population": int(total_pop_2021),
        "median_household_income": int(avg_income),
        "median_age": round(avg_age, 1),
        "renter_pct": round(renter_pct, 4),
        "growth_rate_annual": round(growth_annual, 4),
        "zip_count": len(covered_tracts),
        "zip_codes": covered_tracts
    }
    
    # Calculate Score
    results['scores'] = calculate_demographic_score(results)
    
    return results
