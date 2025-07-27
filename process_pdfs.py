import os
import json
import fitz  # PyMuPDF
import re
from pathlib import Path
from typing import List, Dict, Tuple

INPUT_DIR = "/app/input"
OUTPUT_DIR = "/app/output"

class RobustPDFProcessor:
    def __init__(self):
        # Font size thresholds for determining heading levels
        self.heading_thresholds = {
            'h1': 16,  # Large headings
            'h2': 14,  # Medium headings  
            'h3': 12,  # Small headings
            'h4': 11,  # Sub headings
        }
        
    def extract_title_from_first_page(self, doc: fitz.Document) -> str:
        """Extract document title from metadata or first page content"""
        # Try metadata first
        title = doc.metadata.get("title", "").strip()
        if title and len(title) > 3:
            return self.clean_text(title)
        
        # Fall back to analyzing first page for title
        if len(doc) > 0:
            first_page = doc[0]
            
            # Try to get text blocks sorted by position
            text_blocks = first_page.get_text("blocks")
            
            # Look for the first substantial text block as potential title
            for block in text_blocks[:3]:  # Check first 3 blocks
                text = block[4].strip() if len(block) > 4 else ""
                if text and len(text.split()) >= 3 and len(text) > 10:
                    # Clean and return first substantial text as title
                    cleaned = self.clean_text(text)
                    # Take only the first line if it's multi-line
                    first_line = cleaned.split('\n')[0].strip()
                    if first_line:
                        return first_line
        
        return "Untitled Document"
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text.strip())
        # Remove character repetitions (like "eeeeee" -> "ee")
        text = re.sub(r'(.)\1{3,}', r'\1\1', text)
        # Remove newlines within text
        text = text.replace('\n', ' ').replace('\r', ' ')
        # Clean up common OCR artifacts and keep essential punctuation
        text = re.sub(r'[^\w\s\.,;:!?()\-\'\"\/&%$#@]', '', text)
        return text.strip()
    
    def is_heading_text(self, text: str, font_size: float, is_bold: bool) -> str:
        """Determine if text is a heading and what level"""
        text_clean = text.strip()
        
        # Skip very short text
        if len(text_clean) < 3:
            return 'text'
            
        # Common heading patterns
        heading_patterns = [
            r'^\d+\.?\s+[A-Z]',              # "1. Introduction" or "1 Introduction"
            r'^Chapter\s+\d+',               # "Chapter 1"
            r'^Section\s+\d+',               # "Section 1" 
            r'^\d+\.\d+\.?\s+[A-Z]',         # "1.1 Subsection"
            r'^[A-Z][A-Z\s]{4,}$',           # "ALL CAPS HEADINGS"
            r'^[A-Z][a-z]+(\s+[A-Z][a-z]*)*$', # "Title Case Headings"
        ]
        
        is_likely_heading = any(re.match(pattern, text_clean) for pattern in heading_patterns)
        
        # Additional checks for title-like text
        words = text_clean.split()
        is_title_like = (
            len(words) >= 2 and len(words) <= 15 and  # Reasonable word count
            len(text_clean) > 5 and len(text_clean) < 200 and  # Reasonable length
            not text_clean.endswith('.') and  # Titles usually don't end with period
            sum(1 for c in text_clean if c.isupper()) >= 2  # Has some uppercase letters
        )
        
        # Determine heading level
        if font_size >= self.heading_thresholds['h1'] and (is_bold or is_likely_heading or is_title_like):
            return 'h1'
        elif font_size >= self.heading_thresholds['h2'] and (is_bold or is_likely_heading or is_title_like):
            return 'h2'
        elif font_size >= self.heading_thresholds['h3'] and (is_bold or is_likely_heading):
            return 'h3'
        elif font_size >= self.heading_thresholds['h4'] and (is_bold or is_likely_heading):
            return 'h4'
        elif is_likely_heading or (is_bold and is_title_like):
            return 'h4'
        else:
            return 'text'
    
    def extract_with_fonts(self, pdf_path: str) -> Tuple[str, List[Dict]]:
        """Extract text with font information using get_text method"""
        doc = fitz.open(pdf_path)
        title = self.extract_title_from_first_page(doc)
        outline = []
        
        for page_num, page in enumerate(doc, start=1):
            # Get text with font information
            text_dict = page.get_text("dict")
            
            for block in text_dict.get("blocks", []):
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    # Collect all text and font info from spans in this line
                    line_texts = []
                    max_font_size = 0
                    has_bold = False
                    
                    for span in line.get("spans", []):
                        span_text = span.get("text", "").strip()
                        if span_text:
                            line_texts.append(span_text)
                            font_size = span.get("size", 12)
                            max_font_size = max(max_font_size, font_size)
                            # Check if bold (flags & 16)
                            if span.get("flags", 0) & 16:
                                has_bold = True
                    
                    if line_texts:
                        # Combine all text from the line
                        full_text = " ".join(line_texts)
                        cleaned_text = self.clean_text(full_text)
                        
                        if len(cleaned_text) >= 3:  # Only include substantial text
                            level = self.is_heading_text(cleaned_text, max_font_size, has_bold)
                            
                            outline.append({
                                "level": level,
                                "text": cleaned_text,
                                "page": page_num
                            })
        
        doc.close()
        
        # Post-process to remove obvious duplicates
        outline = self.remove_duplicates(outline)
        
        return title, outline
    
    def remove_duplicates(self, outline: List[Dict]) -> List[Dict]:
        """Remove duplicate entries from outline"""
        seen = set()
        filtered_outline = []
        
        for item in outline:
            # Create a key based on text and page (case-insensitive)
            key = (item["text"].lower().strip(), item["page"])
            
            if key not in seen:
                seen.add(key)
                filtered_outline.append(item)
        
        return filtered_outline
    
    def process_single_pdf(self, pdf_path: str, output_path: str) -> bool:
        """Process a single PDF file"""
        try:
            title, outline = self.extract_with_fonts(pdf_path)
            
            # Ensure we have valid output structure  
            result = {
                "title": title,
                "outline": outline
            }
            
            # Write output JSON
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Error processing {pdf_path}: {str(e)}")
            return False
    
    def process_all_pdfs(self):
        """Process all PDFs in the input directory"""
        # Ensure output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        input_path = Path(INPUT_DIR)
        processed_count = 0
        
        # Find all PDF files
        pdf_files = list(input_path.glob("*.pdf"))
        
        if not pdf_files:
            print("No PDF files found in input directory")
            return
        
        print(f"Found {len(pdf_files)} PDF files to process")
        
        for pdf_file in pdf_files:
            output_file = Path(OUTPUT_DIR) / f"{pdf_file.stem}.json"
            
            print(f"Processing: {pdf_file.name}")
            
            if self.process_single_pdf(str(pdf_file), str(output_file)):
                processed_count += 1
                print(f"✅ Successfully processed {pdf_file.name} -> {output_file.name}")
            else:
                print(f"❌ Failed to process {pdf_file.name}")
        
        print(f"\nCompleted processing {processed_count}/{len(pdf_files)} PDF files")

def main():
    """Main execution function"""
    processor = RobustPDFProcessor()
    processor.process_all_pdfs()

if __name__ == "__main__":
    main()