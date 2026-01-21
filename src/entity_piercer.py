"""
NY DOS Process Scraper - Official State Database Access

This module extracts "DOS Process" (Service of Process) information
from the New York Department of State Corporation Database.

The DOS Process name is typically the owner or their attorney - much more
reliable than generic web searches for NY entities.

Features:
- Direct access to NYS DOS Corporation Database
- Extracts Service of Process name and address
- Thread isolation for asyncio compatibility
- County Clerk fallback link generation
"""

import re
import time
import random
import urllib.parse
from typing import Dict, Optional
from playwright.sync_api import sync_playwright


class NYDOSScraper:
    """
    Scrapes official state corporation databases (NY and DE)
    to extract "DOS Process" (Service of Process) information for LLCs.
    """
    
    def __init__(self):
        """Initialize the state registry scraper."""
        self.last_request_time = 0
        self.dos_search_url = "https://appext20.dos.ny.gov/corp_public/CORPSEARCH.ENTITY_SEARCH_ENTRY"
        self.de_search_url = "https://icis.corp.delaware.gov/ecorp/entitysearch/namesearch.aspx"
    
    def _rate_limit(self, delay_range=(2000, 4000)):
        """Enforce random rate limiting."""
        elapsed = time.time() - self.last_request_time
        min_delay = delay_range[0] / 1000
        
        if elapsed < min_delay:
            time.sleep(min_delay - elapsed)
        
        extra_delay = random.randint(*delay_range) / 1000
        time.sleep(extra_delay)
        
        self.last_request_time = time.time()
    
    def get_process_name(self, entity_name: str) -> Dict[str, any]:
        """
        Extract DOS Process (Service of Process) name from NY DOS database.
        """
        import threading
        import queue
        
        print(f"🗽 Searching NY DOS for DOS Process: {entity_name}")
        
        res_queue = queue.Queue()
        
        def _thread_wrapper():
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True, slow_mo=100)
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                    page = context.new_page()
                    
                    inner_result = {
                        'process_name': None,
                        'process_address': None,
                        'source': 'NY DOS',
                        'source_url': None,
                        'success': False
                    }
                    
                    try:
                        time.sleep(random.uniform(2, 4))
                        page.goto(self.dos_search_url, wait_until='load', timeout=30000)
                        inner_result['source_url'] = page.url
                        
                        try:
                            page.wait_for_selector('input', timeout=10000)
                            inputs = page.locator('input[type="text"]').all()
                            if inputs:
                                inputs[0].fill(entity_name)
                            else:
                                page.fill('input[name="p_name_type"]', entity_name)
                        except:
                            pass
                        
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(random.randint(3000, 5000))
                        inner_result['source_url'] = page.url
                        
                        try:
                            results = page.locator('table a').all()
                            if results:
                                active_found = False
                                for link in results:
                                    try:
                                        row_text = link.evaluate('el => el.closest("tr").innerText')
                                        if 'Active' in row_text:
                                            link.click()
                                            active_found = True
                                            break
                                    except:
                                        continue
                                if not active_found:
                                    results[0].click()
                                page.wait_for_timeout(random.randint(2000, 3000))
                                inner_result['source_url'] = page.url
                        except:
                            pass
                        
                        labels = ["DOS Process", "Service of Process"]
                        for label in labels:
                            try:
                                element = page.locator(f'text="{label}"').first
                                if element.count() > 0:
                                    parent_row = element.evaluate_handle('el => el.closest("tr")')
                                    row_content = parent_row.evaluate('el => el.innerText')
                                    content = row_content.replace(label, "").strip()
                                    lines = [line.strip() for line in content.split('\n') if line.strip()]
                                    if lines:
                                        inner_result['process_name'] = lines[0]
                                        inner_result['process_address'] = ", ".join(lines[1:])
                                        inner_result['success'] = True
                                        break
                            except:
                                continue
                    finally:
                        context.close()
                        browser.close()
                    
                    res_queue.put(inner_result)
            except Exception as e:
                print(f"❌ NY Scrape internal error: {e}")
                res_queue.put(None)

        worker = threading.Thread(target=_thread_wrapper)
        worker.daemon = True
        worker.start()
        worker.join(timeout=40)
        
        try:
            thread_res = res_queue.get(timeout=2)
            if thread_res:
                return thread_res
        except (queue.Empty, Exception):
            print("⚠️ NY DOS search timed out or failed")
        
        return {
            'process_name': None,
            'process_address': None,
            'source': 'NY DOS',
            'source_url': self.dos_search_url,
            'success': False
        }

    def search_delaware_icis(self, entity_name: str) -> Dict[str, any]:
        """
        Extract Registered Agent info from Delaware ICIS database.
        """
        import threading
        import queue
        
        print(f"🛡️ Searching Delaware ICIS for: {entity_name}")
        
        res_queue = queue.Queue()
        
        def _thread_wrapper():
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True, slow_mo=150)
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                    page = context.new_page()
                    
                    inner_result = {
                        'process_name': None,
                        'process_address': None,
                        'source': 'Delaware ICIS',
                        'source_url': None,
                        'success': False
                    }
                    
                    try:
                        time.sleep(random.uniform(2, 4))
                        page.goto(self.de_search_url, wait_until='load', timeout=30000)
                        inner_result['source_url'] = page.url
                        
                        # Wait for input field
                        page.wait_for_selector('#ctl00_ContentPlaceHolder1_txtEntityName', timeout=15000)
                        page.fill('#ctl00_ContentPlaceHolder1_txtEntityName', entity_name)
                        page.click('#ctl00_ContentPlaceHolder1_btnSubmit')
                        
                        page.wait_for_timeout(random.randint(3000, 5000))
                        inner_result['source_url'] = page.url
                        
                        # Click the first File Number link
                        try:
                            first_result = page.locator('table#ctl00_ContentPlaceHolder1_gvResults a').first
                            if first_result.count() > 0:
                                first_result.click()
                                page.wait_for_timeout(random.randint(2000, 3000))
                                inner_result['source_url'] = page.url
                            else:
                                print(f"⚠️ No Delaware results found for {entity_name}")
                                return
                        except:
                            return
                        
                        # Extract Registered Agent
                        try:
                            # Look for labels like "Registered Agent Name" or "Registered Agent"
                            agent_label = page.locator('text="Registered Agent Name"').first
                            if agent_label.count() > 0:
                                # Get the value in the next cell or same row
                                parent_row = agent_label.evaluate_handle('el => el.closest("tr")')
                                row_text = parent_row.evaluate('el => el.innerText')
                                # Simple split/replace to extract name
                                name = row_text.replace("Registered Agent Name:", "").replace("Registered Agent Name", "").strip()
                                
                                address_label = page.locator('text="Registered Agent Address"').first
                                address = ""
                                if address_label.count() > 0:
                                    addr_row = address_label.evaluate_handle('el => el.closest("tr")')
                                    addr_text = addr_row.evaluate('el => el.innerText')
                                    address = addr_text.replace("Registered Agent Address:", "").replace("Registered Agent Address", "").strip()
                                    # Clean up newline artifacts
                                    address = " ".join([l.strip() for l in address.split("\n") if l.strip()])
                                
                                if name:
                                    inner_result['process_name'] = name
                                    inner_result['process_address'] = address
                                    inner_result['success'] = True
                                    print(f"✅ Extracted DE Agent: {name}")
                        except Exception as e:
                            print(f"⚠️ DE extraction failed: {e}")
                    finally:
                        context.close()
                        browser.close()
                    
                    res_queue.put(inner_result)
            except Exception as e:
                print(f"❌ DE Scrape internal error: {e}")
                res_queue.put(None)

        worker = threading.Thread(target=_thread_wrapper)
        worker.daemon = True
        worker.start()
        worker.join(timeout=50)
        
        try:
            return res_queue.get(timeout=2) or {
                'process_name': None,
                'process_address': None,
                'source': 'Delaware ICIS',
                'source_url': self.de_search_url,
                'success': False
            }
        except:
            return {
                'process_name': None,
                'process_address': None,
                'source': 'Delaware ICIS',
                'source_url': self.de_search_url,
                'success': False
            }

    @staticmethod
    def generate_county_clerk_link(entity_name: str, county: str = "dutchess") -> str:
        """
        Generate Google Dork link for County Clerk's deed search page.
        """
        # Patterns for high-value targets
        patterns = {
            'dutchess': 'site:iqs.dutchessny.gov "{name}" deed',
            'orange': 'site:ocrecords.orangecountygov.com "{name}" deed',
            'westchester': 'site:westchesterclerk.com "{name}" deed',
            'nassau': 'site:nassaucountyny.gov "{name}" deed'
        }
        
        county_lower = county.lower()
        if county_lower in patterns:
            query = patterns[county_lower].replace("{name}", entity_name)
        else:
            # High-conversion Google DorkPattern
            query = f'site:official-deeds.com "{county} county" "{entity_name}" deed'
            # Fallback to general clerk search if specific domain is unknown
            if not county:
                query = f'"{entity_name}" county clerk property deed search'
        
        encoded_query = urllib.parse.quote(query)
        return f"https://www.google.com/search?q={encoded_query}"

# Convenience function for quick testing
def get_ny_dos_process(entity_name: str):
    """Quick function to get DOS process name."""
    scraper = NYDOSScraper()
    return scraper.get_process_name(entity_name)


# Convenience function for quick testing
def get_ny_dos_process(entity_name: str):
    """Quick function to get DOS process name."""
    scraper = NYDOSScraper()
    return scraper.get_process_name(entity_name)
