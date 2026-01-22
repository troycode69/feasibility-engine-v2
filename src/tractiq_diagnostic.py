"""
TractIQ PDF Diagnostic Tool
Analyzes uploaded PDFs to understand their structure and help improve extraction
"""

import pdfplumber
import json
from typing import Dict, List

def diagnose_pdf(pdf_file) -> Dict:
    """
    Analyze a PDF to understand its structure for better extraction.
    Returns diagnostic information about tables, text patterns, and structure.
    """
    diagnostics = {
        "page_count": 0,
        "has_tables": False,
        "table_count": 0,
        "table_samples": [],
        "text_samples": [],
        "detected_patterns": {
            "has_competitor_data": False,
            "has_rate_data": False,
            "has_occupancy_data": False,
            "has_unit_mix": False
        }
    }

    try:
        with pdfplumber.open(pdf_file) as pdf:
            diagnostics["page_count"] = len(pdf.pages)

            for page_num, page in enumerate(pdf.pages, 1):
                # Extract text sample
                text = page.extract_text() or ""
                if text:
                    # Store first 1000 chars of each page
                    diagnostics["text_samples"].append({
                        "page": page_num,
                        "text": text[:1000]
                    })

                # Extract tables
                tables = page.extract_tables()
                if tables:
                    diagnostics["has_tables"] = True
                    diagnostics["table_count"] += len(tables)

                    # Store sample of first few tables
                    for table_num, table in enumerate(tables, 1):
                        if len(diagnostics["table_samples"]) < 5:  # Keep first 5 tables
                            # Get header and first 3 rows
                            sample_rows = table[:4] if len(table) > 4 else table
                            diagnostics["table_samples"].append({
                                "page": page_num,
                                "table_num": table_num,
                                "rows": sample_rows,
                                "column_count": len(table[0]) if table else 0,
                                "row_count": len(table)
                            })

                # Detect patterns in text
                text_lower = text.lower()

                # Check for competitor-related keywords
                if any(word in text_lower for word in ["facility", "competitor", "storage", "location"]):
                    diagnostics["detected_patterns"]["has_competitor_data"] = True

                # Check for rate data
                if "$" in text and any(word in text_lower for word in ["rate", "rent", "price"]):
                    diagnostics["detected_patterns"]["has_rate_data"] = True

                # Check for occupancy
                if "%" in text and "occup" in text_lower:
                    diagnostics["detected_patterns"]["has_occupancy_data"] = True

                # Check for unit mix
                if any(pattern in text_lower for pattern in ["unit mix", "unit type", "unit size"]):
                    diagnostics["detected_patterns"]["has_unit_mix"] = True

    except Exception as e:
        diagnostics["error"] = str(e)

    return diagnostics


def format_diagnostic_report(diagnostics: Dict) -> str:
    """Format diagnostics as readable text report."""
    report = []
    report.append("=" * 80)
    report.append("TractIQ PDF DIAGNOSTIC REPORT")
    report.append("=" * 80)
    report.append("")

    # Basic info
    report.append(f"Page Count: {diagnostics['page_count']}")
    report.append(f"Has Tables: {diagnostics['has_tables']}")
    report.append(f"Total Tables: {diagnostics['table_count']}")
    report.append("")

    # Detected patterns
    report.append("DETECTED PATTERNS:")
    for pattern, detected in diagnostics['detected_patterns'].items():
        status = "✓" if detected else "✗"
        report.append(f"  {status} {pattern}")
    report.append("")

    # Table samples
    if diagnostics['table_samples']:
        report.append("TABLE SAMPLES:")
        report.append("-" * 80)
        for i, table in enumerate(diagnostics['table_samples'], 1):
            report.append(f"\nTable {i} (Page {table['page']}, {table['row_count']} rows × {table['column_count']} cols):")
            report.append("")

            # Show header and first few rows
            for row_num, row in enumerate(table['rows']):
                if row_num == 0:
                    report.append("  HEADER: " + " | ".join([str(cell)[:20] if cell else "" for cell in row]))
                else:
                    report.append(f"  Row {row_num}: " + " | ".join([str(cell)[:20] if cell else "" for cell in row]))
            report.append("-" * 80)

    # Text samples
    if diagnostics['text_samples']:
        report.append("\nTEXT SAMPLES (First 500 chars per page):")
        report.append("-" * 80)
        for sample in diagnostics['text_samples'][:3]:  # First 3 pages
            report.append(f"\nPage {sample['page']}:")
            report.append(sample['text'][:500])
            report.append("-" * 80)

    return "\n".join(report)
