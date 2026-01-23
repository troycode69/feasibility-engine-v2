import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Logic imports
try:
    from src.pdf_processor import extract_pdf_data
except ImportError:
    extract_pdf_data = None

try:
    from src.csv_processor import extract_csv_data
except ImportError:
    extract_csv_data = None

try:
    from src.tractiq_cache import cache_tractiq_data
except ImportError:
    cache_tractiq_data = None

try:
    from src.site_intelligence import SiteIntelligence
except ImportError:
    SiteIntelligence = None

try:
    from src.economic_data import fetch_economic_data
except ImportError:
    fetch_economic_data = None

try:
    from src.competitor_intelligence import get_competitor_intelligence
except ImportError:
    get_competitor_intelligence = None

try:
    from src.demographics_data import fetch_demographics_data
except ImportError:
    fetch_demographics_data = None


class FeasibilityEngine:
    """
    Backend engine for Storage OS Feasibility Analysis.
    Handles data processing, AI orchestration, and complex logic 
    to keep the UI layer (app.py) clean.
    """
    
    def __init__(self):
        pass

    def process_uploaded_files(self, files, market_name="Market Data"):
        """
        Process a list of uploaded files (PDF, CSV, Excel) and return results.
        
        Args:
            files: List of uploaded file objects (Streamlit UploadedFile)
            market_name: Name of the market for caching purposes
            
        Returns:
            dict: {
                "results": dict of extraction results keyed by filename,
                "summary": {
                    "total_competitors": int,
                    "total_rates": int,
                    "success_count": int
                },
                "cache_status": str (message)
            }
        """
        results = {}
        summary = {
            "total_competitors": 0,
            "total_rates": 0,
            "success_count": 0
        }
        
        if not files:
            return {"results": {}, "summary": summary, "cache_status": "No files provided"}

        for file in files:
            file_name = file.name
            file_ext = file_name.split('.')[-1].lower()
            ext_result = {}
            
            try:
                # Reset file pointer
                file.seek(0)
                
                # Route to appropriate processor
                if file_ext == 'pdf':
                    if extract_pdf_data:
                        ext_result = extract_pdf_data(file)
                    else:
                        ext_result = {"error": "PDF Processor not available"}
                elif file_ext == 'csv':
                    if extract_csv_data:
                        ext_result = extract_csv_data(file)
                    else:
                        ext_result = {"error": "CSV Processor not available"}
                elif file_ext in ['xlsx', 'xls']:
                    if extract_csv_data:
                        ext_result = extract_csv_data(file)
                    else:
                        ext_result = {"error": "Excel Processor not available"}
                else:
                    ext_result = {"error": f"Unsupported file type: {file_ext}"}
                
                # Aggregate stats if successful
                if not ext_result.get('error'):
                    summary["total_competitors"] += len(ext_result.get('competitors', []))
                    summary["total_rates"] += len(ext_result.get('extracted_rates', []))
                    summary["success_count"] += 1
                
                results[file_name] = ext_result
                
            except Exception as e:
                import traceback
                results[file_name] = {
                    "error": str(e),
                    "error_details": traceback.format_exc()
                }

        # Cache results if possible
        cache_msg = "Caching skipped"
        if results and cache_tractiq_data:
            try:
                # Filter out error entries before caching
                valid_data = {k: v for k, v in results.items() if not v.get('error')}
                if valid_data:
                    cache_tractiq_data(market_name, valid_data)
                    cache_msg = f"Automatically cached for market: {market_name}"
            except Exception as e:
                cache_msg = f"Cache failed: {str(e)}"

        return {
            "results": results,
            "summary": summary,
            "cache_status": cache_msg
        }

    def run_ai_analysis_orchestration(self, address, lat, lon, filtered_comps=None, parcel_sqft=100000, proposed_nra=60000):
        """
        Orchestrate the AI analysis pipeline: Site -> Demographics -> Economic -> Competitor.
        Generator method that yields status updates and partial results.
        """
        results = {}
        
        # 1. Site Analysis
        yield {"step": "site", "status": "running", "message": "Analyzing site with AI vision..."}
        try:
            if SiteIntelligence:
                site_analyzer = SiteIntelligence()
                # Determine if we can run full analysis
                results['site'] = site_analyzer.analyze_complete_site(
                    address=address,
                    parcel_sqft=parcel_sqft,
                    proposed_nra=proposed_nra
                )
            else:
                results['site'] = {"error": "SiteAnalysis module missing"}
        except Exception as e:
             results['site'] = {"error": str(e)}
        yield {"step": "site", "status": "complete", "data": results['site']}

        # 2. Demographics
        yield {"step": "demographics", "status": "running", "message": "Fetching demographics..."}
        try:
            if fetch_demographics_data:
                results['demographics'] = fetch_demographics_data(lat, lon)
            else:
                results['demographics'] = {"error": "Demographics module missing"}
        except Exception as e:
            results['demographics'] = {"error": str(e)}
        yield {"step": "demographics", "status": "complete", "data": results['demographics']}

        # 3. Economic Data
        yield {"step": "economic", "status": "running", "message": "Fetching economic data..."}
        try:
            if fetch_economic_data:
                results['economic'] = fetch_economic_data(lat, lon)
            else:
                 results['economic'] = {"error": "Economic module missing"}
        except Exception as e:
            results['economic'] = {"error": str(e)}
        yield {"step": "economic", "status": "complete", "data": results['economic']}

        # 4. Competitor Intelligence
        yield {"step": "competitors", "status": "running", "message": "Analyzing competitors..."}
        try:
            if get_competitor_intelligence:
                if filtered_comps:
                    results['competitors'] = get_competitor_intelligence(
                        competitors=filtered_comps,
                        your_rate_psf=1.20 # Default
                    )
                else:
                    results['competitors'] = {
                        'count': 0,
                        'quality': 'Average',
                        'pricing': 'At Market',
                        'note': 'No competitors found in radius'
                    }
            else:
                 results['competitors'] = {"error": "Competitor module missing"}
        except Exception as e:
            results['competitors'] = {"error": str(e)}
        yield {"step": "competitors", "status": "complete", "data": results['competitors']}
        
        return results
