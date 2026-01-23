import time
import re
import urllib.parse
import pandas as pd
from playwright.sync_api import sync_playwright
from geopy.distance import geodesic

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def get_coords_from_google_link(url):
    """Extracts !3d and !4d from the hidden Google URL."""
    try:
        if not url: return None, None
        lat = re.search(r'!3d([\d\.-]+)', url)
        lon = re.search(r'!4d([\d\.-]+)', url)
        if lat and lon:
            return float(lat.group(1)), float(lon.group(1))
    except: pass
    return None, None

def get_exact_coords(address):
    """
    Uses the browser to search the address on Google Maps and extract exact GPS.
    """
    import threading
    import queue
    import os

    print(f"📍 Precision Geocoding for: {address}")
    res_queue = queue.Queue()

    def _thread_wrapper():
        try:
            with sync_playwright() as p:
                # Use system chromium in cloud environment
                browser_args = [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage"
                ]

                launch_options = {
                    "headless": True,
                    "args": browser_args
                }

                # Try to use system chromium if available
                chromium_path = os.getenv('CHROMIUM_PATH', '/usr/bin/chromium')
                if os.path.exists(chromium_path):
                    launch_options["executable_path"] = chromium_path

                browser = p.chromium.launch(**launch_options)
                context = browser.new_context(
                    user_agent=USER_AGENT,
                    viewport={"width": 1280, "height": 720}
                )
                page = context.new_page()
                
                found_lat, found_lon = None, None
                
                try:
                    page.goto("https://www.google.com/maps?hl=en", wait_until='load', timeout=30000)
                    page.wait_for_load_state("domcontentloaded")
                    
                    try:
                        consent = page.locator("button[aria-label='Accept all']").or_(
                            page.locator("form[action*='consent'] button")
                        ).first
                        if consent.is_visible(timeout=3000):
                            consent.click()
                    except: pass

                    selectors = ["input#searchboxinput", "input[name='q']", "input[aria-label='Search Google Maps']"]
                    search_input = None
                    for sel in selectors:
                        try:
                            loc = page.locator(sel).first
                            if loc.is_visible(timeout=3000):
                                search_input = loc
                                break
                        except: continue
                    
                    if search_input:
                        search_input.fill(address)
                        search_input.press("Enter")
                        
                        for _ in range(10):
                            page.wait_for_timeout(1000)
                            current_url = page.url
                            match = re.search(r'@([\d\.-]+),([\d\.-]+)', current_url)
                            if match:
                                found_lat, found_lon = float(match.group(1)), float(match.group(2))
                                break
                            
                            l, lo = get_coords_from_google_link(current_url)
                            if l and lo:
                                found_lat, found_lon = l, lo
                                break
                finally:
                    context.close()
                    browser.close()
                
                res_queue.put((found_lat, found_lon))
        except Exception as e:
            print(f"❌ Geocoding thread error: {e}")
            res_queue.put((None, None))

    worker = threading.Thread(target=_thread_wrapper)
    worker.daemon = True
    worker.start()
    worker.join(timeout=40)
    
    try:
        return res_queue.get(timeout=2)
    except (queue.Empty, Exception):
        print("⚠️ Geocoding timed out")
        return None, None

def init_browser(p):
    """Initializes the browser and page context."""
    browser = p.chromium.launch(headless=True, slow_mo=100)
    context = browser.new_context(viewport={"width": 1400, "height": 900}, user_agent=USER_AGENT)
    page = context.new_page()
    return browser, page

def scroll_feed(page):
    """Scrolls the results feed to load lazy-loaded items."""
    print("      Scrolling results...")
    try:
        feed = page.locator('div[role="feed"]')
        # Scroll more aggressively to trigger lazy loading
        for _ in range(10): 
            feed.evaluate("node => node.scrollBy(0, 1000)")
            time.sleep(1.5) # Give it time to render new pins
            
            # Check for "You've reached the end of the list"
            if page.get_by_text("You've reached the end of the list").is_visible():
                break
    except Exception as e:
        print(f"      ⚠️ Scroll warning: {e}")

def parse_listing(listing, seen_ids, target_lat, target_lon, term):
    """Parses a single listing element and returns data if valid."""
    try:
        name = listing.get_attribute("aria-label")
        if not name or name in seen_ids: return None
        
        # --- STRICT FILTERING (NO APARTMENTS/MOVERS) ---
        negative_keywords = ["apartment", "condo", "mobile home", "portable", "container", "truck rental", "towing", "transport"]
        name_lower = name.lower()
        
        # Rule 1: Reject generic U-Haul neighborhood dealers (gas stations)
        if "u-haul neighborhood dealer" in name_lower:
            return None
            
        # Rule 2: Reject Movers/Apartments unless "Self Storage" or "Storage Units" is explicitly in title
        has_negative = any(kw in name_lower for kw in negative_keywords)
        has_positive_anchor = any(pw in name_lower for pw in ["self storage", "storage units", "mini storage"])
        
        if has_negative and not has_positive_anchor:
            return None

        # Site details
        website = "N/A"
        phone = "N/A"
        
        try:
            # Look for Website link
            ws_loc = listing.locator('a[data-value="Website"]').first
            if ws_loc.is_visible(timeout=500):
                website = ws_loc.get_attribute("href")
        except: pass
        
        try:
            # Look for phone number pattern in the listing text
            text = listing.inner_text()
            phone_match = re.search(r'(\+?\d{1,2}\s?)?(\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}', text)
            if phone_match:
                phone = phone_match.group(0)
        except: pass

        seen_ids.add(name)
        link_href = listing.locator("a").first.get_attribute("href")
        comp_lat, comp_lon = get_coords_from_google_link(link_href)
        
        # Distance Check
        dist = 999.9
        if comp_lat:
            dist = geodesic((target_lat, target_lon), (comp_lat, comp_lon)).miles
        
        return {
            "Name": name,
            "Distance": round(dist, 2),
            "Website": website,
            "Phone": phone,
            "Rate": "Call for Rate", # Placeholder, will be overriden by adjustor if available
            "Coords": f"{comp_lat},{comp_lon}" if comp_lat else "Unknown",
            "Source Term": term
        }
    except:
        return None

def get_competitors_realtime(target_lat, target_lon, radius_miles=5):
    """
    Searches multiple keywords in parallel using coordinate injection.
    Filters results by real-world radius.
    """
    from concurrent.futures import ThreadPoolExecutor
    import threading
    
    # Dynamic Zoom Level based on radius
    zoom = "13z" if radius_miles <= 5 else "11z"
    
    print(f"🕵️  Scraping REAL-TIME (Radius: {radius_miles}mi, Zoom: {zoom}) from: {target_lat}, {target_lon}")
    search_terms = ["Self Storage", "Storage Units", "RV Storage"]
    all_competitors = []
    seen_locked = threading.Lock()
    unified_seen = set()

    def _search_worker(term):
        results = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=USER_AGENT)
                page = context.new_page()
                
                encoded_term = urllib.parse.quote_plus(term)
                search_url = f"https://www.google.com/maps/search/{encoded_term}/@{target_lat},{target_lon},{zoom}/data=!3m1!4b1?entry=ttu"
                
                page.goto(search_url, wait_until='load', timeout=30000)
                try:
                    if page.locator("button[aria-label='Accept all']").is_visible(timeout=2000):
                        page.locator("button[aria-label='Accept all']").click()
                except: pass
                
                try:
                    page.wait_for_selector('div[role="feed"]', timeout=5000)
                    scroll_feed(page)
                    listings = page.locator('div[role="article"]').all()
                    
                    for listing in listings:
                        # Use a local seen set for this thread's loop, then lock for global
                        data = parse_listing(listing, set(), target_lat, target_lon, term)
                        if data:
                            # Strict Radius Filtering
                            if data["Distance"] <= radius_miles:
                                with seen_locked:
                                    if data["Name"] not in unified_seen:
                                        unified_seen.add(data["Name"])
                                        results.append(data)
                except: pass
                
                browser.close()
        except Exception as e:
            print(f"      ⚠️ Scraper error '{term}': {e}")
        return results

    with ThreadPoolExecutor(max_workers=len(search_terms)) as executor:
        futures = [executor.submit(_search_worker, term) for term in search_terms]
        for future in futures:
            all_competitors.extend(future.result())

    all_competitors.sort(key=lambda x: x["Distance"])
    print(f"✅ Scrape complete. Found {len(all_competitors)} competitors within {radius_miles} miles.")
    return all_competitors

# Backward compatibility alias
def get_competitors_dragnet(target_lat, target_lon):
    return get_competitors_realtime(target_lat, target_lon, radius_miles=5)