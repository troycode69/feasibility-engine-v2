import re
import pdfplumber

def extract_pdf_data(pdf_file):
    """
    Extracts high-level insights from market research PDFs.
    Works with BytesIO objects (Streamlit uploads).
    """
    data = {
        "pipeline_risk": "Standard",
        "extracted_rates": [],
        "raw_text_sample": ""
    }
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
            
            data["raw_text_sample"] = text[:5000] # For AI context if needed
            
            # 1. Pipeline Risk Detection
            risk_keywords = {
                "High": ["Planning", "Proposed", "Under Construction", "Permit Issued", "Deferred"],
                "Moderate": ["Expansion", "Renovation"],
            }
            
            found_risks = []
            for risk, keywords in risk_keywords.items():
                for kw in keywords:
                    if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
                        found_risks.append(f"{risk} ({kw})")
            
            if found_risks:
                data["pipeline_risk"] = ", ".join(list(set(found_risks)))
            
            # 2. Rate Extraction (Regex for $ and nearby numbers)
            # Looks for things like "10x10 $145" or "Small: $99"
            rate_patterns = [
                r"\$([0-9]{2,3})", # Simple $99 or $145
                r"10x10.*?\$([0-9]{2,3})" # Specific to 10x10
            ]
            
            rates = []
            for pattern in rate_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    rates.append(int(match.group(1)))
            
            if rates:
                # Use a realistic average or range
                data["extracted_rates"] = sorted(list(set(rates)))
                
    except Exception as e:
        print(f"PDF Analysis Error: {e}")
        
    return data
