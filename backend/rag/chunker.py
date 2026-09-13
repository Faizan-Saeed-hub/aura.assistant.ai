import re
from typing import List, Dict, Any
from backend.config import config

class TextChunker:
    """Splits documents into overlapping chunks with metadata preservation."""
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP

    def split_text(self, text: str) -> List[str]:
        if not text:
            return []
        
        # If smaller than chunk size, return single item
        if len(text) <= self.chunk_size:
            return [text.strip()]
        
        # Split separators in priority order
        separators = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""]
        
        def _split_recursive(t: str, seps: List[str]) -> List[str]:
            if len(t) <= self.chunk_size or not seps:
                return [t.strip()] if t.strip() else []
            
            sep = seps[0]
            parts = t.split(sep) if sep else list(t)
            chunks = []
            current = ""
            
            for part in parts:
                candidate = (current + sep + part).strip() if current else part.strip()
                if len(candidate) <= self.chunk_size:
                    current = candidate
                else:
                    if current:
                        chunks.append(current)
                    if len(part) > self.chunk_size:
                        # Split part with next separator
                        sub_chunks = _split_recursive(part, seps[1:])
                        chunks.extend(sub_chunks)
                        current = ""
                    else:
                        current = part.strip()
                        
            if current:
                chunks.append(current)
            return chunks

        raw_chunks = _split_recursive(text, separators)
        
        # Apply overlapping
        final_chunks = []
        for i, chunk in enumerate(raw_chunks):
            if i > 0 and self.chunk_overlap > 0:
                prev_overlap = raw_chunks[i-1][-self.chunk_overlap:]
                combined = (prev_overlap + " " + chunk).strip()
                final_chunks.append(combined)
            else:
                final_chunks.append(chunk)
                
        return [c for c in final_chunks if len(c) > 20]

    def chunk_document(self, doc_id: str, parsed_pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        chunks = []
        chunk_idx = 0
        for page_data in parsed_pages:
            text = page_data.get("text", "")
            page_num = page_data.get("page", 1)
            filename = page_data.get("filename", "unknown")
            
            splits = self.split_text(text)
            for split in splits:
                chunks.append({
                    "id": f"{doc_id}_{chunk_idx}",
                    "doc_id": doc_id,
                    "chunk_index": chunk_idx,
                    "filename": filename,
                    "page": page_num,
                    "text": split
                })
                chunk_idx += 1
        return chunks

text_chunker = TextChunker()
