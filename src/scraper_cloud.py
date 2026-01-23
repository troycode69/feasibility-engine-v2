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
    print("🔧 Initializing Selenium browser for cloud...")

    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')

    # Use system chromium if available (Debian uses /usr/bin/chromium)
    chromium_paths = ['/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome']
    found_chromium = False
    for path in chromium_paths:
        print(f"   Checking chromium at: {path} ... exists={os.path.exists(path)}")
        if os.path.exists(path):
            chrome_options.binary_location = path
            print(f"   ✅ Using chromium at: {path}")
            found_chromium = True
            break

    if not found_chromium:
        print("   ⚠️ No chromium binary found!")

    # Debian uses /usr/bin/chromedriver from chromium-driver package
    chromedriver_paths = ['/usr/bin/chromedriver', '/usr/lib/chromium/chromedriver']
    service = None
    found_driver = False
    for path in chromedriver_paths:
        print(f"   Checking chromedriver at: {path} ... exists={os.path.exists(path)}")
        if os.path.exists(path):
            service = Service(path)
            print(f"   ✅ Using chromedriver at: {path}")
            found_driver = True
            break

    if not found_driver:
        print("   ⚠️ No chromedriver found!")

    try:
        print("🚀 Starting Chrome webdriver...")
        browser = webdriver.Chrome(service=service, options=chrome_options)
        print("✅ Chrome webdriver started successfully!")
        return browser
    except Exception as e:
        print(f"❌ Failed to start browser: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_competitors_realtime_cloud(target_lat, target_lon, radius_miles=5):
    """
    Cloud-compatible competitor scraper using Selenium
    """
    print(f"🕵️  CLOUD SCRAPER CALLED: Scraping REAL-TIME (Radius: {radius_miles}mi) from: {target_lat}, {target_lon}")
    print(f"🔍 Current working directory: {os.getcwd()}")
    print(f"🔍 Checking for chromium binaries...")

    browser = get_cloud_browser()
    if not browser:
        print("⚠️ Browser failed to start in cloud environment")
        return []

    print(f"✅ Browser started successfully!")

    competitors = []
    queries = ["Storage Units", "Self Storage", "RV Storage"]

    try:
        for query in queries:
            try:
                search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}/@{target_lat},{target_lon},13z"
                print(f"      🔍 Searching: '{query}' at URL: {search_url}")

                browser.get(search_url)
                print(f"      ⏳ Page loaded, waiting for results...")
                time.sleep(3)  # Wait for results to load

                # Wait for results
                print(f"      ⏳ Waiting for article elements...")
                WebDriverWait(browser, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='article']"))
                )
                print(f"      ✅ Found article elements!")

                # Scroll to load more results
                scrollable = browser.find_element(By.CSS_SELECTOR, "div[role='feed']")
                for _ in range(3):
                    browser.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', scrollable)
                    time.sleep(1)

                # Extract results
                results = browser.find_elements(By.CSS_SELECTOR, "div[role='article']")
                print(f"      📊 Found {len(results)} article elements")

                for idx, result in enumerate(results[:20]):  # Limit to 20 per query
                    try:
                        name_elem = result.find_element(By.CSS_SELECTOR, "a[href*='maps']")
                        name = name_elem.text.strip()

                        if not name:
                            print(f"         [Result {idx}] Skipping - no name")
                            continue

                        # Get coordinates from URL
                        href = name_elem.get_attribute('href')
                        lat_match = re.search(r'!3d([\d\.-]+)', href)
                        lon_match = re.search(r'!4d([\d\.-]+)', href)

                        if lat_match and lon_match:
                            comp_lat = float(lat_match.group(1))
                            comp_lon = float(lon_match.group(1))
                            distance = geodesic((target_lat, target_lon), (comp_lat, comp_lon)).miles

                            print(f"         [Result {idx}] {name} - {distance:.1f}mi")

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
                                print(f"         ✅ Added (within {radius_miles}mi radius)")
                            else:
                                print(f"         ❌ Skipped (outside {radius_miles}mi radius)")
                        else:
                            print(f"         [Result {idx}] Skipping - no coordinates in URL")
                    except Exception as e:
                        print(f"         [Result {idx}] Error: {str(e)[:50]}")
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
