import re
import pdfplumber
from datetime import datetime

def extract_pdf_data(pdf_file):
    """
    Extracts comprehensive market intelligence from TractIQ PDFs and other market research.
    Works with BytesIO objects (Streamlit uploads).

    Enhanced to extract:
    - Competitor profiles (name, address, units, occupancy, rates)
    - Unit mix breakdowns
    - Historical pricing trends
    - Market analytics and metrics
    - Pipeline risk assessments
    """
    data = {
        "pipeline_risk": "Standard",
        "extracted_rates": [],
        "raw_text_sample": "",
        "competitors": [],
        "unit_mix": {},
        "market_metrics": {},
        "historical_trends": [],
        "source_type": "Unknown",
        "extraction_date": datetime.now().isoformat()
    }

    try:
        with pdfplumber.open(pdf_file) as pdf:
            text = ""
            tables = []

            for page in pdf.pages:
                # Extract text
                page_text = page.extract_text() or ""
                text += page_text

                # Extract tables (TractIQ exports often have tabular data)
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)

            data["raw_text_sample"] = text[:5000]

            # Detect source type
            if "tractiq" in text.lower() or "yardi matrix" in text.lower():
                data["source_type"] = "TractIQ"
            elif "costar" in text.lower():
                data["source_type"] = "CoStar"

            # === 1. COMPETITOR EXTRACTION ===
            competitors = extract_competitors_from_text(text, tables)
            if competitors:
                data["competitors"] = competitors

            # === 2. UNIT MIX EXTRACTION ===
            unit_mix = extract_unit_mix(text, tables)
            if unit_mix:
                data["unit_mix"] = unit_mix

            # === 3. PIPELINE RISK DETECTION ===
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

            # === 4. RATE EXTRACTION (Enhanced) ===
            rates = extract_rates(text, tables)
            if rates:
                data["extracted_rates"] = sorted(list(set(rates)))

            # === 5. MARKET METRICS ===
            metrics = extract_market_metrics(text)
            if metrics:
                data["market_metrics"] = metrics

            # === 6. HISTORICAL TRENDS ===
            trends = extract_historical_trends(text, tables)
            if trends:
                data["historical_trends"] = trends

    except Exception as e:
        print(f"PDF Analysis Error: {e}")

    return data


def extract_competitors_from_text(text, tables):
    """Extract competitor facility information from text and tables."""
    competitors = []

    # Strategy 1: Extract from TractIQ Rate Trends Report format
    # Format: Facility Name\nAddress\nSquare Footage\nDistance
    rate_trends_pattern = r"([A-Z][A-Za-z0-9\s&'.-]+(?:Storage|Self[ -]Storage|Mini[ -]Storage|U-Haul))\s*\n([^\n]+(?:USA|United States)[^\n]*)\s*\n([\d,]+)\s*sq\.?\s*feet\s*\n([\d.]+)\s*miles?"

    for match in re.finditer(rate_trends_pattern, text, re.IGNORECASE):
        name = match.group(1).strip()
        address = match.group(2).strip()
        sqft_str = match.group(3).replace(',', '')
        distance_str = match.group(4)

        # Skip generic headers
        if name.lower() in ['self storage', 'mini storage', 'rate trends report']:
            continue

        comp = {
            "name": name,
            "address": address,
            "source": "PDF Text Extract (Rate Trends)",
            "nrsf": int(sqft_str),
            "distance_miles": float(distance_str)
        }

        # Look for rate data after this facility block (next 300 chars)
        context_start = match.end()
        context_end = min(context_start + 300, len(text))
        context = text[context_start:context_end]

        # Extract 10x10 rate from $/SF format (avg line)
        # Pattern: "avg. ... $X.XX" where we want the 10x10 CC column
        avg_rate_pattern = r'avg\.\s+(?:N/A\s+){0,6}\$(\d\.\d{2})'
        avg_matches = re.findall(avg_rate_pattern, context)
        if avg_matches:
            # Take the first valid $/SF rate and convert to 10x10 (100 SF)
            psf = float(avg_matches[0])
            comp["rate_10x10"] = round(psf * 100, 2)

        competitors.append(comp)

    # Strategy 2: Extract from text-based layouts (other formats)
    # Look for facility names in various TractIQ formats

    # Pattern 1: Facility name with storage keywords
    facility_pattern = r"([A-Z][A-Za-z0-9\s&'.-]+(?:Storage|Self[ -]Storage|Mini[ -]Storage|U-Haul|Public Storage|Extra Space|CubeSmart|Life Storage))"

    # Find all potential facility names
    potential_facilities = re.finditer(facility_pattern, text, re.IGNORECASE)

    for match in potential_facilities:
        name = match.group(1).strip()

        # Skip if it's too generic or just a header
        if name.lower() in ['self storage', 'mini storage', 'public storage', 'rate trends report']:
            continue

        # Skip if already found by Rate Trends extraction
        if any(c.get('name', '').lower() == name.lower() for c in competitors):
            continue

        # Try to find associated data near this facility name (within next 500 chars)
        context_start = match.start()
        context_end = min(context_start + 500, len(text))
        context = text[context_start:context_end]

        comp = {
            "name": name,
            "source": "PDF Text Extract"
        }

        # Look for units in context
        units_match = re.search(r'(\d{1,4})\s*(?:units?|Units?|UNITS?)', context, re.IGNORECASE)
        if units_match:
            comp["units"] = int(units_match.group(1))

        # Look for occupancy in context
        occ_match = re.search(r'(\d{1,3}(?:\.\d+)?)\s*%?\s*(?:occ|occup|physical)', context, re.IGNORECASE)
        if occ_match:
            comp["occupancy"] = float(occ_match.group(1))

        # Look for rates in context (10x10 specifically)
        rate_match = re.search(r'(?:10\s*[xX×]\s*10|10x10)[^\$]*\$\s*([0-9]{2,3}(?:\.[0-9]{2})?)', context, re.IGNORECASE)
        if rate_match:
            comp["rate_10x10"] = float(rate_match.group(1))

        # Only add if we found at least one metric
        if len(comp) > 2:
            competitors.append(comp)

    # Strategy 3: Extract from tables (more reliable for TractIQ exports)
    for table in tables:
        if not table or len(table) < 2:
            continue

        # Check if this looks like a competitor table
        header = [str(cell).lower() if cell else "" for cell in table[0]]

        # Look for key columns - try multiple variations
        name_col = next((i for i, h in enumerate(header) if any(word in h for word in ["name", "facility", "property", "site", "location"])), None)
        units_col = next((i for i, h in enumerate(header) if "unit" in h and "mix" not in h and "size" not in h), None)
        occ_col = next((i for i, h in enumerate(header) if "occ" in h or "phys" in h), None)  # TractIQ uses "Physical Occupancy"
        rate_col = next((i for i, h in enumerate(header) if "rate" in h or "10x10" in h or "10 x 10" in h or "street" in h), None)

        if name_col is not None:
            for row in table[1:]:  # Skip header
                if not row or len(row) <= name_col:
                    continue

                comp = {"source": "PDF Table"}

                # Extract name
                if row[name_col]:
                    comp["name"] = str(row[name_col]).strip()
                else:
                    continue

                # Extract units
                if units_col is not None and row[units_col]:
                    try:
                        comp["units"] = int(re.sub(r'[^\d]', '', str(row[units_col])))
                    except:
                        pass

                # Extract occupancy
                if occ_col is not None and row[occ_col]:
                    try:
                        occ_str = str(row[occ_col]).replace('%', '').strip()
                        comp["occupancy"] = float(occ_str)
                    except:
                        pass

                # Extract rate
                if rate_col is not None and row[rate_col]:
                    try:
                        rate_str = str(row[rate_col]).replace('$', '').replace(',', '').strip()
                        comp["rate_10x10"] = float(rate_str)
                    except:
                        pass

                if len(comp) > 2:  # Has more than just source and name
                    competitors.append(comp)

    return competitors


def extract_unit_mix(text, tables):
    """Extract unit mix distribution from tables and text."""
    unit_mix = {}

    # Common unit size patterns with counts
    # Match patterns like: "10x10 (45 units)", "5 x 5: 20", "10x15 - 30 units"
    size_count_pattern = r"(\d{1,2}\s*[xX×]\s*\d{1,2})[^\d\n]{0,20}(\d{1,4})\s*(?:units?|Units?|UNITS?)?"

    matches = re.finditer(size_count_pattern, text, re.IGNORECASE)
    for match in matches:
        size_raw = match.group(1)
        count_str = match.group(2)

        # Normalize size format (convert to "10x10" standard)
        size = re.sub(r'\s*([xX×])\s*', 'x', size_raw)

        try:
            count = int(count_str)
            # Only accept reasonable unit counts (not years, rates, etc.)
            if 1 <= count <= 1000:
                if size in unit_mix:
                    unit_mix[size] += count
                else:
                    unit_mix[size] = count
        except:
            pass

    # Try to find unit mix in tables
    for table in tables:
        if not table or len(table) < 2:
            continue

        header = [str(cell).lower() if cell else "" for cell in table[0]]

        # Look for unit size column
        size_col = next((i for i, h in enumerate(header) if "size" in h or "type" in h), None)
        count_col = next((i for i, h in enumerate(header) if "count" in h or "units" in h or "#" in h), None)

        if size_col is not None and count_col is not None:
            for row in table[1:]:
                if not row or len(row) <= max(size_col, count_col):
                    continue

                size = str(row[size_col]).strip() if row[size_col] else ""
                count_str = str(row[count_col]).strip() if row[count_col] else ""

                if size and count_str:
                    try:
                        count = int(re.sub(r'[^\d]', '', count_str))
                        unit_mix[size] = count
                    except:
                        pass

    return unit_mix


def extract_rates(text, tables):
    """Enhanced rate extraction supporting multiple formats."""
    rates = []

    # Pattern 1: Dollar amounts with decimals or whole numbers
    # Match $1.23, $145, $99.00, etc.
    dollar_pattern = r"\$\s*([0-9]{2,3}(?:\.[0-9]{2})?)"
    matches = re.finditer(dollar_pattern, text)
    for match in matches:
        try:
            rate = float(match.group(1))
            if 40 <= rate <= 600:  # Reasonable range for storage (expanded)
                rates.append(int(round(rate)))
        except:
            pass

    # Pattern 2: Specific to 10x10 climate or standard
    # Matches: "10x10 Climate $145", "10 x 10: $99.50", etc.
    tenten_pattern = r"10\s*[xX×]\s*10[^\$\n]{0,50}\$\s*([0-9]{2,3}(?:\.[0-9]{2})?)"
    matches = re.finditer(tenten_pattern, text, re.IGNORECASE)
    for match in matches:
        try:
            rates.append(int(round(float(match.group(1)))))
        except:
            pass

    # Pattern 3: Rate per square foot (common in TractIQ)
    # Matches: "$1.25/SF", "$ 1.50 / sq ft"
    psf_pattern = r"\$\s*([0-9]\.[0-9]{2})\s*/\s*(?:SF|sq\.?\s*ft)"
    matches = re.finditer(psf_pattern, text, re.IGNORECASE)
    for match in matches:
        try:
            # Convert $/SF to approximate 10x10 rate (100 SF)
            psf = float(match.group(1))
            rate_10x10 = int(round(psf * 100))
            if 40 <= rate_10x10 <= 600:
                rates.append(rate_10x10)
        except:
            pass

    # Extract from tables
    for table in tables:
        if not table:
            continue

        for row in table:
            if not row:
                continue
            for cell in row:
                if not cell:
                    continue
                cell_str = str(cell)
                if '$' in cell_str:
                    try:
                        # Remove everything except digits and decimal
                        rate_str = re.sub(r'[^\d.]', '', cell_str)
                        rate = float(rate_str)
                        if 40 <= rate <= 600:
                            rates.append(int(round(rate)))
                    except:
                        pass

    return rates


def extract_market_metrics(text):
    """Extract market-level metrics like average occupancy, supply, etc."""
    metrics = {}

    # Market occupancy pattern
    occ_pattern = r"(?:market|average|avg|area)\s*(?:occupancy|occ)[^\d]*(\d{1,3})%"
    match = re.search(occ_pattern, text, re.IGNORECASE)
    if match:
        metrics["market_occupancy"] = float(match.group(1))

    # Market rate pattern
    rate_pattern = r"(?:market|average|avg|area)\s*(?:rate|rental)[^\$]*\$([0-9]{2,3})"
    match = re.search(rate_pattern, text, re.IGNORECASE)
    if match:
        metrics["market_avg_rate"] = float(match.group(1))

    # Total supply
    supply_pattern = r"(?:total|market)\s*(?:supply|units|inventory)[^\d]*(\d{1,3},?\d{3})"
    match = re.search(supply_pattern, text, re.IGNORECASE)
    if match:
        supply_str = match.group(1).replace(',', '')
        metrics["total_supply"] = int(supply_str)

    return metrics


def extract_historical_trends(text, tables):
    """Extract historical pricing or occupancy trends."""
    trends = []

    # Look for year + rate patterns (expanded to handle more formats)
    # E.g., "2023: $145", "Q1 2024 $150", "Jan 2025 $1.45/SF", "2024 $99.50"
    year_rate_pattern = r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*20\d{2}|20\d{2}|Q[1-4]\s*20\d{2})[^\$\n]{0,30}\$\s*([0-9]{1,3}(?:\.[0-9]{2})?)"
    matches = re.finditer(year_rate_pattern, text)

    for match in matches:
        period = match.group(1).strip()
        try:
            rate = float(match.group(2))
            # If rate is very small (like 1.45), it might be $/SF - convert to 10x10
            if rate < 10:
                rate = rate * 100
            trends.append({
                "period": period,
                "rate": int(round(rate))
            })
        except:
            pass

    # Look for occupancy trends (expanded to handle month names)
    year_occ_pattern = r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*20\d{2}|20\d{2}|Q[1-4]\s*20\d{2})[^\d\n]{0,30}(\d{1,3}(?:\.\d+)?)\s*%?\s*(?:occ|occup)"
    matches = re.finditer(year_occ_pattern, text, re.IGNORECASE)

    for match in matches:
        period = match.group(1).strip()
        try:
            occ = float(match.group(2))

            # Find or create trend entry for this period
            existing = next((t for t in trends if t["period"] == period), None)
            if existing:
                existing["occupancy"] = occ
            else:
                trends.append({
                    "period": period,
                    "occupancy": occ
                })
        except:
            pass

    return sorted(trends, key=lambda x: x.get("period", ""))
