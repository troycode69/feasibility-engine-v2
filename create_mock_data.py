import pandas as pd
import json
import os

def create_mock_files():
    # 1. Mock TractiQ Export.csv
    csv_data = {
        'Owner Name': ['Darlene Watkins', 'Bob Storage', 'Alice Vault'],
        'Phone': ['555-0101', '555-0202', '555-0303'],
        'Facility Name': ['Darlene\'s Secure Units', 'Bob\'s Big Box', 'Alice\'s Attic'],
        'Address': ['123 Pine St, New York, NY', '456 Oak Ave, Austin, TX', '789 Maple Rd, Denver, CO']
    }
    df = pd.DataFrame(csv_data)
    df.to_csv('TractiQ Export.csv', index=False)
    print("Created mock 'TractiQ Export.csv'")

    # 2. Mock Master v2.json (Buyer criteria)
    buyer_leads = [
        {'name': 'Buyer A', 'lat': 40.7128, 'lon': -74.0060}, # NYC
        {'name': 'Buyer B', 'lat': 30.2672, 'lon': -97.7431}  # Austin
    ]
    with open('Master v2.json', 'w') as f:
        json.dump(buyer_leads, f, indent=4)
    print("Created mock 'Master v2.json'")

if __name__ == "__main__":
    create_mock_files()
