class UnitMixOptimizer:
    # Constants
    DEMAND_PER_CAPITA = 7.0  # sqft per person
    
    # Base "Suburban" Profile
    BASE_PREFERENCES = {
        "5x5": 0.10,
        "10x10": 0.40,
        "10x20": 0.35,
        "Climate": 0.15,
        "Boat_RV": 0.00
    }
    
    AVG_COMPETITOR_SIZE = 40000  # sqft

    def __init__(self, population, competitors, demographics=None):
        """
        Initializes the optimizer.
        :param population: int, Total trade area population
        :param competitors: list of dicts, Competitor data from scraper
        :param demographics: dict, Optional rich data (renter_pct, etc.)
        """
        self.population = population
        self.competitors = competitors
        self.demographics = demographics or {} # defaults to empty

    def get_adjusted_mix_ratios(self):
        """
        Adjusts the base mix based on demographic profile.
        """
        mix = self.BASE_PREFERENCES.copy()
        market_type = "Suburban (Standard)"
        
        # Extract constraints
        renter_pct = self.demographics.get('renter_pct', 0.35) # default 35%
        # Use provided population if available in demo, otherwise the passed int
        pop = self.demographics.get('total_population', self.population)
        
        # 1. URBAN / HIGH DENSITY PROFILE
        # High Renters implies apartments -> Need small overflow storage (5x5) and Climate Control
        if renter_pct > 0.45:
            market_type = "Urban / High Density"
            # Shift 15% from Large to Small/Climate
            mix["5x5"] += 0.10
            mix["Climate"] += 0.10
            mix["10x20"] -= 0.20
            
        # 2. RURAL / TERTIARY PROFILE
        # Low Pop implies houses with land -> Need "Toy" storage (Boats, RVs, Tractors)
        elif pop < 25000:
            market_type = "Tertiary / Rural"
            # Shift 20% from Small/10x10 to Large/RV
            mix["5x5"] -= 0.05
            mix["10x10"] -= 0.10
            mix["10x20"] += 0.05
            mix["Boat_RV"] = 0.10 # Add RV parking
            
        # Clean up negative floats just in case
        total = sum(mix.values())
        return {k: v/total for k, v in mix.items()}, market_type

    def calculate_optimal_mix(self):
        """
        Calculates the gap between demand and supply to recommend unit mix.
        """
        # Get Dynamic Ratios
        target_ratios, market_desc = self.get_adjusted_mix_ratios()
        
        # 1. Calculate Total Demand
        total_sqft_demand = self.population * self.DEMAND_PER_CAPITA
        
        # 2. Breakdown Demand by Unit Type
        demand_by_type = {
            k: total_sqft_demand * v 
            for k, v in target_ratios.items()
        }

        # 3. Estimate Supply
        # Realistically, we don't know the exact unit mix of competitors.
        # We assume they have a "standard" mix proportional to our preferences
        # for the sake of estimation, applied to their total sqft.
        total_supply_sqft = 0
        for comp in self.competitors:
            size = comp.get('Size', self.AVG_COMPETITOR_SIZE)
            total_supply_sqft += size
        
        # Pro-rate supply across types (Assumption)
        supply_by_type = {
            k: total_supply_sqft * v 
            for k, v in target_ratios.items()
        }

        # 4. Calculate Gap
        gap_by_type = {}
        for k in target_ratios.keys():
            demand = demand_by_type[k]
            supply = supply_by_type.get(k, 0)
            gap = demand - supply
            # Ensure no negative recommendations (oversupply = 0 new units)
            gap_by_type[k] = max(0, gap)

        # 5. Convert Gap SqFt to Unit Count
        unit_sqft_map = {
            "5x5": 25,
            "10x10": 100,
            "10x20": 200,
            "Climate": 100,
            "Boat_RV": 360 # 12x30
        }
        
        recommended_units = {}
        total_new_sqft = 0
        
        for k, sqft_gap in gap_by_type.items():
            unit_size = unit_sqft_map.get(k, 100)
            count = int(sqft_gap / unit_size)
            if count > 0:
                recommended_units[k] = count
                total_new_sqft += (count * unit_size)

        return {
            "recommended_units": recommended_units,
            "total_new_sqft": total_new_sqft,
            "market_profile": market_desc, # Inform user
            "details": {
                "total_demand": total_sqft_demand,
                "total_supply": total_supply_sqft,
                "gap_sqft": gap_by_type
            }
        }
