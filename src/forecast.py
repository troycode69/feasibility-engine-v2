import pandas as pd
import numpy as np
import random

class RevenueForecaster:
    def __init__(self):
        self.history_data = None
        self.model_params = None

    def generate_synthetic_history(self, n_sites=50, months=84):
        """
        Generates dummy historical data for 'similar' storage sites.
        Simulates lease-up curves using a logistic function with noise.
        """
        history = []
        
        # Base parameters for lease-up curves
        # Logistic curve: L / (1 + exp(-k * (x - x0)))
        # L: Max occupancy (usually 0.85 - 0.95)
        # k: Growth rate
        # x0: Midpoint of growth
        
        for site_id in range(n_sites):
            L = np.random.uniform(0.85, 0.98) # Stabilized occupancy
            k = np.random.uniform(0.15, 0.35) # Speed of lease up
            x0 = np.random.uniform(12, 24)    # Month of peak growth
            
            # Start date offset
            start_noise = np.random.uniform(0, 5)
            
            site_months = []
            for t in range(months):
                # Logistic trend
                trend = L / (1 + np.exp(-k * (t - x0 + start_noise)))
                
                # Add random noise (market fluctuations)
                noise = np.random.normal(0, 0.02)
                occupancy = np.clip(trend + noise, 0, 1.0)
                
                site_months.append({
                    "site_id": f"site_{site_id}",
                    "month": t + 1,
                    "occupancy": occupancy
                })
            
            history.extend(site_months)
            
        self.history_data = pd.DataFrame(history)
        return self.history_data

    def predict_revenue(self, current_occupancy=0.0, months=84, target_occupancy=None, speed_period="Medium"):
        """
        Predicts the Subject Site's occupancy trajectory over 7 years (84 months).
        Returns a DataFrame with P10, P50, P90 confidence intervals.
        """
        # If we haven't trained/generated history, do it now
        if self.history_data is None:
            self.generate_synthetic_history()
            
        forecast_rows = []
        
        # Speed mapping to 'k' parameter (logistic growth rate)
        speed_map = {
            "Slow": (0.10, 0.20),
            "Medium": (0.20, 0.30),
            "Moderate": (0.20, 0.30),
            "Fast": (0.30, 0.45)
        }
        k_range = speed_map.get(speed_period, (0.20, 0.30))
        
        # We will use the synthetic history to derive a distribution of curves
        # For simplicity in this robust proxy, we'll simulate new curves based on the distribution
        # of parameters observed in our "synthetic training set" logic.
        
        # Monte Carlo Simulation
        n_simulations = 1000
        simulated_trajectories = np.zeros((n_simulations, months))
        
        for i in range(n_simulations):
            # Sample parameters similar to our synthetic history
            
            if target_occupancy:
                # Target is the MEAN stabilized occupancy.
                # We allow small variation around it per simulation, but not drift.
                L = np.random.normal(target_occupancy, 0.01) 
                L = np.clip(L, 0.0, 1.0)
            else:
                L = np.random.uniform(0.85, 0.98) 
            
            k = np.random.uniform(k_range[0], k_range[1])
            x0 = np.random.uniform(12, 24)
            
            # Simulate a timeline
            t_values = np.arange(months)
            
            # 1. Base Logistic Trend
            trend = L / (1 + np.exp(-k * (t_values - x0)))
            
            # 2. Seasonality (Sine Wave)
            # Assumption: Peak in Summer (Months 6, 7, 8), Low in Winter.
            # Sin wave period is 12 months.
            # Shift phase so peak is around Month 7 (July).
            seasonality = 0.02 * np.sin(2 * np.pi * (t_values - 4) / 12)
            
            # 3. Random Walk Noise (Market Volatility)
            # Damped over time to prevent wild divergence from L at the end
            raw_noise = np.random.normal(0, 0.005, months)
            random_walk_noise = np.cumsum(raw_noise)
            
            # Combine
            trajectory = trend + seasonality + random_walk_noise
            
            # 4. Strict clamping logic if target is set
            # If we are near stabilization, pull back towards L to avoid infinite drift
            if target_occupancy:
                # Weight factor that increases as we get closer to month 84
                # to Ensure we end up near the target.
                w = np.linspace(0, 0.8, months)
                trajectory = (1 - w) * trajectory + w * (L + seasonality)

            # Adjust starting point
            if current_occupancy > 0:
                # Smooth blending from current_occupancy to the trajectory over 6 months
                # to avoid jump discontinuities
                diff = current_occupancy - trajectory[0]
                decay = np.exp(-0.3 * t_values) # Decays the initial difference
                trajectory += diff * decay
                
            simulated_trajectories[i, :] = np.clip(trajectory, 0, 1.0)

        # Calculate Percentiles for each month
        p10_curve = np.percentile(simulated_trajectories, 10, axis=0)
        p50_curve = np.percentile(simulated_trajectories, 50, axis=0) # Expected
        p90_curve = np.percentile(simulated_trajectories, 90, axis=0)
        
        for t in range(months):
            forecast_rows.append({
                "Month": t + 1,
                "P10_Occupancy": p10_curve[t],
                "P50_Occupancy": p50_curve[t],
                "P90_Occupancy": p90_curve[t]
            })
            
        return pd.DataFrame(forecast_rows)

    def generate_narrative(self, forecast_df):
        """
        Generates a text summary of the forecast.
        """
        # Extract key milestones
        year_1 = forecast_df[forecast_df['Month'] == 12]['P50_Occupancy'].values[0]
        year_3 = forecast_df[forecast_df['Month'] == 36]['P50_Occupancy'].values[0]
        stabilized = forecast_df['P50_Occupancy'].max()
        
        # Determine speed
        year_1_pct = year_1 * 100
        speed_desc = "steady"
        if year_1_pct > 60:
            speed_desc = "rapid"
        elif year_1_pct < 30:
            speed_desc = "slower-than-average"
            
        narrative = f"""
        **AI Forecast Analysis:**
        
        The model predicts a **{speed_desc} lease-up phase**, reaching approximately **{year_1:.1%} occupancy** by the end of Year 1. 
        
        By Year 3, the asset is projected to stabilize around **{year_3:.1%} occupancy**, with a long-term potential of **{stabilized:.1%}** (P50 scenario).
        
        *Risk Assessment:* The shaded region represents the range of probable outcomes. In a downside scenario (P10), stabilization may take longer or cap at a lower occupancy, while the upside (P90) suggests potential for faster absorption if market conditions remain favorable.
        """
        return narrative.strip()
