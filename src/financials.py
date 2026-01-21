import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class FinancialModel:
    def __init__(self, land_cost, construction_cost_per_sqft, rentable_sqft, avg_rent_per_sqft):
        self.land_cost = land_cost
        self.construction_cost_per_sqft = construction_cost_per_sqft
        self.rentable_sqft = rentable_sqft
        self.avg_rent_per_sqft = avg_rent_per_sqft

    def calculate_noi(self):
        """Calculates Net Operating Income (NOI)."""
        gross_potential_income = self.rentable_sqft * self.avg_rent_per_sqft * 12
        operating_expenses = gross_potential_income * 0.35  # 35% opex
        noi = gross_potential_income - operating_expenses
        
        return {
            "NOI": noi,
            "Gross Revenue": gross_potential_income,
            "Operating Expenses": operating_expenses
        }

    def get_returns(self):
        """Calculates return metrics."""
        total_development_cost = self.land_cost + (self.rentable_sqft * self.construction_cost_per_sqft)
        noi = self.calculate_noi()["NOI"]
        yield_on_cost = (noi / total_development_cost) * 100
        
        market_cap_rate = 0.065
        stabilized_value = noi / market_cap_rate
        equity_created = stabilized_value - total_development_cost

        return {
            "Total Cost": total_development_cost,
            "Yield on Cost": round(yield_on_cost, 2),
            "Stabilized Value": stabilized_value,
            "Equity Created": equity_created
        }

def recommend_unit_mix(market_type, total_sqft, sf_per_capita=None):
    """
    Recommends unit mix based on market type and supply/demand metrics.
    
    Args:
        market_type: "Urban" or "Tertiary"
        total_sqft: Total rentable square footage
        sf_per_capita: Optional SF per capita metric for supply/demand analysis
    
    Returns:
        tuple: (DataFrame with recommended unit mix, strategy message)
    """
    
    # Determine market strategy based on supply/demand
    strategy_message = ""
    size_adjustment = 1.0
    climate_boost = False
    
    if sf_per_capita is not None:
        if sf_per_capita < 5.0:
            # UNDERSUPPLIED MARKET - Aggressive build
            strategy_message = f"🟢 **Market is Undersupplied** ({sf_per_capita:.1f} SF/cap). **Recommended Strategy:** Maximize Density (Multistory Climate Control). Go aggressive with size and amenities."
            size_adjustment = 1.25  # 25% larger facility
            climate_boost = True
        elif sf_per_capita > 8.0:
            # OVERSUPPLIED MARKET - Conservative build
            strategy_message = f"🔴 **Market is Oversupplied** ({sf_per_capita:.1f} SF/cap). **Recommended Strategy:** Conservative Build (Drive-Up Focus). Minimize capital outlay, focus on cost efficiency."
            size_adjustment = 0.65  # 35% smaller facility
            climate_boost = False
        else:
            # BALANCED MARKET
            strategy_message = f"🟡 **Market is Balanced** ({sf_per_capita:.1f} SF/cap). **Recommended Strategy:** Standard mixed-use facility."
    
    # Adjust total sqft based on market conditions
    adjusted_sqft = total_sqft * size_adjustment
    
    if market_type == "Urban":
        # Urban: More small units, climate controlled
        if climate_boost:
            # Aggressive urban: even more climate control
            mix = {
                "Unit Type": ["5x5", "5x10", "10x10", "10x15", "10x20"],
                "% of Total": [30, 35, 20, 10, 5],
                "Climate Controlled": ["Yes", "Yes", "Yes", "Yes", "Yes"]
            }
        else:
            mix = {
                "Unit Type": ["5x5", "5x10", "10x10", "10x15", "10x20"],
                "% of Total": [25, 30, 25, 15, 5],
                "Climate Controlled": ["Yes", "Yes", "Yes", "Yes", "No"]
            }
    else:  # Tertiary
        # Tertiary: More large units
        if climate_boost:
            # Aggressive tertiary: balanced climate/drive-up
            mix = {
                "Unit Type": ["5x10", "10x10", "10x15", "10x20", "10x30"],
                "% of Total": [15, 25, 30, 20, 10],
                "Climate Controlled": ["Yes", "Yes", "Yes", "No", "No"]
            }
        else:
            # Conservative tertiary: more drive-up
            mix = {
                "Unit Type": ["5x10", "10x10", "10x15", "10x20", "10x30"],
                "% of Total": [10, 20, 30, 25, 15],
                "Climate Controlled": ["No", "Yes", "No", "No", "No"]
            }
    
    df = pd.DataFrame(mix)
    df["Square Feet"] = adjusted_sqft * df["% of Total"] / 100
    df["# of Units"] = (df["Square Feet"] / df["Unit Type"].str.replace("x", "*").apply(eval)).astype(int)
    
    return df, strategy_message

def generate_pro_forma(total_cost, total_sqft, avg_rate_psf, stabilized_occ=90, cap_rate=7.5):
    """
    Generates comprehensive pro forma with monthly Year 1 and annual Years 2-7.
    
    Args:
        total_cost: Total development cost
        total_sqft: Total rentable SF
        avg_rate_psf: Average monthly rate per SF
        stabilized_occ: Stabilized occupancy %
        cap_rate: Exit cap rate %
    
    Returns:
        Dictionary with monthly_y1 and annual_y2_7 DataFrames
    """
    
    # === YEAR 1: MONTHLY PRO FORMA ===
    months = []
    start_date = datetime.now()
    
    for month in range(1, 13):
        # Lease-up curve: 0% -> 90% over 12 months
        occupancy = min((month / 12) * stabilized_occ, stabilized_occ)
        
        occupied_sf = total_sqft * (occupancy / 100)
        gross_revenue = occupied_sf * avg_rate_psf
        
        # Operating expenses (35% of revenue)
        opex = gross_revenue * 0.35
        noi = gross_revenue - opex
        
        # Debt service (assume 70% LTV, 6% rate, 25yr amortization)
        loan_amount = total_cost * 0.70
        monthly_payment = loan_amount * (0.06/12) / (1 - (1 + 0.06/12)**(-25*12))
        
        cash_flow = noi - monthly_payment
        
        months.append({
            "Month": month,
            "Date": (start_date + timedelta(days=30*month)).strftime("%b %Y"),
            "Occupancy %": round(occupancy, 1),
            "Gross Revenue": round(gross_revenue, 0),
            "Operating Expenses": round(opex, 0),
            "NOI": round(noi, 0),
            "Debt Service": round(monthly_payment, 0),
            "Cash Flow": round(cash_flow, 0)
        })
    
    monthly_df = pd.DataFrame(months)
    
    # === YEARS 2-7: ANNUAL PRO FORMA ===
    years = []
    
    for year in range(2, 8):
        # Assume 2% annual rent growth, stabilized occupancy
        growth_factor = 1.02 ** (year - 1)
        
        occupied_sf = total_sqft * (stabilized_occ / 100)
        gross_revenue = occupied_sf * avg_rate_psf * 12 * growth_factor
        
        opex = gross_revenue * 0.35
        noi = gross_revenue - opex
        
        # Annual debt service
        loan_amount = total_cost * 0.70
        monthly_payment = loan_amount * (0.06/12) / (1 - (1 + 0.06/12)**(-25*12))
        annual_debt_service = monthly_payment * 12
        
        cash_flow = noi - annual_debt_service
        
        # Calculate property value at exit (Year 7)
        if year == 7:
            exit_value = noi / (cap_rate / 100)
            equity_multiple = exit_value / (total_cost * 0.30)  # On equity invested
        else:
            exit_value = 0
            equity_multiple = 0
        
        years.append({
            "Year": year,
            "Occupancy %": stabilized_occ,
            "Gross Revenue": round(gross_revenue, 0),
            "Operating Expenses": round(opex, 0),
            "NOI": round(noi, 0),
            "Debt Service": round(annual_debt_service, 0),
            "Cash Flow": round(cash_flow, 0),
            "Exit Value": round(exit_value, 0) if year == 7 else "",
            "Equity Multiple": round(equity_multiple, 2) if year == 7 else ""
        })
    
    annual_df = pd.DataFrame(years)
    
    return {
        "monthly_y1": monthly_df,
        "annual_y2_7": annual_df,
        "summary": {
            "Total Development Cost": total_cost,
            "Year 1 Total Revenue": monthly_df["Gross Revenue"].sum(),
            "Year 1 Total NOI": monthly_df["NOI"].sum(),
            "Stabilized NOI": annual_df[annual_df["Year"] == 2]["NOI"].values[0],
            "Exit Cap Rate": cap_rate,
            "Exit Value": annual_df[annual_df["Year"] == 7]["Exit Value"].values[0]
        }
    }
