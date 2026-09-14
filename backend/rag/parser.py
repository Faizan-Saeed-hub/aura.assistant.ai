import os
from pathlib import Path
from typing import List, Dict, Any

class DocumentParser:
    """Extracts text content and metadata from multiple file formats."""
    
    @staticmethod
    def parse_file(file_path: str) -> List[Dict[str, Any]]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        ext = path.suffix.lower()
        if ext == ".pdf":
            return DocumentParser._parse_pdf(path)
        elif ext == ".docx":
            return DocumentParser._parse_docx(path)
        elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
            return DocumentParser._parse_image(path)
        elif ext in [".txt", ".md", ".markdown", ".json", ".csv", ".py", ".js", ".html", ".css"]:
            return DocumentParser._parse_text(path)
        else:
            return DocumentParser._parse_text(path)

    @staticmethod
    def _parse_text(path: Path) -> List[Dict[str, Any]]:
        encodings = ["utf-8", "latin-1", "cp1252"]
        content = ""
        for enc in encodings:
            try:
                content = path.read_text(encoding=enc)
                break
            except Exception:
                continue
        return [{
            "text": content,
            "page": 1,
            "filename": path.name
        }]

    @staticmethod
    def _parse_pdf(path: Path) -> List[Dict[str, Any]]:
        pages_data = []
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages_data.append({
                        "text": text,
                        "page": idx + 1,
                        "filename": path.name
                    })
        except Exception as e:
            # If pypdf fails or not yet ready
            pages_data.append({
                "text": f"Error reading PDF: {e}",
                "page": 1,
                "filename": path.name
            })
        return pages_data

    @staticmethod
    def _parse_docx(path: Path) -> List[Dict[str, Any]]:
        try:
            import docx
            doc = docx.Document(str(path))
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text)
            return [{
                "text": "\n\n".join(full_text),
                "page": 1,
                "filename": path.name
            }]
        except Exception as e:
            return [{
                "text": f"Error reading DOCX: {e}",
                "page": 1,
                "filename": path.name
            }]

    @staticmethod
    def _parse_image(path: Path) -> List[Dict[str, Any]]:
        try:
            from PIL import Image
            img = Image.open(str(path))
            w, h = img.size
            fmt = (img.format or path.suffix.upper().lstrip(".")).upper()
            mode = img.mode

            extracted_text = ""

            # 1. Try pytesseract if installed
            try:
                import pytesseract
                extracted_text = pytesseract.image_to_string(img).strip()
            except Exception:
                pass

            # 2. Try Google Gemini Vision OCR if api key available
            if not extracted_text:
                try:
                    from backend.database import get_setting
                    gemini_key = get_setting("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
                    if gemini_key:
                        import google.generativeai as genai
                        genai.configure(api_key=gemini_key)
                        model = genai.GenerativeModel("gemini-2.5-flash")
                        prompt = "Extract and transcribe all text, numbers, headings, tables, labels, and relevant content from this image clearly and completely."
                        response = model.generate_content([prompt, img])
                        if response and response.text:
                            extracted_text = response.text.strip()
                except Exception:
                    pass

            doc_text_parts = [
                f"Document Image: {path.name}",
                f"File Format: {fmt} | Dimensions: {w} x {h} pixels | Color Mode: {mode}"
            ]
            if extracted_text:
                doc_text_parts.append(f"\nExtracted Text & Document Content:\n{extracted_text}")
            else:
                doc_text_parts.append(f"Image document '{path.name}' indexed in Knowledge Base for reference and visual analysis.")

            return [{
                "text": "\n".join(doc_text_parts),
                "page": 1,
                "filename": path.name
            }]
        except Exception as e:
            return [{
                "text": f"Error indexing image {path.name}: {e}",
                "page": 1,
                "filename": path.name
            }]

document_parser = DocumentParser()
