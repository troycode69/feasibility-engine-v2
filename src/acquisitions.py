"""
Full-Spectrum Lead Enrichment System

This module orchestrates LLC resolution and contact discovery:
1. Smart column mapping for messy county CSVs
2. LLC detection (LLC/Inc/Corp/Holdings)
3. LLC → Human name resolution (via entity_search.py)
4. Human → Phone/Email discovery (via contact_finder.py)
5. Manual research link generation for failures

Output: Leads_Enriched.csv with full contact details
"""

import re
import urllib.parse
from typing import Dict, Optional
import pandas as pd
from .entity_search import CorporatePiercer
from .contact_finder import ContactFinder
from .entity_piercer import NYDOSScraper


class LeadEnricher:
    """
    Full-spectrum lead enrichment orchestrator.
    Handles LLC unmasking and contact discovery in a single pipeline.
    """
    
    def __init__(self):
        """Initialize enricher with entity resolver and contact finder."""
        self.entity_piercer = None  # Lazy init (generic)
        self.contact_finder = None  # Lazy init
        self.ny_dos_scraper = None  # Lazy init (NY official)
    
    @staticmethod
    def normalize_csv_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Smart column mapping for inconsistent county CSV headers.
        Creates standardized Owner_Name, Mailing_City, Mailing_State columns.
        
        Args:
            df: Raw DataFrame from county CSV
            
        Returns:
            DataFrame with normalized column names
        """
        df_normalized = df.copy()
        
        # Priority list for owner name column
        owner_name_candidates = [
            'Owner Name', 'owner_name', 'OWNER_NAME',
            'first_owner_name', 'FIRST_OWNER_NAME',
            'owner1', 'OWNER1'
        ]
        
        # Find owner name column
        owner_col = None
        for candidate in owner_name_candidates:
            if candidate in df.columns:
                owner_col = candidate
                break
        
        # If no single owner column, try to combine first + last
        if not owner_col:
            if 'owner1_first' in df.columns and 'owner1_last' in df.columns:
                df_normalized['Owner_Name'] = df['owner1_first'].fillna('') + ' ' + df['owner1_last'].fillna('')
                df_normalized['Owner_Name'] = df_normalized['Owner_Name'].str.strip()
            elif 'OWNER1_FIRST' in df.columns and 'OWNER1_LAST' in df.columns:
                df_normalized['Owner_Name'] = df['OWNER1_FIRST'].fillna('') + ' ' + df['OWNER1_LAST'].fillna('')
                df_normalized['Owner_Name'] = df_normalized['Owner_Name'].str.strip()
        else:
            df_normalized['Owner_Name'] = df[owner_col]
        
        # Find county column
        county_candidates = ['County', 'county', 'COUNTY', 'Mailing County', 'mailing_county']
        for candidate in county_candidates:
            if candidate in df.columns:
                df_normalized['County'] = df[candidate]
                break
        if 'County' not in df_normalized.columns:
            df_normalized['County'] = 'Dutchess'  # Default for this user's context
        
        # Find city column
        city_candidates = ['Mailing City', 'mailing_city', 'MAILING_CITY', 'city', 'CITY', 'owner_city']
        for candidate in city_candidates:
            if candidate in df.columns:
                df_normalized['Mailing_City'] = df[candidate]
                break
        
        # Find state column
        state_candidates = ['Mailing State', 'mailing_state', 'MAILING_STATE', 'state', 'STATE', 'owner_state']
        for candidate in state_candidates:
            if candidate in df.columns:
                df_normalized['Mailing_State'] = df[candidate]
                break
        
        return df_normalized
    
    @staticmethod
    def is_llc(owner_name: str) -> bool:
        """Detect if owner name is a company/LLC."""
        return any(keyword in owner_name.upper() 
                  for keyword in ['LLC', 'INC', 'CORP', 'HOLDING', 'LP', 'LTD'])
    
    @staticmethod
    def generate_manual_research_link(target_owner: str, city: str = "", state: str = "", county: str = "") -> str:
        """Generate Google Dork link for manual research."""
        # Task 4: Fix the Links
        query = f'"{target_owner}" "{city}" owner contact phone'
        encoded_query = urllib.parse.quote(query)
        return f"https://www.google.com/search?q={encoded_query}"
    
    def enrich_lead(
        self,
        owner_name: str,
        city: str = "",
        state: str = "",
        county: str = ""
    ) -> Dict[str, any]:
        """
        Full-spectrum enrichment for a single lead.
        """
        print(f"\n{'='*60}")
        print(f"📋 Processing: {owner_name}")
        print(f"{'='*60}")
        
        # Robust "No Data" handling (Empty instead of "None")
        result = {
            'Original_Owner': owner_name,
            'Unmasked_Human': None,
            'Phone': None,
            'Phone_Type': None,
            'Email': None,
            'Confidence': 'Low',
            'Source': None,
            'Source_Link': None,
            'County_Clerk_Link': None
        }
        
        # Step 1: Unmask Entity (NY -> DE -> Generic)
        is_company = self.is_llc(owner_name)
        human_name = None
        
        if is_company:
            print(f"🏢 Detected LLC/Corporation")
            
            # Step 1 & 2: Registry Search (NY then DE)
            if self.entity_piercer is None:
                self.entity_piercer = CorporatePiercer()
            
            # prioritized resolution: NY -> DE -> Generic
            entity_result = self.entity_piercer.resolve_entity(owner_name, state)
            
            if entity_result['success'] and entity_result['name']:
                human_name = entity_result['name']
                result['Source'] = entity_result.get('source')
                result['Source_Link'] = entity_result.get('source_url')
                result['Confidence'] = entity_result.get('confidence', 'Medium')
                print(f"👤 Unmasked to: {human_name}")
            else:
                print(f"⚠️ Entity unmasking failed, assuming {owner_name} is a person/hidden entity.")
                # Task 2: Step 3 - If unmasking fails, assume owner name is the target
                human_name = owner_name 
                result['Source_Link'] = self.generate_manual_research_link(owner_name, city, state, county)
        else:
            print(f"👤 Individual owner (not LLC)")
            human_name = owner_name
        
        result['Unmasked_Human'] = human_name
        
        # Add County Clerk Link for NY context regardless of success
        if (state or "").upper() == "NY":
            result['County_Clerk_Link'] = NYDOSScraper.generate_county_clerk_link(owner_name, county)

        # Step 3: Find contact info for the human
        if self.contact_finder is None:
            self.contact_finder = ContactFinder()
        
        contact_result = self.contact_finder.find_contact_info(human_name, city, state)
        
        # Update source link with actual search URL if found
        if contact_result.get('source_url'):
            result['Source_Link'] = contact_result['source_url']
            
        if contact_result['success']:
            # Validation for bot traps
            phone = contact_result.get('phone')
            if phone and "333-333" in phone:
                print(f"⚠️ Discarding bot-trap phone: {phone}")
                phone = None
                
            result['Phone'] = phone
            result['Phone_Type'] = contact_result.get('phone_type')
            result['Email'] = contact_result.get('email')
            result['Source'] = contact_result.get('source', result['Source'])
            
            if result['Confidence'] == 'Low':
                result['Confidence'] = 'Medium'
            
            print(f"✅ Contact found!")
        else:
            print(f"❌ Contact not found")
            # Repair manual research links using the new dork pattern
            if not result['Source_Link']:
                result['Source_Link'] = self.generate_manual_research_link(human_name, city, state)
        
        return result
    
    def process_csv(self, csv_path: str, output_path: str = "data/leads/Leads_Enriched.csv"):
        """
        Process entire CSV file with full enrichment pipeline.
        
        Args:
            csv_path: Path to input county CSV
            output_path: Path for enriched output CSV
            
        Returns:
            DataFrame with enriched leads
        """
        print(f"\n{'#'*60}")
        print(f"# FULL-SPECTRUM LEAD ENRICHMENT")
        print(f"# Input: {csv_path}")
        print(f"{'#'*60}\n")
        
        # Load and normalize CSV
        df = pd.read_csv(csv_path)
        print(f"📁 Loaded {len(df)} records")
        
        df_normalized = self.normalize_csv_columns(df)
        print(f"✅ Normalized columns")
        
        # Check required columns
        if 'Owner_Name' not in df_normalized.columns:
            raise ValueError("Could not find owner name column in CSV")
        
        # Process each record
        enriched_results = []
        
        for idx, row in df_normalized.iterrows():
            print(f"\n[{idx + 1}/{len(df_normalized)}]")
            
            owner = row.get('Owner_Name', '')
            city = row.get('Mailing_City', '')
            state = row.get('Mailing_State', '')
            county = row.get('County', '')
            
            result = self.enrich_lead(owner, city, state, county)
            enriched_results.append(result)
        
        # Create output DataFrame
        df_enriched = pd.DataFrame(enriched_results)
        
        # Save to CSV
        df_enriched.to_csv(output_path, index=False)
        
        print(f"\n{'#'*60}")
        print(f"# ENRICHMENT COMPLETE")
        print(f"# Output: {output_path}")
        print(f"# Total Records: {len(df_enriched)}")
        print(f"# High Confidence: {len(df_enriched[df_enriched['Confidence'] == 'High'])}")
        print(f"# Medium Confidence: {len(df_enriched[df_enriched['Confidence'] == 'Medium'])}")
        print(f"# With Phone: {len(df_enriched[df_enriched['Phone'] != ''])}")
        print(f"# With Email: {len(df_enriched[df_enriched['Email'] != ''])}")
        print(f"{'#'*60}\n")
        
        return df_enriched


# Convenience function for quick testing
def enrich_single_lead(owner_name: str, city: str = "", state: str = "", county: str = ""):
    """Quick function to enrich a single lead."""
    enricher = LeadEnricher()
    return enricher.enrich_lead(owner_name, city, state, county)
