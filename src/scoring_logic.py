"""
Feasibility Scoring Engine
Based on: Allspace Storage - Self Storage Feasibility Inputs.xlsx - Scoring Guideline Tables.csv
"""

class FeasibilityScorer:
    """
    Strict scoring engine implementing the exact Allspace Storage rubric.
    Total: 100 points across 5 categories.
    """
    
    def __init__(self):
        self.scores = {
            "demographics": 0,
            "supply": 0,
            "site": 0,
            "competitor": 0,
            "economic": 0
        }
        # Store last inputs for PDF generation
        self.last_inputs = {
            "demographics": {},
            "supply": {},
            "site": {},
            "competitor": {},
            "economic": {}
        }
    
    # === DEMOGRAPHICS (25 points max) ===
    
    def score_population_3mi_with_rubric(self, population):
        """Population within 3-mile radius (5 points max) with rubric explanation"""
        if population >= 75000:
            return (5, 5, f"{population:,}", "Tier: ≥75,000 (5 pts)")
        elif population >= 50000:
            return (4, 5, f"{population:,}", "Tier: 50,000-74,999 (4 pts)")
        elif population >= 35000:
            return (3, 5, f"{population:,}", "Tier: 35,000-49,999 (3 pts)")
        elif population >= 25000:
            return (2, 5, f"{population:,}", "Tier: 25,000-34,999 (2 pts)")
        else:
            return (1, 5, f"{population:,}", "Tier: <25,000 (1 pt)")
    
    def score_median_income_with_rubric(self, income):
        """Median Household Income (5 points max) with rubric"""
        if income >= 75000:
            return (5, 5, f"${income:,}", "Tier: ≥$75,000 (5 pts)")
        elif income >= 60000:
            return (4, 5, f"${income:,}", "Tier: $60,000-$74,999 (4 pts)")
        elif income >= 50000:
            return (3, 5, f"${income:,}", "Tier: $50,000-$59,999 (3 pts)")
        elif income >= 40000:
            return (2, 5, f"${income:,}", "Tier: $40,000-$49,999 (2 pts)")
        else:
            return (1, 5, f"${income:,}", "Tier: <$40,000 (1 pt)")
    
    def score_population_growth_with_rubric(self, growth_rate):
        """Annual Population Growth Rate % (5 points max) with rubric"""
        if growth_rate >= 3.0:
            return (5, 5, f"{growth_rate:.1f}%", "Tier: ≥3.0% (5 pts)")
        elif growth_rate >= 2.0:
            return (4, 5, f"{growth_rate:.1f}%", "Tier: 2.0%-2.9% (4 pts)")
        elif growth_rate >= 1.0:
            return (3, 5, f"{growth_rate:.1f}%", "Tier: 1.0%-1.9% (3 pts)")
        elif growth_rate >= 0.5:
            return (2, 5, f"{growth_rate:.1f}%", "Tier: 0.5%-0.9% (2 pts)")
        else:
            return (1, 5, f"{growth_rate:.1f}%", "Tier: <0.5% (1 pt)")
    
    def score_renter_occupied_with_rubric(self, renter_pct):
        """Renter-Occupied Housing % (5 points max) with rubric"""
        if renter_pct >= 50:
            return (5, 5, f"{renter_pct}%", "Tier: ≥50% (5 pts)")
        elif renter_pct >= 40:
            return (4, 5, f"{renter_pct}%", "Tier: 40%-49% (4 pts)")
        elif renter_pct >= 30:
            return (3, 5, f"{renter_pct}%", "Tier: 30%-39% (3 pts)")
        elif renter_pct >= 20:
            return (2, 5, f"{renter_pct}%", "Tier: 20%-29% (2 pts)")
        else:
            return (1, 5, f"{renter_pct}%", "Tier: <20% (1 pt)")
    
    def score_age_demographics_with_rubric(self, pct_25_54):
        """% Population Age 25-54 (5 points max) with rubric"""
        if pct_25_54 >= 45:
            return (5, 5, f"{pct_25_54}%", "Tier: ≥45% (5 pts)")
        elif pct_25_54 >= 40:
            return (4, 5, f"{pct_25_54}%", "Tier: 40%-44% (4 pts)")
        elif pct_25_54 >= 35:
            return (3, 5, f"{pct_25_54}%", "Tier: 35%-39% (3 pts)")
        elif pct_25_54 >= 30:
            return (2, 5, f"{pct_25_54}%", "Tier: 30%-34% (2 pts)")
        else:
            return (1, 5, f"{pct_25_54}%", "Tier: <30% (1 pt)")
    
    # Legacy methods without rubric (for backward compatibility)
    def score_population_3mi(self, population):
        """Population within 3-mile radius (5 points max)"""
        return self.score_population_3mi_with_rubric(population)[0]
    
    def score_median_income(self, income):
        """Median Household Income (5 points max)"""
        return self.score_median_income_with_rubric(income)[0]
    
    def score_population_growth(self, growth_rate):
        """Annual Population Growth Rate % (5 points max)"""
        return self.score_population_growth_with_rubric(growth_rate)[0]
    
    def score_renter_occupied(self, renter_pct):
        """Renter-Occupied Housing % (5 points max)"""
        return self.score_renter_occupied_with_rubric(renter_pct)[0]
    
    def score_age_demographics(self, pct_25_54):
        """% Population Age 25-54 (5 points max)"""
        return self.score_age_demographics_with_rubric(pct_25_54)[0]
    
    def calculate_demographics_score(self, population, income, growth, renter_pct, age_pct):
        """Total Demographics Score (25 points max)"""
        # Store inputs for PDF generation
        self.last_inputs["demographics"] = {
            "population": population,
            "income": income,
            "growth": growth,
            "renter_pct": renter_pct,
            "age_pct": age_pct
        }
        total = (
            self.score_population_3mi(population) +
            self.score_median_income(income) +
            self.score_population_growth(growth) +
            self.score_renter_occupied(renter_pct) +
            self.score_age_demographics(age_pct)
        )
        self.scores["demographics"] = total
        return total
    
    def get_demographics_rubric(self, population, income, growth, renter_pct, age_pct):
        """Get detailed rubric breakdown for demographics"""
        return [
            ("Population (3mi)", *self.score_population_3mi_with_rubric(population)),
            ("Median Income", *self.score_median_income_with_rubric(income)),
            ("Growth Rate", *self.score_population_growth_with_rubric(growth)),
            ("Renter %", *self.score_renter_occupied_with_rubric(renter_pct)),
            ("Age 25-54 %", *self.score_age_demographics_with_rubric(age_pct))
        ]

    
    # === SUPPLY ANALYSIS (25 points max) ===
    
    def score_sf_per_capita_with_rubric(self, sf_per_capita):
        """Existing SF per Capita (8 points max) with rubric"""
        if sf_per_capita <= 4.0:
            return (8, 8, f"{sf_per_capita:.1f}", "Tier: ≤4.0 (8 pts)")
        elif sf_per_capita <= 5.5:
            return (6, 8, f"{sf_per_capita:.1f}", "Tier: 4.1-5.5 (6 pts)")
        elif sf_per_capita <= 7.0:
            return (4, 8, f"{sf_per_capita:.1f}", "Tier: 5.6-7.0 (4 pts)")
        elif sf_per_capita <= 8.5:
            return (2, 8, f"{sf_per_capita:.1f}", "Tier: 7.1-8.5 (2 pts)")
        else:
            return (0, 8, f"{sf_per_capita:.1f}", "Tier: >8.5 (0 pts)")
    
    def score_avg_occupancy_with_rubric(self, occupancy_pct):
        """Average Market Occupancy % (8 points max) with rubric"""
        if occupancy_pct >= 90:
            return (8, 8, f"{occupancy_pct}%", "Tier: ≥90% (8 pts)")
        elif occupancy_pct >= 85:
            return (6, 8, f"{occupancy_pct}%", "Tier: 85%-89% (6 pts)")
        elif occupancy_pct >= 80:
            return (4, 8, f"{occupancy_pct}%", "Tier: 80%-84% (4 pts)")
        elif occupancy_pct >= 75:
            return (2, 8, f"{occupancy_pct}%", "Tier: 75%-79% (2 pts)")
        else:
            return (0, 8, f"{occupancy_pct}%", "Tier: <75% (0 pts)")
    
    def score_absorption_trend_with_rubric(self, trend):
        """Absorption Trend (5 points max) with rubric"""
        trend_map = {
            "Strong": (5, 5, "Strong", "Strong Demand (5 pts)"),
            "Moderate": (3, 5, "Moderate", "Stable Demand (3 pts)"),
            "Weak": (2, 5, "Weak", "Fading Demand (2 pts)"),
            "Declining": (0, 5, "Declining", "Oversupplied (0 pts)")
        }
        return trend_map.get(trend, (0, 5, trend, "N/A"))
    
    def score_pipeline_risk_with_rubric(self, pipeline_sf_per_capita):
        """Pipeline Supply Risk (4 points max) with rubric"""
        if pipeline_sf_per_capita <= 0.5:
            return (4, 4, f"{pipeline_sf_per_capita:.1f}", "Tier: ≤0.5 SF/cap (4 pts)")
        elif pipeline_sf_per_capita <= 1.0:
            return (3, 4, f"{pipeline_sf_per_capita:.1f}", "Tier: 0.6-1.0 (3 pts)")
        elif pipeline_sf_per_capita <= 1.5:
            return (2, 4, f"{pipeline_sf_per_capita:.1f}", "Tier: 1.1-1.5 (2 pts)")
        elif pipeline_sf_per_capita <= 2.0:
            return (1, 4, f"{pipeline_sf_per_capita:.1f}", "Tier: 1.6-2.0 (1 pt)")
        else:
            return (0, 4, f"{pipeline_sf_per_capita:.1f}", "Tier: >2.0 (0 pts)")
    
    # Legacy methods
    def score_sf_per_capita(self, sf_per_capita):
        return self.score_sf_per_capita_with_rubric(sf_per_capita)[0]
    
    def score_avg_occupancy(self, occupancy_pct):
        return self.score_avg_occupancy_with_rubric(occupancy_pct)[0]
    
    def score_absorption_trend(self, trend):
        return self.score_absorption_trend_with_rubric(trend)[0]
    
    def score_pipeline_risk(self, pipeline_sf_per_capita):
        return self.score_pipeline_risk_with_rubric(pipeline_sf_per_capita)[0]
    
    def calculate_supply_score(self, sf_per_capita, occupancy, trend, pipeline):
        self.last_inputs["supply"] = {
            "sf_per_capita": sf_per_capita,
            "occupancy": occupancy,
            "trend": trend,
            "pipeline": pipeline
        }
        total = (
            self.score_sf_per_capita(sf_per_capita) +
            self.score_avg_occupancy(occupancy) +
            self.score_absorption_trend(trend) +
            self.score_pipeline_risk(pipeline)
        )
        self.scores["supply"] = total
        return total
    
    def get_supply_rubric(self, sf_per_capita, occupancy, trend, pipeline):
        return [
            ("SF per Capita", *self.score_sf_per_capita_with_rubric(sf_per_capita)),
            ("Avg Occupancy", *self.score_avg_occupancy_with_rubric(occupancy)),
            ("Absorption Trend", *self.score_absorption_trend_with_rubric(trend)),
            ("Pipeline Risk", *self.score_pipeline_risk_with_rubric(pipeline))
        ]

    
    # === SITE ATTRIBUTES (25 points max) ===
    
    def score_visibility_with_rubric(self, visibility):
        """Site Visibility (7 points max) with rubric"""
        v_map = {
            "Excellent": (7, 7, "Excellent", "Primary Road/Signal (7 pts)"),
            "Good": (5, 7, "Good", "Secondary Road (5 pts)"),
            "Fair": (3, 7, "Fair", "Tertiary Road (3 pts)"),
            "Poor": (1, 7, "Poor", "Hidden/Low Flow (1 pt)")
        }
        return v_map.get(visibility, (0, 7, visibility, "N/A"))
    
    def score_access_with_rubric(self, access):
        """Site Access (7 points max) with rubric"""
        a_map = {
            "Excellent": (7, 7, "Excellent", "Multiple Entry/Signal (7 pts)"),
            "Good": (5, 7, "Good", "Easy Turn-in (5 pts)"),
            "Fair": (3, 7, "Fair", "Right-in/Right-out (3 pts)"),
            "Poor": (1, 7, "Poor", "Difficult Access (1 pt)")
        }
        return a_map.get(access, (0, 7, access, "N/A"))
    
    def score_zoning_with_rubric(self, zoning_status):
        """Zoning Status (6 points max) with rubric"""
        z_map = {
            "Permitted": (6, 6, "Permitted", "By Right (6 pts)"),
            "Conditional": (4, 6, "Conditional", "SUP Required (4 pts)"),
            "Requires Variance": (2, 6, "Requires Variance", "Re-zoning Required (2 pts)")
        }
        return z_map.get(zoning_status, (0, 6, zoning_status, "N/A"))
    
    def score_site_size_with_rubric(self, size_adequacy):
        """Site Size Adequacy (5 points max) with rubric"""
        s_map = {
            "Ideal": (5, 5, "Ideal", "Plenty of room for expansion (5 pts)"),
            "Adequate": (4, 5, "Adequate", "Fits proposed NRA well (4 pts)"),
            "Marginal": (2, 5, "Marginal", "Tight for NRA / Topo issues (2 pts)"),
            "Insufficient": (0, 5, "Insufficient", "Too small for NRA (0 pts)")
        }
        return s_map.get(size_adequacy, (0, 5, size_adequacy, "N/A"))
    
    # Legacy methods
    def score_visibility(self, visibility):
        return self.score_visibility_with_rubric(visibility)[0]
    
    def score_access(self, access):
        return self.score_access_with_rubric(access)[0]
    
    def score_zoning(self, zoning):
        return self.score_zoning_with_rubric(zoning)[0]
    
    def score_site_size(self, size):
        return self.score_site_size_with_rubric(size)[0]
    
    def calculate_site_score(self, visibility, access, zoning, size):
        self.last_inputs["site"] = {
            "visibility": visibility,
            "access": access,
            "zoning": zoning,
            "size": size
        }
        total = (
            self.score_visibility(visibility) +
            self.score_access(access) +
            self.score_zoning(zoning) +
            self.score_site_size(size)
        )
        self.scores["site"] = total
        return total
    
    def get_site_rubric(self, visibility, access, zoning, size):
        return [
            ("Visibility", *self.score_visibility_with_rubric(visibility)),
            ("Access", *self.score_access_with_rubric(access)),
            ("Zoning", *self.score_zoning_with_rubric(zoning)),
            ("Site Size", *self.score_site_size_with_rubric(size))
        ]

    
    # === COMPETITOR ANALYSIS (15 points max) ===
    
    def score_competitor_count_with_rubric(self, count_within_3mi):
        """Number of Competitors within 3 miles (5 points max) with rubric"""
        if count_within_3mi <= 2:
            return (5, 5, str(count_within_3mi), "Tier: ≤2 (5 pts)")
        elif count_within_3mi <= 4:
            return (4, 5, str(count_within_3mi), "Tier: 3-4 (4 pts)")
        elif count_within_3mi <= 6:
            return (3, 5, str(count_within_3mi), "Tier: 5-6 (3 pts)")
        elif count_within_3mi <= 8:
            return (2, 5, str(count_within_3mi), "Tier: 7-8 (2 pts)")
        else:
            return (1, 5, str(count_within_3mi), "Tier: >8 (1 pt)")
    
    def score_competitor_quality_with_rubric(self, quality):
        """Competitor Quality (5 points max) with rubric"""
        q_map = {
            "Aging/Poor": (5, 5, "Aging/Poor", "Vulnerable targets (5 pts)"),
            "Average": (3, 5, "Average", "Standard competition (3 pts)"),
            "Modern/Strong": (1, 5, "Modern/Strong", "Best-in-class assets (1 pt)")
        }
        return q_map.get(quality, (0, 5, quality, "N/A"))
    
    def score_pricing_power_with_rubric(self, pricing_position):
        """Pricing Power (5 points max) with rubric"""
        p_map = {
            "Above Market": (5, 5, "Above Market", "Premium pricing possible (5 pts)"),
            "At Market": (3, 5, "At Market", "Competitive pricing (3 pts)"),
            "Below Market": (1, 5, "Below Market", "Pricing constraints (1 pt)")
        }
        return p_map.get(pricing_position, (0, 5, pricing_position, "N/A"))
    
    # Legacy methods
    def score_competitor_count(self, count):
        return self.score_competitor_count_with_rubric(count)[0]
    
    def score_competitor_quality(self, quality):
        return self.score_competitor_quality_with_rubric(quality)[0]
    
    def score_pricing_power(self, pricing):
        return self.score_pricing_power_with_rubric(pricing)[0]
    
    def calculate_competitor_score(self, count, quality, pricing):
        self.last_inputs["competitor"] = {
            "count": count,
            "quality": quality,
            "pricing": pricing
        }
        total = (
            self.score_competitor_count(count) +
            self.score_competitor_quality(quality) +
            self.score_pricing_power(pricing)
        )
        self.scores["competitor"] = total
        return total
    
    def get_competitor_rubric(self, count, quality, pricing):
        return [
            ("Competitor Count", *self.score_competitor_count_with_rubric(count)),
            ("Competitor Quality", *self.score_competitor_quality_with_rubric(quality)),
            ("Pricing Power", *self.score_pricing_power_with_rubric(pricing))
        ]

    
    # === ECONOMIC INDICATORS (10 points max) ===
    
    def score_unemployment_with_rubric(self, unemployment_rate):
        """Unemployment Rate % (4 points max) with rubric"""
        if unemployment_rate <= 3.5:
            return (4, 4, f"{unemployment_rate}%", "Tier: ≤3.5% (4 pts)")
        elif unemployment_rate <= 5.0:
            return (3, 4, f"{unemployment_rate}%", "Tier: 3.6%-5.0% (3 pts)")
        elif unemployment_rate <= 6.5:
            return (2, 4, f"{unemployment_rate}%", "Tier: 5.1%-6.5% (2 pts)")
        elif unemployment_rate <= 8.0:
            return (1, 4, f"{unemployment_rate}%", "Tier: 6.6%-8.0% (1 pt)")
        else:
            return (0, 4, f"{unemployment_rate}%", "Tier: >8.0% (0 pts)")
    
    def score_business_growth_with_rubric(self, growth_trend):
        """Business Growth Trend (3 points max) with rubric"""
        g_map = {
            "Strong": (3, 3, "Strong", "Strong Corporate Expansion (3 pts)"),
            "Moderate": (2, 3, "Moderate", "Steady Local Growth (2 pts)"),
            "Weak": (1, 3, "Weak", "Stagnant Economy (1 pt)")
        }
        return g_map.get(growth_trend, (0, 3, growth_trend, "N/A"))
    
    def score_economic_stability_with_rubric(self, stability):
        """Economic Stability (3 points max) with rubric"""
        s_map = {
            "Stable": (3, 3, "Stable", "Diverse Industry Base (3 pts)"),
            "Moderate": (2, 3, "Moderate", "Some Concentration Risk (2 pts)"),
            "Volatile": (1, 3, "Volatile", "Single-Industry Dependent (1 pt)")
        }
        return s_map.get(stability, (0, 3, stability, "N/A"))
    
    # Legacy methods
    def score_unemployment(self, rate):
        return self.score_unemployment_with_rubric(rate)[0]
    
    def score_business_growth(self, trend):
        return self.score_business_growth_with_rubric(trend)[0]
    
    def score_economic_stability(self, stability):
        return self.score_economic_stability_with_rubric(stability)[0]
    
    def calculate_economic_score(self, unemployment, business_growth, stability):
        self.last_inputs["economic"] = {
            "unemployment": unemployment,
            "business_growth": business_growth,
            "stability": stability
        }
        total = (
            self.score_unemployment(unemployment) +
            self.score_business_growth(business_growth) +
            self.score_economic_stability(stability)
        )
        self.scores["economic"] = total
        return total
    
    def get_economic_rubric(self, unemployment, growth, stability):
        return [
            ("Unemployment", *self.score_unemployment_with_rubric(unemployment)),
            ("Business Growth", *self.score_business_growth_with_rubric(growth)),
            ("Economic Stability", *self.score_economic_stability_with_rubric(stability))
        ]

    
    # === TOTAL SCORE ===
    
    def get_total_score(self):
        """Calculate total feasibility score (100 points max)"""
        return sum(self.scores.values())
    
    def get_recommendation(self):
        """Get recommendation based on total score"""
        total = self.get_total_score()
        
        if total >= 80:
            return {
                "decision": "PROCEED",
                "confidence": "High",
                "message": "Strong acquisition candidate. Proceed with LOI."
            }
        elif total >= 65:
            return {
                "decision": "PROCEED WITH CAUTION",
                "confidence": "Moderate",
                "message": "Conditional interest. Requires additional due diligence."
            }
        else:
            return {
                "decision": "PASS",
                "confidence": "Low",
                "message": "Does not meet minimum feasibility thresholds."
            }
    
    def get_score_breakdown(self):
        """Return detailed score breakdown"""
        return {
            "Demographics": {"score": self.scores["demographics"], "max": 25},
            "Supply Analysis": {"score": self.scores["supply"], "max": 25},
            "Site Attributes": {"score": self.scores["site"], "max": 25},
            "Competitor Analysis": {"score": self.scores["competitor"], "max": 15},
            "Economic Indicators": {"score": self.scores["economic"], "max": 10},
            "Total": {"score": self.get_total_score(), "max": 100}
        }
    
    def get_rubric_dict(self):
        """
        Return complete rubric definitions for all categories.
        Shows the full "Good vs Bad" scoring standards.
        """
        return {
            "Demographics": {
                "Population (3mi)": "5pts: ≥75,000 | 4pts: 50,000-74,999 | 3pts: 35,000-49,999 | 2pts: 25,000-34,999 | 1pt: <25,000",
                "Median Income": "5pts: ≥$75,000 | 4pts: $60,000-$74,999 | 3pts: $50,000-$59,999 | 2pts: $40,000-$49,999 | 1pt: <$40,000",
                "Growth Rate": "5pts: ≥3.0% | 4pts: 2.0%-2.9% | 3pts: 1.0%-1.9% | 2pts: 0.5%-0.9% | 1pt: <0.5%",
                "Renter %": "5pts: ≥50% | 4pts: 40%-49% | 3pts: 30%-39% | 2pts: 20%-29% | 1pt: <20%",
                "Age 25-54 %": "5pts: ≥45% | 4pts: 40%-44% | 3pts: 35%-39% | 2pts: 30%-34% | 1pt: <30%"
            },
            "Supply": {
                "SF per Capita": "8pts: ≤4.0 | 6pts: 4.1-5.5 | 4pts: 5.6-7.0 | 2pts: 7.1-8.5 | 0pts: >8.5",
                "Avg Occupancy": "8pts: ≥90% | 6pts: 85%-89% | 4pts: 80%-84% | 2pts: 75%-79% | 0pts: <75%",
                "Absorption Trend": "5pts: Strong | 3pts: Moderate | 2pts: Weak | 0pts: Declining",
                "Pipeline Risk": "4pts: ≤0.5 SF/cap | 3pts: 0.6-1.0 | 2pts: 1.1-1.5 | 1pt: 1.6-2.0 | 0pts: >2.0"
            },
            "Site": {
                "Visibility": "7pts: Excellent | 5pts: Good | 3pts: Fair | 1pt: Poor",
                "Access": "7pts: Excellent | 5pts: Good | 3pts: Fair | 1pt: Poor",
                "Zoning": "6pts: Permitted | 4pts: Conditional | 2pts: Requires Variance",
                "Size Adequacy": "5pts: Ideal | 4pts: Adequate | 2pts: Marginal | 0pts: Insufficient"
            },
            "Competitor": {
                "Count (3mi)": "5pts: ≤2 | 4pts: 3-4 | 3pts: 5-6 | 2pts: 7-8 | 1pt: >8",
                "Quality": "5pts: Aging/Poor | 3pts: Average | 1pt: Modern/Strong",
                "Pricing Power": "5pts: Above Market | 3pts: At Market | 1pt: Below Market"
            },
            "Economic": {
                "Unemployment": "4pts: ≤3.5% | 3pts: 3.6%-5.0% | 2pts: 5.1%-6.5% | 1pt: 6.6%-8.0% | 0pts: >8.0%",
                "Business Growth": "3pts: Strong | 2pts: Moderate | 1pt: Weak",
                "Economic Stability": "3pts: Stable | 2pts: Moderate | 1pt: Volatile"
            }
        }
