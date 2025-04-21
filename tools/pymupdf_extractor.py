# evaluation_system/tools/pymupdf_extractor.py
import fitz # PyMuPDF
from pathlib import Path
from typing import Any, Dict, List

from .base_tool import BaseTool

class PyMuPDFExtractor(BaseTool):
    """Extracts plain text from a PDF using PyMuPDF."""

    def process(self, input_data: Any, context: Dict[str, Any]) -> Any:
        """
        :param input_data: Should be the path to the PDF file (string).
        :param context: Context dictionary.
        :return: Dictionary with document_id, text, and content_units.
        """
        pdf_path_str = str(input_data)
        if not isinstance(pdf_path_str, str) or not Path(pdf_path_str).is_file():
             raise ValueError(f"Input for PyMuPDFExtractor must be a valid PDF file path string, got: {input_data}")

        pdf_path = Path(pdf_path_str)
        document_id = pdf_path.stem
        concatenated_text = ""
        content_units = []
        
        try:
            doc = fitz.open(pdf_path)
            unit_count = 0
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text("text")
                concatenated_text += page_text + "\n--- Page Break ---\n"
                
                # For this simple example, we'll treat each paragraph (text separated by empty lines)
                # as a separate content unit
                paragraphs = [p.strip() for p in page_text.split('\n\n') if p.strip()]
                
                for para in paragraphs:
                    unit_count += 1
                    content_units.append({
                        "unit_id": f"unit_{unit_count}",
                        "text": para,
                        "source_page_start": page_num + 1,
                        "source_page_end": page_num + 1
                    })
                    
            doc.close()
            # Basic cost/latency is handled by the base class run method
            # No specific API cost here, so self._cost remains 0 unless set otherwise
        except Exception as e:
            print(f"Error processing {pdf_path.name} with PyMuPDF: {e}")
            raise # Re-raise the exception

        return {
            "document_id": document_id,
            "text": concatenated_text,  # Keep raw text for backward compatibility
            "content_units": content_units
        }