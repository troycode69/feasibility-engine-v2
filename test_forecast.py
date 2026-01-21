from src.forecast import RevenueForecaster
import pandas as pd

def test_forecast():
    print("Initializing Forecaster...")
    forecaster = RevenueForecaster()
    
    print("Generating Synthetic History...")
    history = forecaster.generate_synthetic_history(n_sites=10)
    print(f"Generated {len(history)} rows of history.")
    
    print("Predicting Revenue...")
    forecast = forecaster.predict_revenue(current_occupancy=0.0, months=84)
    
    print("\nForecast Head:")
    print(forecast.head())
    
    print("\nForecast Tail:")
    print(forecast.tail())
    
    print("\nNarrative:")
    narrative = forecaster.generate_narrative(forecast)
    print(narrative)
    
    assert len(forecast) == 84
    assert 'P10_Occupancy' in forecast.columns
    assert 'P50_Occupancy' in forecast.columns
    assert 'P90_Occupancy' in forecast.columns
    
    print("\nTEST PASSED!")

if __name__ == "__main__":
    test_forecast()
