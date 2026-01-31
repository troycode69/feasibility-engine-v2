"""
Example Study Loader
Loads reference feasibility studies to improve AI-generated report quality
Supports: PDF, Word (.docx), Text (.txt), Markdown (.md)
"""

import os
from pathlib import Path
from typing import List, Dict
import PyPDF2


def load_example_studies(example_dir: str = None) -> List[Dict[str, str]]:
    """
    Load all example studies from the example_studies directory.

    Supports: PDF, Word (.docx), Text (.txt), Markdown (.md)

    Returns:
        List of dicts with 'filename', 'content', and 'type' keys
    """
    if example_dir is None:
        # Default to src/data/example_studies
        current_dir = Path(__file__).parent
        example_dir = current_dir / "data" / "example_studies"
    else:
        example_dir = Path(example_dir)

    if not example_dir.exists():
        return []

    examples = []

    # Load PDF files
    for pdf_file in example_dir.glob("*.pdf"):
        try:
            content = extract_text_from_pdf(pdf_file)
            if content:
                examples.append({
                    'filename': pdf_file.name,
                    'content': content,
                    'type': 'pdf'
                })
        except Exception as e:
            print(f"Warning: Could not load {pdf_file.name}: {e}")

    # Load Word documents (.docx)
    for docx_file in example_dir.glob("*.docx"):
        try:
            content = extract_text_from_docx(docx_file)
            if content:
                examples.append({
                    'filename': docx_file.name,
                    'content': content,
                    'type': 'docx'
                })
        except Exception as e:
            print(f"Warning: Could not load {docx_file.name}: {e}")

    # Load text files
    for text_file in example_dir.glob("*.txt"):
        try:
            with open(text_file, 'r', encoding='utf-8') as f:
                content = f.read()
                examples.append({
                    'filename': text_file.name,
                    'content': content,
                    'type': 'text'
                })
        except Exception as e:
            print(f"Warning: Could not load {text_file.name}: {e}")

    # Load markdown files
    for md_file in example_dir.glob("*.md"):
        if md_file.name == "README.md":
            continue
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                examples.append({
                    'filename': md_file.name,
                    'content': content,
                    'type': 'markdown'
                })
        except Exception as e:
            print(f"Warning: Could not load {md_file.name}: {e}")

    return examples


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text content from a PDF file."""
    try:
        text_content = []
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text_content.append(page.extract_text())

        return "\n\n".join(text_content)
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return ""


def extract_text_from_docx(docx_path: Path) -> str:
    """Extract text content from a Word document (.docx)."""
    try:
        from docx import Document

        doc = Document(docx_path)
        text_content = []

        # Extract paragraphs
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_content.append(paragraph.text)

        # Extract tables
        for table in doc.tables:
            for row in table.rows:
                row_text = []
                for cell in row.cells:
                    if cell.text.strip():
                        row_text.append(cell.text.strip())
                if row_text:
                    text_content.append(" | ".join(row_text))

        return "\n\n".join(text_content)
    except ImportError:
        print(f"Warning: python-docx not installed. Install with: pip install python-docx")
        return ""
    except Exception as e:
        print(f"Error extracting Word document text: {e}")
        return ""


def format_examples_for_prompt(examples: List[Dict[str, str]], max_examples: int = 3) -> str:
    """
    Format example studies as context for AI prompts.

    Args:
        examples: List of example study dicts
        max_examples: Maximum number of examples to include (to control token usage)

    Returns:
        Formatted string to include in AI prompt
    """
    if not examples:
        return ""

    # Limit to max_examples
    examples = examples[:max_examples]

    prompt_text = "\n\n# REFERENCE EXAMPLES\n\n"
    prompt_text += "Below are example feasibility study sections from previous reports. "
    prompt_text += "Use these as reference for writing style, depth of analysis, and formatting:\n\n"

    for i, example in enumerate(examples, 1):
        # Truncate very long examples (max 10000 chars each for richer context)
        content = example['content']
        if len(content) > 10000:
            content = content[:10000] + "\n\n[... content truncated for length ...]"

        prompt_text += f"---\n\n## Example {i}: {example['filename']}\n\n"
        prompt_text += content
        prompt_text += "\n\n"

    prompt_text += "---\n\n"
    prompt_text += "Now, using the style and depth demonstrated above, generate the requested section for the current project.\n\n"

    return prompt_text


# Test function
if __name__ == "__main__":
    examples = load_example_studies()
    print(f"Loaded {len(examples)} example studies:")
    for ex in examples:
        print(f"  - {ex['filename']} ({ex['type']}, {len(ex['content'])} chars)")

    if examples:
        prompt_addition = format_examples_for_prompt(examples, max_examples=2)
        print(f"\nPrompt addition length: {len(prompt_addition)} characters")
