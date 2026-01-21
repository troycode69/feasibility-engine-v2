from dataclasses import dataclass, field
from typing import List
import random
import pandas as pd

@dataclass
class Competitor:
    name: str
    address: str
    distance_miles: float
    nrsf: float
    occupancy_pct: float
    rate_10x10_cc: float
    rate_10x10_std: float
    website: str = ""
    lat: float = 0.0
    lon: float = 0.0

@dataclass
class CompetitorStats:
    total_supply_sf: float
    avg_occupancy_pct: float
    avg_rate_cc: float
    avg_rate_std: float
    count: int

class CompetitorManager:
    def __init__(self):
        pass

    def get_competitors(self, center_lat, center_lon) -> List[Competitor]:
        """
        Generates 5 realistic, varied mock competitors to simulate a diverse market.
        Variations:
        1. The "REIT" (High Rate, High Occ)
        2. The "Value Player" (Low Rate, High Occ)
        3. The "New Class A" (High Rate, Low Occ - Lease Up)
        4. The "Mom & Pop" (Low Rate, Med Occ, No Website)
        5. The "Aggressor" (Med Rate, High Occ)
        """
        import random
        
        profiles = [
            # Brand, Base Rate, Occ Range, Age profile
            ("Public Storage", 185, (92, 96), "Established REIT"),
            ("U-Haul Moving & Storage", 145, (90, 95), "Value Value"),
            ("CubeSmart (New Build)", 195, (45, 65), "Lease-Up Phase"),
            ("A-1 Self Storage", 135, (85, 90), "Vintage / Mom & Pop"),
            ("Extra Space Storage", 175, (88, 93), "Institutional"),
            ("Life Storage", 165, (90, 94), "Institutional"),
            ("Space Shop Self Storage", 180, (85, 90), "Class A Regional"),
            ("Secure-It Storage", 125, (80, 85), "Vintage / Drive-Up"),
            ("Morningstar Storage", 190, (88, 92), "Premium Class A"),
            ("Budget Storage", 115, (95, 98), "Value / Low Amenity"),
            ("Mid-Town Storage", 155, (85, 90), "Urban Infill"),
            ("SmartStop Self Storage", 170, (89, 93), "Institutional")
        ]
        
        # Realistic local street names (Mocking realism)
        streets = [
            "Main St", "Market St", "South Rd", "North Ave", "Cherry St", 
            "Washington St", "Liberty Dr", "Commerce Blvd", "Industrial Park Rd", 
            "Route 9", "Manchester Rd", "Raymond Ave", "College Ave", 
            "Creek Rd", "Violet Ave", "Salt Point Turnpike", "Van Wagner Rd"
        ]
        
        comps = []
        for i, (name, base_rate, occ_range, notes) in enumerate(profiles):
            # Seed for deterministic location
            seed = int((center_lat + center_lon + i) * 1000)
            random.seed(seed)
            
            # Pick a random street
            street = streets[i % len(streets)]
            st_num = random.randint(100, 2000)
            
            # Distance: 0.5 to 4.5 miles
            dist = 0.5 + (random.random() * 4.0)
            
            # NRSF: 40k to 110k
            nrsf = random.randint(40, 110) * 1000
            
            # Occupancy
            occ = random.uniform(occ_range[0], occ_range[1])
            
            # Rate variation
            # Closer to site = slightly higher rate?
            dist_premium = max(0, (2.0 - dist) * 10) # +$10 if < 2 miles
            final_rate_cc = base_rate + dist_premium + random.randint(-5, 5)
            
            # Standard Rate discount
            final_rate_std = final_rate_cc * 0.78
            
            # Mock Lat/Lon offset
            lat_off = (random.random() - 0.5) * 0.08
            lon_off = (random.random() - 0.5) * 0.08
            
            comp = Competitor(
                name=name,
                address=f"{st_num} {street} ({notes})",
                distance_miles=round(dist, 2),
                nrsf=nrsf,
                occupancy_pct=round(occ, 1),
                rate_10x10_cc=round(final_rate_cc, 0),
                rate_10x10_std=round(final_rate_std, 0),
                lat=center_lat + lat_off,
                lon=center_lon + lon_off
            )
            comps.append(comp)
            
        return sorted(comps, key=lambda x: x.distance_miles)

    def calculate_stats(self, competitors: List[Competitor]) -> CompetitorStats:
        if not competitors:
            return CompetitorStats(0, 0, 0, 0, 0)
            
        total_sf = sum(c.nrsf for c in competitors)
        
        # Weighted Average Occupancy
        w_occ = sum(c.occupancy_pct * c.nrsf for c in competitors) / total_sf
        
        # Simple Average Rates
        avg_cc = sum(c.rate_10x10_cc for c in competitors) / len(competitors)
        avg_std = sum(c.rate_10x10_std for c in competitors) / len(competitors)
        
        return CompetitorStats(
            total_supply_sf=total_sf,
            avg_occupancy_pct=w_occ,
            avg_rate_cc=avg_cc,
            avg_rate_std=avg_std,
            count=len(competitors)
        )
