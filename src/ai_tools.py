from vertexai.generative_models import FunctionDeclaration, Tool
from src.scraper import get_exact_coords
from src.demographics import get_demographics_in_radius
from src.financials import FinancialModel
from src.forecast import RevenueForecaster

# --- WRAPPER FUNCTIONS ---
# These functions will be called by the Vertex AI Agent orchestrator.

def get_coordinates(address: str):
    """
    Finds exact GPS coordinates for a given mailing address.
    """
    lat, lon = get_exact_coords(address)
    return {"lat": lat, "lon": lon}

def get_market_metrics(lat: float, lon: float, radius_miles: int = 3):
    """
    Fetches demographic data (population, income, growth) for a specific location and radius.
    """
    data = get_demographics_in_radius(lat, lon, radius_miles)
    if data:
        # Return a summarized version for the LLM to process easily
        return {
            "population": data.get("total_population"),
            "median_income": data.get("median_household_income"),
            "growth_rate": data.get("growth_rate_annual"),
            "suitability_score": data.get("scores", {}).get("Total"),
            "tracts_included": data.get("zip_count")
        }
    return {"error": "Could not fetch demographics for this location."}

def calculate_project_returns(land_cost: float, build_cost_sqft: float, rentable_sqft: float, avg_rent: float):
    """
    Calculates development pro-forma metrics including Total Cost, NOI, and Yield on Cost.
    """
    model = FinancialModel(
        land_cost=land_cost,
        construction_cost_per_sqft=build_cost_sqft,
        rentable_sqft=rentable_sqft,
        avg_rent_per_sqft=avg_rent
    )
    returns = model.get_returns()
    metrics = model.calculate_noi()
    return {**returns, **metrics}

def forecast_lease_up(current_occupancy: float, speed: str = "Medium", target_stabilization: float = 0.92):
    """
    Predicts the lease-up trajectory and revenue stabilization timeline.
    """
    forecaster = RevenueForecaster()
    # speed mapping
    df = forecaster.predict_revenue(
        current_occupancy=current_occupancy,
        target_occupancy=target_stabilization,
        speed_period=speed
    )
    # Return summary stats for the AI
    year_3_occ = df[df['Month'] == 36]['P50_Occupancy'].values[0]
    return {
        "stabilization_month_36": f"{year_3_occ:.1%}",
        "narrative_summary": forecaster.generate_narrative(df)
    }

def run_feasibility_pipeline(address: str, radius_miles: int = 3):
    """
    Executes the full feasibility study pipeline: geocoding, competitive scouting, demographics, 
    and preliminary financial returns.
    """
    from src.scraper import get_competitors_dragnet
    
    # 1. Geocode
    lat, lon = get_exact_coords(address)
    if not lat:
        return {"error": "Address not found."}
    
    # 2. Competitors
    comps = get_competitors_dragnet(lat, lon)
    
    # 3. Demographics
    demo = get_demographics_in_radius(lat, lon, radius_miles)
    
    # 4. Preliminary Financials (Using defaults for initial study)
    model = FinancialModel(
        land_cost=1000000,
        construction_cost_per_sqft=80,
        rentable_sqft=65000,
        avg_rent_per_sqft=1.65
    )
    returns = model.get_returns()
    metrics = model.calculate_noi()
    
    return {
        "status": "success",
        "location": {"lat": lat, "lon": lon, "address": address},
        "market_summary": f"Found {len(comps)} competitors within radius.",
        "demographics": {
            "population": demo.get("total_population"),
            "suitability_score": demo.get("scores", {}).get("Total")
        },
        "financials": {**returns, **metrics},
        "raw_data": {
            "competitors": comps,
            "demo_full": demo
        }
    }

# --- VERTEX AI DECLARATIONS ---

run_pipeline_tool = FunctionDeclaration(
    name="run_feasibility_pipeline",
    description="Run a full automated feasibility study for a site. This includes geocoding, competitor search, and demographics. Use this for 'Analyze X' or 'Run a study for X' queries.",
    parameters={
        "type": "object",
        "properties": {
            "address": {"type": "string", "description": "The site address."},
            "radius_miles": {"type": "integer", "description": "Analysis radius (default 3)."}
        },
        "required": ["address"]
    }
)

get_coords_tool = FunctionDeclaration(
# ... (rest of the file)
    name="get_coordinates",
    description="Get GPS coordinates for an address. Use this first when a user asks about a specific site location.",
    parameters={
        "type": "object",
        "properties": {
            "address": {"type": "string", "description": "The full address of the potential development site."}
        },
        "required": ["address"]
    }
)

get_market_tool = FunctionDeclaration(
    name="get_market_metrics",
    description="Get demographic and market metrics for a latitude/longitude point.",
    parameters={
        "type": "object",
        "properties": {
            "lat": {"type": "number", "description": "Latitude coordinate."},
            "lon": {"type": "number", "description": "Longitude coordinate."},
            "radius_miles": {"type": "integer", "description": "Analysis radius in miles (default 3)."}
        },
        "required": ["lat", "lon"]
    }
)

calculate_returns_tool = FunctionDeclaration(
    name="calculate_project_returns",
    description="Run a financial pro-forma analysis for a self-storage project.",
    parameters={
        "type": "object",
        "properties": {
            "land_cost": {"type": "number", "description": "Cost to acquire the land."},
            "build_cost_sqft": {"type": "number", "description": "Construction cost per square foot."},
            "rentable_sqft": {"type": "number", "description": "Total net rentable square footage."},
            "avg_rent": {"type": "number", "description": "Weighted average rent per square foot per month."}
        },
        "required": ["land_cost", "build_cost_sqft", "rentable_sqft", "avg_rent"]
    }
)

forecast_lease_up_tool = FunctionDeclaration(
    name="forecast_lease_up",
    description="Forecast the revenue and occupancy trajectory for a new facility.",
    parameters={
        "type": "object",
        "properties": {
            "current_occupancy": {"type": "number", "description": "Starting occupancy (0.0 to 1.0)."},
            "speed": {"type": "string", "enum": ["Slow", "Medium", "Fast"], "description": "Predicted lease-up pace."},
            "target_stabilization": {"type": "number", "description": "Target stabilized occupancy (e.g. 0.90)."}
        },
        "required": ["current_occupancy"]
    }
)

# Combined Toolset
feasibility_tools = Tool(
    function_declarations=[
        run_pipeline_tool,
        get_coords_tool,
        get_market_tool,
        calculate_returns_tool,
        forecast_lease_up_tool
    ]
)
