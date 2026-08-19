import spacy
import fitz  # PyMuPDF

class ParsingService:
    _nlp = None

    @classmethod
    def _get_nlp(cls):
        if cls._nlp is None:
            print("Loading spaCy model lazily...")
            cls._nlp = spacy.load("en_core_web_sm")
        return cls._nlp

    def parse(self, text: str, file_path: str = None, actual_confidence: float = 100.0) -> dict:
        # 1. Process NLP ONLY ONCE here.
        nlp = self._get_nlp()
        # Process the text slice once and store it in 'doc'
        doc = nlp(text[:50000]) 
        
        # 2. Pass that 'doc' object to parse_text to reuse the work
        raw_result = self.parse_text(text, doc=doc) 
        
        # 3. Calculate PDF page count
        page_count = 1
        if file_path and file_path.lower().endswith('.pdf'):
            try:
                with fitz.open(file_path) as doc_handle:
                    page_count = len(doc_handle)
            except Exception as e:
                print(f"Error reading PDF page count: {e}")
        
        return {
            "ocr_confidence": actual_confidence,
            "pages": page_count,
            "entities": raw_result.get("entities_found", []),
            "section_count": raw_result.get("section_count", 0),
            "parsed_sections": raw_result.get("parsed_sections", [])
        }
        
    def parse_text(self, text: str, doc=None) -> dict:
        """Parses raw text using the already processed 'doc' object."""
        # If doc wasn't passed, fallback to processing (but avoid this to save memory!)
        if doc is None:
            nlp = self._get_nlp()
            doc = nlp(text[:50000])
        
        # Extract entities from the already-processed 'doc'
        entities = []
        for ent in doc.ents:
            if ent.label_ in ["ORG", "PERSON", "DATE", "MONEY"]:
                entities.append({
                    "text": ent.text,
                    "label": ent.label_
                })
        
        # Split text into logical paragraphs/sections
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        
        return {
            "section_count": len(paragraphs),
            "entities_found": entities,
            "parsed_sections": paragraphs
        }
