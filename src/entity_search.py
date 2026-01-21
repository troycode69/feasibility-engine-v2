"""
CorporatePiercer - State-Specific Entity Resolution Module

This module provides targeted searches for LLC owners and registered agents
using official state registries and reliable third-party sources.

Supports:
- New York: NY Department of State Corporation Search
- Delaware: OpenCorporates (to avoid CAPTCHA on DE DOS)
- Other States: Generic bizapedia/business directory search
"""

import re
import time
import random
import urllib.parse
from typing import Dict, Optional
from playwright.sync_api import sync_playwright
from duckduckgo_search import DDGS


class CorporatePiercer:
    """
    Advanced entity resolution system for finding human owners behind LLCs.
    Uses state-specific strategies to maximize success rate.
    """
    
    def __init__(self):
        """Initialize the CorporatePiercer."""
        self.last_request_time = 0
    
    def _rate_limit(self, delay_range=(2000, 5000)):
        """Enforce random rate limiting."""
        elapsed = time.time() - self.last_request_time
        min_delay = delay_range[0] / 1000
        
        if elapsed < min_delay:
            time.sleep(min_delay - elapsed)
        
        # Add random additional delay
        extra_delay = random.randint(*delay_range) / 1000
        time.sleep(extra_delay)
        
        self.last_request_time = time.time()
    
    def search_ny_dos(self, entity_name: str) -> Dict[str, any]:
        """
        Search New York Department of State Corporation Database.
        """
        import threading
        import queue
        
        print(f"🗽 Searching NY DOS registry for: {entity_name}")
        
        res_queue = queue.Queue()
        
        def _thread_wrapper():
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                    page = context.new_page()
                    
                    inner_result = {
                        'name': None,
                        'address': None,
                        'source': 'NY DOS (OpenCorp)',
                        'source_url': None,
                        'success': False
                    }
                    
                    try:
                        time.sleep(random.uniform(2, 4))
                        search_url = f"https://opencorporates.com/companies/us_ny?q={entity_name.replace(' ', '+')}"
                        page.goto(search_url, wait_until='load', timeout=30000)
                        inner_result['source_url'] = page.url
                        page.wait_for_timeout(random.randint(2000, 4000))
                        
                        try:
                            # Try to click first result
                            page.click('a.company_search_result', timeout=5000)
                            page.wait_for_timeout(random.randint(2000, 3000))
                            inner_result['source_url'] = page.url
                        except:
                            pass
                        
                        html_content = page.content()
                        agent_match = re.search(r'Registered Agent[:\s]*([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)', html_content)
                        if agent_match:
                            inner_result['name'] = agent_match.group(1)
                            inner_result['success'] = True
                        else:
                            officer_match = re.search(r'(?:Director|Officer|President|Member)[:\s]*([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)', html_content)
                            if officer_match:
                                inner_result['name'] = officer_match.group(1)
                                inner_result['success'] = True
                    finally:
                        context.close()
                        browser.close()
                    
                    res_queue.put(inner_result)
            except Exception as e:
                print(f"❌ NY DOS registry thread error: {e}")
                res_queue.put(None)
        
        worker = threading.Thread(target=_thread_wrapper)
        worker.daemon = True
        worker.start()
        worker.join(timeout=40)
        
        try:
            result = res_queue.get(timeout=2) or {'name': None, 'address': None, 'source': 'NY DOS (OpenCorp)', 'success': False, 'source_url': None}
        except queue.Empty:
            print("⚠️ NY DOS registry queue timed out")
            result = {'name': None, 'address': None, 'source': 'NY DOS (OpenCorp)', 'success': False, 'source_url': None}
            
        result['confidence'] = 'High' if result['success'] else 'Low'
        return result
    
    def search_delaware_proxy(self, entity_name: str) -> Dict[str, any]:
        """
        Search Delaware entities via OpenCorporates.
        """
        import threading
        import queue
        
        print(f"🛡️ Searching Delaware registry for: {entity_name}")
        
        res_queue = queue.Queue()
        
        def _thread_wrapper():
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                    page = context.new_page()
                    
                    inner_result = {
                        'name': None,
                        'source': 'OpenCorporates (DE)',
                        'source_url': None,
                        'success': False
                    }
                    
                    try:
                        time.sleep(random.uniform(2, 4))
                        search_url = f"https://opencorporates.com/companies/us_de?q={entity_name.replace(' ', '+')}"
                        page.goto(search_url, wait_until='load', timeout=30000)
                        inner_result['source_url'] = page.url
                        page.wait_for_timeout(random.randint(3000, 5000))
                        
                        try:
                            page.click('a.company_search_result', timeout=5000)
                            page.wait_for_timeout(random.randint(2000, 4000))
                            inner_result['source_url'] = page.url
                        except:
                            pass
                            
                        html_content = page.content()
                        agent_match = re.search(r'Agent[:\s]*([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)', html_content, re.IGNORECASE)
                        if agent_match:
                            inner_result['name'] = agent_match.group(1)
                            inner_result['success'] = True
                        else:
                            officer_match = re.search(r'(?:Director|Officer|President|Member)[:\s]*([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)', html_content, re.IGNORECASE)
                            if officer_match:
                                inner_result['name'] = officer_match.group(1)
                                inner_result['success'] = True
                    finally:
                        context.close()
                        browser.close()
                    
                    res_queue.put(inner_result)
            except Exception as e:
                print(f"❌ DE registry thread error: {e}")
                res_queue.put(None)
                    
        worker = threading.Thread(target=_thread_wrapper)
        worker.daemon = True
        worker.start()
        worker.join(timeout=40)
        
        try:
            result = res_queue.get(timeout=2) or {'name': None, 'source': 'OpenCorporates (DE)', 'success': False, 'source_url': None}
        except queue.Empty:
            print("⚠️ DE registry queue timed out")
            result = {'name': None, 'source': 'OpenCorporates (DE)', 'success': False, 'source_url': None}
            
        result['confidence'] = 'High' if result['success'] else 'Low'
        return result
    
    def search_generic_bizapedia(self, entity_name: str, state: str = "") -> Dict[str, any]:
        """
        Generic business directory search using DuckDuckGo + bizapedia.com.
        """
        print(f"🔍 Bizapedia fallback search: {entity_name}")
        
        result = {
            'name': None,
            'source': 'Bizapedia',
            'source_url': None,
            'success': False
        }
        
        # Build query
        query = f'site:bizapedia.com "{entity_name}"'
        if state:
            query += f' "{state}" principal'
        
        try:
            ddg = DDGS()
            results = ddg.text(query, max_results=8)
            
            for res in results:
                snippet = res.get('body', '') + " " + res.get('title', '')
                curr_url = res.get('href')
                
                # Look for Registered Agent
                agent_match = re.search(r'Registered Agent[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)', snippet, re.IGNORECASE)
                if agent_match:
                    name = agent_match.group(1)
                    if self._is_valid_person_name(name):
                        result['name'] = name
                        result['success'] = True
                        result['source_url'] = curr_url
                        print(f"✅ Bizapedia Agent: {name}")
                        return result
                
                # Look for Principal
                principal_match = re.search(r'Principal[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)', snippet, re.IGNORECASE)
                if principal_match:
                    name = principal_match.group(1)
                    if self._is_valid_person_name(name):
                        result['name'] = name
                        result['success'] = True
                        result['source_url'] = curr_url
                        print(f"✅ Bizapedia Principal: {name}")
                        return result
        
        except Exception as e:
            print(f"❌ Bizapedia search error: {e}")
        
        if result['success']:
            result['confidence'] = 'Medium'
        else:
            result['confidence'] = 'Low'
            result['source_url'] = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        
        return result
    
    def _is_valid_person_name(self, name: str) -> bool:
        """Validate that extracted name is a person, not a company."""
        if any(word in name.upper() for word in ['LLC', 'INC', 'CORP', 'LTD', 'LP', 'TRUST']):
            return False
        
        false_positives = [
            'Self Storage', 'United States', 'Real Estate',
            'Property Management', 'New York', 'Delaware', 'County Clerk'
        ]
        
        for fp in false_positives:
            if fp.lower() in name.lower():
                return False
        
        return len(name.split()) >= 2
    
    def search_delaware(self, entity_name: str) -> Dict[str, any]:
        """
        Search Delaware ICIS database directly for Registered Agent info.
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
                        'name': None,
                        'address': None,
                        'source': 'Delaware ICIS',
                        'source_url': 'https://icis.corp.delaware.gov/ecorp/entitysearch/namesearch.aspx',
                        'success': False
                    }
                    
                    try:
                        time.sleep(random.uniform(2, 4))
                        page.goto(inner_result['source_url'], wait_until='load', timeout=30000)
                        
                        # Fill Entity Name
                        page.wait_for_selector('#ctl00_ContentPlaceHolder1_txtEntityName', timeout=15000)
                        page.fill('#ctl00_ContentPlaceHolder1_txtEntityName', entity_name)
                        page.click('#ctl00_ContentPlaceHolder1_btnSubmit')
                        
                        page.wait_for_timeout(random.randint(3000, 5000))
                        inner_result['source_url'] = page.url
                        
                        # Click the first result File Number link
                        try:
                            # Table selector for results
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
                        
                        # Extract Registered Agent and potentially General Partner
                        try:
                            # Look for Registered Agent Name
                            agent_label = page.locator('text="Registered Agent Name"').first
                            if agent_label.count() > 0:
                                parent_row = agent_label.evaluate_handle('el => el.closest("tr")')
                                row_text = parent_row.evaluate('el => el.innerText')
                                name = row_text.replace("Registered Agent Name:", "").replace("Registered Agent Name", "").strip()
                                
                                # Split out "General Partner" if it's in the same text or just extract it
                                if "General Partner" in row_text:
                                    # Attempt GP extraction if requested
                                    gp_match = re.search(r'General Partner[:\s]*([A-Z\s]+)', row_text, re.IGNORECASE)
                                    if gp_match:
                                        name = gp_match.group(1).strip()
                                
                                address_label = page.locator('text="Registered Agent Address"').first
                                address = ""
                                if address_label.count() > 0:
                                    addr_row = address_label.evaluate_handle('el => el.closest("tr")')
                                    addr_text = addr_row.evaluate('el => el.innerText')
                                    address = addr_text.replace("Registered Agent Address:", "").replace("Registered Agent Address", "").strip()
                                    address = " ".join([l.strip() for l in address.split("\n") if l.strip()])
                                
                                if name:
                                    inner_result['name'] = name
                                    inner_result['address'] = address
                                    inner_result['success'] = True
                                    print(f"✅ Extracted DE Agent/Principal: {name}")
                        except Exception as e:
                            print(f"⚠️ DE extraction failed: {e}")
                    finally:
                        context.close()
                        browser.close()
                    
                    res_queue.put(inner_result)
            except Exception as e:
                print(f"❌ DE ICIS registry thread error: {e}")
                res_queue.put(None)
                    
        worker = threading.Thread(target=_thread_wrapper)
        worker.daemon = True
        worker.start()
        worker.join(timeout=50)
        
        try:
            return res_queue.get(timeout=2) or {'name': None, 'source': 'Delaware ICIS', 'success': False, 'source_url': None}
        except:
            return {'name': None, 'source': 'Delaware ICIS', 'success': False, 'source_url': None}

    def resolve_entity(self, entity_name: str, state: str = "") -> Dict[str, any]:
        """
        Main entry point - resolve entity to human owner using prioritized state logic.
        """
        state_upper = (state or "").upper()
        
        # Logic Flow: NY -> DE -> Generic
        # 1. NY Search
        if state_upper == "NY":
            result = self.search_ny_dos(entity_name)
            if result['success']: return result
            
        # 2. Delaware Search (Direct ICIS)
        if state_upper == "DE" or not state_upper:
            result = self.search_delaware(entity_name)
            if result['success']: return result
            
            # Fallback to OpenCorporates Proxy for DE if direct fails
            result = self.search_delaware_proxy(entity_name)
            if result['success']: return result
        
        # 3. Generic Fallback
        return self.search_generic_bizapedia(entity_name, state)
