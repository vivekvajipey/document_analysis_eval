# evaluation_system/tools/pymupdf_extractor.py
import fitz # PyMuPDF
from pathlib import Path
from typing import Any, Dict

from .base_tool import BaseTool

class PyMuPDFExtractor(BaseTool):
    """Extracts plain text from a PDF using PyMuPDF."""

    def process(self, input_data: Any, context: Dict[str, Any]) -> Any:
        """
        :param input_data: Should be the path to the PDF file (string).
        :param context: Context dictionary.
        :return: Extracted plain text content as a single string.
        """
        pdf_path_str = str(input_data)
        if not isinstance(pdf_path_str, str) or not Path(pdf_path_str).is_file():
             raise ValueError(f"Input for PyMuPDFExtractor must be a valid PDF file path string, got: {input_data}")

        pdf_path = Path(pdf_path_str)
        extracted_text = ""
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                extracted_text += page.get_text("text") + "\n--- Page Break ---\n"
            doc.close()
            # Basic cost/latency is handled by the base class run method
            # No specific API cost here, so self._cost remains 0 unless set otherwise
        except Exception as e:
            print(f"Error processing {pdf_path.name} with PyMuPDF: {e}")
            raise # Re-raise the exception

        return extracted_text