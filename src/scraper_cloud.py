"""
Cloud-compatible scraper using Selenium with system Chromium
"""
import time
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from geopy.distance import geodesic

def get_cloud_browser():
    """Get a Selenium browser configured for Streamlit Cloud"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')

    # Use system chromium if available
    chromium_path = '/usr/bin/chromium' if os.path.exists('/usr/bin/chromium') else '/usr/bin/chromium-browser'
    if os.path.exists(chromium_path):
        chrome_options.binary_location = chromium_path

    service = Service('/usr/bin/chromedriver') if os.path.exists('/usr/bin/chromedriver') else None

    try:
        browser = webdriver.Chrome(service=service, options=chrome_options)
        return browser
    except Exception as e:
        print(f"Failed to start browser: {e}")
        return None

def get_competitors_realtime_cloud(target_lat, target_lon, radius_miles=5):
    """
    Cloud-compatible competitor scraper using Selenium
    """
    print(f"🕵️  Scraping REAL-TIME (Radius: {radius_miles}mi) from: {target_lat}, {target_lon}")

    browser = get_cloud_browser()
    if not browser:
        print("⚠️ Browser failed to start in cloud environment")
        return []

    competitors = []
    queries = ["Storage Units", "Self Storage", "RV Storage"]

    try:
        for query in queries:
            try:
                search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}/@{target_lat},{target_lon},13z"
                print(f"      🔍 Searching: '{query}'")

                browser.get(search_url)
                time.sleep(3)  # Wait for results to load

                # Wait for results
                WebDriverWait(browser, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='article']"))
                )

                # Scroll to load more results
                scrollable = browser.find_element(By.CSS_SELECTOR, "div[role='feed']")
                for _ in range(3):
                    browser.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', scrollable)
                    time.sleep(1)

                # Extract results
                results = browser.find_elements(By.CSS_SELECTOR, "div[role='article']")

                for result in results[:20]:  # Limit to 20 per query
                    try:
                        name_elem = result.find_element(By.CSS_SELECTOR, "a[href*='maps']")
                        name = name_elem.text.strip()

                        if not name:
                            continue

                        # Get coordinates from URL
                        href = name_elem.get_attribute('href')
                        lat_match = re.search(r'!3d([\d\.-]+)', href)
                        lon_match = re.search(r'!4d([\d\.-]+)', href)

                        if lat_match and lon_match:
                            comp_lat = float(lat_match.group(1))
                            comp_lon = float(lon_match.group(1))
                            distance = geodesic((target_lat, target_lon), (comp_lat, comp_lon)).miles

                            if distance <= radius_miles:
                                competitors.append({
                                    "Name": name,
                                    "Distance": round(distance, 2),
                                    "Rate": "Call for Rate",
                                    "Source": "Google Maps",
                                    "Address": "",
                                    "Lat": comp_lat,
                                    "Lon": comp_lon
                                })
                    except Exception as e:
                        continue

            except Exception as e:
                print(f"      ⚠️ Scraper error '{query}': {str(e)[:100]}")
                continue
    finally:
        browser.quit()

    # Remove duplicates
    seen = set()
    unique_competitors = []
    for comp in competitors:
        if comp["Name"] not in seen:
            seen.add(comp["Name"])
            unique_competitors.append(comp)

    print(f"✅ Scrape complete. Found {len(unique_competitors)} competitors within {radius_miles} miles.")
    return unique_competitors
