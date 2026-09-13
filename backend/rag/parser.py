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
        elif ext in [".txt", ".md", ".markdown", ".json", ".csv", ".py", ".js", ".html", ".css"]:
            return DocumentParser._parse_text(path)
        else:
            # Fallback to plain text read
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

document_parser = DocumentParser()
