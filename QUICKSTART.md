# Full-Spectrum LLC Unmasking System - Quick Start

## Quick Test (Single Lead)

```python
from src.acquisitions import enrich_single_lead

# Test 1: NY LLC (will trigger official DOS search)
result = enrich_single_lead(
    owner_name="FM1144 LLC",
    city="Poughkeepsie",
    state="NY",
    county="Dutchess"
)
print(result)

# Test 2: Individual
result = enrich_single_lead(
    owner_name="John Smith",
    city="Austin",
    state="TX"
)
print(result)
```

## Batch CSV Processing

```python
from src.acquisitions import LeadEnricher

enricher = LeadEnricher()

# Process county CSV
# Note: System automatically detects 'County' column for official deed links
df = enricher.process_csv(
    csv_path="data/leads/county_records.csv",
    output_path="data/leads/Leads_Enriched.csv"
)

# View results
print(df.head())
```

## Expected CSV Format

**Input (county_records.csv):**
```csv
Owner Name,Mailing City,Mailing State,County
"ABC Storage LLC","Denver","CO","Denver"
"FM1144 LLC","Poughkeepsie","NY","Dutchess"
"John Smith","Austin","TX","Travis"
```

**Output (Leads_Enriched.csv):**
```csv
Original_Owner,Unmasked_Human,Phone,Phone_Type,Email,Confidence,Source,Manual_Research_Link,County_Clerk_Link
"ABC Storage LLC","Mike Johnson","(303) 555-1234","Wireless","mike@example.com","High","FastPeopleSearch","",""
"FM1144 LLC","Chad Greene","(845) 555-6789","Wireless","cgreene@example.com","High","NY DOS (Official)","",""
"John Smith","John Smith","(512) 555-4567","Wireless","","Medium","FastPeopleSearch","",""
```

## Special NY Features

**1. NY DOS Official Search**: For NY entities, the system directly scrapes the NYS Department of State database to find the "Service of Process" name. This is often the actual owner or their attorney.

**2. County Clerk Fallback**: If the official DOS search fails, the system generates a direct link to the specific County Clerk's deed search page (e.g., Dutchess, Orange, Westchester) so you can manually check signatures.


## Module API Reference

### CorporatePiercer (entity_search.py)

```python
from src.entity_search import CorporatePiercer

piercer = CorporatePiercer()

# Resolve LLC to human
result = piercer.resolve_entity("ABC Storage LLC", "NY")
# Returns: {'name': 'John Doe', 'confidence': 'High', 'success': True, ...}
```

### ContactFinder (contact_finder.py)

```python
from src.contact_finder import ContactFinder

finder = ContactFinder()

# Find contact info for person
result = finder.find_contact_info("John Doe", "Denver", "CO")
# Returns: {'phone': '(555) 123-4567', 'phone_type': 'Wireless', 
#           'email': 'john@example.com', 'success': True, ...}
```

### LeadEnricher (acquisitions.py)

```python
from src.acquisitions import LeadEnricher

enricher = LeadEnricher()

# Single lead
result = enricher.enrich_lead("ABC Storage LLC", "Denver", "CO")

# Batch CSV
df = enricher.process_csv("data/leads/input.csv")
```

## Troubleshooting

### Issue: "Playwright inside asyncio loop" error

**Fix:** Already handled with ThreadPoolExecutor isolation

### Issue: No results found

**Check:**
1. Is city/state provided? (improves accuracy)
2. Is name spelled correctly?
3. Check Manual_Research_Link for manual lookup

### Issue: Slow processing

**Expected:** 7-13 seconds per lead (includes delays to avoid blocking)

**Speed up:** Remove delays (risk of IP ban)
