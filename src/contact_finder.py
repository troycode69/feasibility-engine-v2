"""
ContactFinder - Human Contact Discovery Module

This module finds phone numbers and email addresses for individuals
using people search sites (TruePeopleSearch, CyberBackgroundChecks).

Features:
- Playwright browser automation with stealth
- Thread isolation for asyncio compatibility
- Phone type detection (Wireless vs Landline)
- Email validation
- Fallback to multiple sources
"""

import re
import time
import random
import urllib.parse
from typing import Dict, Optional
from playwright.sync_api import sync_playwright


class ContactFinder:
    """
    Finds contact information (phone, email) for individuals using people search sites.
    Uses browser automation with robust error handling and bot-trap detection.
    """
    
    def __init__(self):
        """Initialize the ContactFinder."""
        self.last_request_time = 0
    
    def _rate_limit(self, delay_range=(3000, 5000)):
        """Enforce random rate limiting to mimic human behavior."""
        elapsed = time.time() - self.last_request_time
        min_delay = delay_range[0] / 1000
        
        if elapsed < min_delay:
            time.sleep(min_delay - elapsed)
        
        extra_delay = random.randint(*delay_range) / 1000
        time.sleep(extra_delay)
        
        self.last_request_time = time.time()
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone to digits only."""
        return re.sub(r'\D', '', phone)
    
    def _validate_phone(self, phone: str) -> Optional[str]:
        """Validate phone number and filter out bot traps."""
        if not phone:
            return None
        
        # Task 3: Filter bot traps
        if "333-333" in phone:
            print(f"⚠️ Bot trap detected ({phone}), skipping...")
            return None
            
        digits = self._normalize_phone(phone)
        if len(digits) < 10:
            return None
            
        return self._format_phone(phone)

    def _format_phone(self, phone: str) -> str:
        """Format phone to (555) 123-4567 format."""
        digits = self._normalize_phone(phone)
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        return phone
    
    def search_cyberbackgroundchecks(self, name: str, city: str, state: str) -> Dict[str, any]:
        """
        Search CyberBackgroundChecks for contact information.
        """
        import threading
        import queue
        
        print(f"🔍 Searching CyberBackgroundChecks for: {name}")
        
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
                        'phone': None,
                        'phone_type': None,
                        'email': None,
                        'source': 'CyberBackgroundChecks',
                        'source_url': None,
                        'success': False
                    }
                    
                    try:
                        time.sleep(random.uniform(3, 5))
                        name_slug = name.lower().replace(' ', '-')
                        city_slug = city.lower().replace(' ', '-')
                        state_slug = state.lower()
                        
                        # CyberBackgroundChecks URL pattern
                        url = f"https://www.cyberbackgroundchecks.com/people/{name_slug}/{city_slug}/{state_slug}"
                        
                        page.goto(url, wait_until='load', timeout=30000)
                        inner_result['source_url'] = page.url
                        
                        # Wait for potential results
                        page.wait_for_timeout(random.randint(4000, 6000))
                        
                        html_content = page.content()
                        
                        # Extraction logic (generic regex for speed, refined by validation)
                        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
                        phone_matches = re.findall(phone_pattern, html_content)
                        
                        for p_match in phone_matches:
                            validated = self._validate_phone(p_match)
                            if validated:
                                inner_result['phone'] = validated
                                inner_result['success'] = True
                                # Detect phone type
                                try:
                                    parent_text = page.locator(f'text="{p_match}"').first.evaluate('el => el.closest("div")?.innerText || ""').lower()
                                    if 'wireless' in parent_text or 'mobile' in parent_text:
                                        inner_result['phone_type'] = 'Wireless'
                                    elif 'landline' in parent_text:
                                        inner_result['phone_type'] = 'Landline'
                                except:
                                    pass
                                break
                        
                        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                        email_matches = re.findall(email_pattern, html_content)
                        if email_matches:
                            valid_emails = [e for e in email_matches if not e.lower().endswith(('.png', '.jpg', '.gif', '.svg'))]
                            if valid_emails:
                                inner_result['email'] = valid_emails[0].lower()
                                
                    finally:
                        context.close()
                        browser.close()
                    
                    res_queue.put(inner_result)
            except Exception as e:
                print(f"❌ CyberBackgroundChecks thread error: {e}")
                res_queue.put(None)
                    
        worker = threading.Thread(target=_thread_wrapper)
        worker.daemon = True
        worker.start()
        worker.join(timeout=45)
        
        try:
            return res_queue.get(timeout=2) or {'phone': None, 'phone_type': None, 'email': None, 'source': 'CyberBackgroundChecks', 'success': False}
        except:
            return {'phone': None, 'phone_type': None, 'email': None, 'source': 'CyberBackgroundChecks', 'success': False}

    def search_truepeoplesearch(self, name: str, city: str, state: str) -> Dict[str, any]:
        """
        Search TruePeopleSearch as primary/fallback source.
        """
        import threading
        import queue
        
        print(f"🔍 Searching TruePeopleSearch for: {name}")
        
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
                        'phone': None,
                        'phone_type': None,
                        'email': None,
                        'source': 'TruePeopleSearch',
                        'source_url': None,
                        'success': False
                    }
                    
                    try:
                        time.sleep(random.uniform(3, 5))
                        query = f"{name} {city} {state}".replace(' ', '+')
                        url = f"https://www.truepeoplesearch.com/results?name={query}"
                        
                        page.goto(url, wait_until='load', timeout=30000)
                        inner_result['source_url'] = page.url
                        
                        page.wait_for_timeout(random.randint(3000, 5000))
                        
                        html_content = page.content()
                        
                        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
                        phone_matches = re.findall(phone_pattern, html_content)
                        for p_match in phone_matches:
                            validated = self._validate_phone(p_match)
                            if validated:
                                inner_result['phone'] = validated
                                inner_result['success'] = True
                                break
                        
                        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                        email_matches = re.findall(email_pattern, html_content)
                        if email_matches:
                            valid_emails = [e for e in email_matches if not e.lower().endswith(('.png', '.jpg', '.gif'))]
                            if valid_emails:
                                inner_result['email'] = valid_emails[0].lower()
                    finally:
                        context.close()
                        browser.close()
                    
                    res_queue.put(inner_result)
            except Exception as e:
                print(f"❌ TruePeopleSearch thread error: {e}")
                res_queue.put(None)
                    
        worker = threading.Thread(target=_thread_wrapper)
        worker.daemon = True
        worker.start()
        worker.join(timeout=40)
        
        try:
            return res_queue.get(timeout=2) or {'phone': None, 'phone_type': None, 'email': None, 'source': 'TruePeopleSearch', 'success': False}
        except:
            return {'phone': None, 'phone_type': None, 'email': None, 'source': 'TruePeopleSearch', 'success': False}
    
    def find_contact_info(self, human_name: str, city: str = "", state: str = "") -> Dict[str, any]:
        """
        Main entry point - find contact information for a person.
        Tries TruePeopleSearch first, falls back to CyberBackgroundChecks.
        """
        if not city or not state:
            print("⚠️ City/State missing - results may be less accurate")
        
        # Try TruePeopleSearch first (more stable)
        result = self.search_truepeoplesearch(human_name, city, state)
        
        if result['success'] and result['phone']:
            return result
        
        # Fallback to CyberBackgroundChecks
        print("⚠️ TruePeopleSearch failed/incomplete, trying CyberBackgroundChecks...")
        result_cbc = self.search_cyberbackgroundchecks(human_name, city, state)
        
        if result_cbc['success']:
            return result_cbc
            
        return result # Return the first attempt if both failed
    
    @staticmethod
    def generate_manual_research_link(name: str, city: str = "", state: str = "") -> str:
        """Generate Google Dork link for manual contact research."""
        # Task 4: Fix the Links
        query = f'"{name}" "{city}" owner contact phone'
        encoded_query = urllib.parse.quote(query)
        return f"https://www.google.com/search?q={encoded_query}"
