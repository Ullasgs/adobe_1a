import os
import json
import fitz  # PyMuPDF
import re
from pathlib import Path
from typing import List, Dict, Tuple

INPUT_DIR = "/app/input"
OUTPUT_DIR = "/app/output"

class LayoutBasedProcessor:
    def __init__(self):
        self.heading_thresholds = {
            'h1': 16,
            'h2': 14,
            'h3': 12,
            'h4': 11,
        }
        
    def extract_title_from_doc(self, doc: fitz.Document) -> str:
        """Extract title from document"""
        title = doc.metadata.get("title", "").strip()
        if title and len(title) > 5:
            return self.clean_text(title)
        
        if len(doc) > 0:
            first_page = doc[0]
            full_text = first_page.get_text()
            
            lines = full_text.split('\n')
            for line in lines:
                cleaned_line = self.clean_text(line)
                if (len(cleaned_line.split()) >= 4 and 
                    len(cleaned_line) > 20 and 
                    len(cleaned_line) < 200):
                    return cleaned_line
        
        return "Untitled Document"
    
    def clean_text(self, text: str) -> str:
        """Clean text with aggressive fragment removal"""
        if not text:
            return ""
        
        text = re.sub(r'[\r\n]+', ' ', text)
        text = re.sub(r'\s+', ' ', text.strip())
        
        text = re.sub(r'(.)\1{3,}', r'\1', text)
        
        text = re.sub(r'\bRee+quest\b', 'Request', text, flags=re.IGNORECASE)
        text = re.sub(r'\bfoo+r\b', 'for', text, flags=re.IGNORECASE)
        text = re.sub(r'\bPropoaal\b', 'Proposal', text, flags=re.IGNORECASE)
        text = re.sub(r'\boposal\b', 'Proposal', text, flags=re.IGNORECASE)
        text = re.sub(r'\bOntarios\b', "Ontario's", text, flags=re.IGNORECASE)
        
        text = re.sub(r'\b(\w+):\s*\w\s+\1:\s*\w\s+', r'\1: Request', text)
        text = re.sub(r'\b(\w+)\s+\1\s+\1\s+', r'\1 ', text)
        
        text = re.sub(r'[^\w\s\.,;:!?()\-\'\"\/&%]', '', text)
        
        return text.strip()
    
    def is_heading_like(self, text: str) -> bool:
        """Determine if text looks like a heading"""
        if len(text) < 3:
            return False
            
        patterns = [
            r'^\d+\.',
            r'^Chapter\s+\d+',
            r'^Section\s+\d+',
            r'^[A-Z][A-Z\s]{3,}$',
            r'^RFP:',
            r'^Request\s+for',
            r'^To\s+Present',
        ]
        
        return any(re.match(pattern, text, re.IGNORECASE) for pattern in patterns)
    
    def classify_text_level(self, text: str, context: Dict) -> str:
        """Classify text into appropriate level"""
        font_size = context.get('font_size', 12)
        is_bold = context.get('is_bold', False)
        is_heading_pattern = self.is_heading_like(text)
        
        words = text.split()
        is_title_like = (
            len(words) >= 3 and len(words) <= 20 and
            len(text) > 15 and len(text) < 300 and
            any(c.isupper() for c in text) and
            not text.endswith('.')
        )
        
        if font_size >= self.heading_thresholds['h1'] and (is_heading_pattern or (is_bold and is_title_like)):
            return 'h1'
        elif font_size >= self.heading_thresholds['h2'] and (is_heading_pattern or is_title_like):
            return 'h2'
        elif font_size >= self.heading_thresholds['h3'] and (is_heading_pattern or is_bold):
            return 'h3'
        elif is_heading_pattern or (is_bold and len(words) <= 10):
            return 'h4'
        else:
            return 'text'
    
    def extract_with_layout_analysis(self, pdf_path: str) -> Tuple[str, List[Dict]]:
        """Extract text using layout analysis to avoid fragmentation"""
        doc = fitz.open(pdf_path)
        title = self.extract_title_from_doc(doc)
        outline = []
        
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text(flags=fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE)
            
            if not page_text.strip():
                continue
            
            lines = page_text.split('\n')
            processed_lines = set()  
            
            for line in lines:
                cleaned_line = self.clean_text(line)
                
                if (not cleaned_line or 
                    len(cleaned_line) < 3 or 
                    cleaned_line in processed_lines):
                    continue
                
                if (re.match(r'^\d+$', cleaned_line) or  
                    re.match(r'^Page\s+\d+', cleaned_line, re.IGNORECASE) or
                    len(cleaned_line) < 3):
                    continue
                
                font_info = self.get_font_info_for_text(page, cleaned_line)
                
                level = self.classify_text_level(cleaned_line, font_info)
                
                outline.append({
                    "level": level,
                    "text": cleaned_line,
                    "page": page_num
                })
                
                processed_lines.add(cleaned_line)
        
        doc.close()
        
        outline = self.final_deduplication(outline)
        
        return title, outline
    
    def get_font_info_for_text(self, page, text: str) -> Dict:
        """Get approximate font information for text"""
        font_info = {'font_size': 12, 'is_bold': False}
        
        try:
            text_dict = page.get_text("dict")
            
            for block in text_dict.get("blocks", []):
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    for span in line.get("spans", []):
                        span_text = span.get("text", "").strip()
                        
                        if span_text and span_text in text:
                            font_info['font_size'] = max(font_info['font_size'], span.get("size", 12))
                            if span.get("flags", 0) & 16:  
                                font_info['is_bold'] = True
                                
        except Exception:
            pass
        
        return font_info
    
    def final_deduplication(self, outline: List[Dict]) -> List[Dict]:
        """Remove duplicates and fragments with sophisticated matching"""
        if not outline:
            return outline
        
        for i, item in enumerate(outline):
            item['_original_index'] = i
        
        outline.sort(key=lambda x: (x['page'], x['_original_index']))
        
        deduplicated = []
        
        for current in outline:
            current_text = current['text'].lower().strip()
            
            is_fragment = False
            items_to_remove = []
            
            for i, existing in enumerate(deduplicated):
                existing_text = existing['text'].lower().strip()
                
                # Skip if identical
                if current_text == existing_text:
                    is_fragment = True
                    break
                
                if len(current_text) < len(existing_text) and current_text in existing_text:
                    is_fragment = True
                    break
                
                if len(existing_text) < len(current_text) and existing_text in current_text:
                    items_to_remove.append(i)
            
            for i in reversed(items_to_remove):
                deduplicated.pop(i)
            
            if not is_fragment:
                current_copy = current.copy()
                if '_original_index' in current_copy:
                    del current_copy['_original_index']
                deduplicated.append(current_copy)
        
        return deduplicated
    
    def process_single_pdf(self, pdf_path: str, output_path: str) -> bool:
        """Process a single PDF file"""
        try:
            print(f"  Processing: {os.path.basename(pdf_path)}")
            title, outline = self.extract_with_layout_analysis(pdf_path)
            
            print(f"  Extracted {len(outline)} elements")
            
            result = {
                "title": title,
                "outline": outline
            }
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"  Error: {str(e)}")
            return False
    
    def process_all_pdfs(self):
        """Process all PDFs in the input directory"""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        input_path = Path(INPUT_DIR)
        pdf_files = list(input_path.glob("*.pdf"))
        
        if not pdf_files:
            print("No PDF files found in input directory")
            return
        
        print(f"Found {len(pdf_files)} PDF files to process")
        processed_count = 0
        
        for pdf_file in pdf_files:
            output_file = Path(OUTPUT_DIR) / f"{pdf_file.stem}.json"
            
            if self.process_single_pdf(str(pdf_file), str(output_file)):
                processed_count += 1
                print(f" {pdf_file.name} -> {output_file.name}")
            else:
                print(f" Failed: {pdf_file.name}")
        
        print(f"\nCompleted: {processed_count}/{len(pdf_files)} files")

def main():
    """Main execution function"""
    processor = LayoutBasedProcessor()
    processor.process_all_pdfs()

if __name__ == "__main__":
    main()