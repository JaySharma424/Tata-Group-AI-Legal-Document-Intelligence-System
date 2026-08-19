import spacy
import fitz  # PyMuPDF for true PDF page counting

class ParsingService:
    _nlp = None

    def _get_nlp(self):
        if self._nlp is None:
            print("Loading spaCy model lazily...")
            # This only runs once, the first time you call parse()
            self._nlp = spacy.load("en_core_web_sm")
        return self._nlp

    # FIX: Added actual_confidence parameter with a default fallback of 100.0
    def parse(self, text: str, file_path: str = None, actual_confidence: float = 100.0) -> dict:
        """
        Wrapper method to match documents.py expectations while 
        leveraging parse_text logic and extracting true PDF page counts.
        """
        nlp = self._get_nlp() # Load only when needed
        doc = nlp(text[:100000]) # Process
        raw_result = self.parse_text(text)
        
        # Calculate true page count if a valid PDF path is provided
        page_count = 1
        if file_path and file_path.lower().endswith('.pdf'):
            try:
                with fitz.open(file_path) as doc:
                    page_count = len(doc)
            except Exception as e:
                print(f"Error reading PDF page count: {e}")
        
        # Map to keys expected by documents.py
        return {
            "ocr_confidence": actual_confidence,  # FIX: Now maps the dynamic score dynamically
            "pages": page_count,      # True extracted PDF page count
            "entities": raw_result.get("entities_found", []),
            "section_count": raw_result.get("section_count", 0),
            "parsed_sections": raw_result.get("parsed_sections", [])
        }

    def parse_text(self, text: str) -> dict:
        """Parses raw text into structural sections and extracts recognized entities."""
        doc = self.nlp(text)
        
        # Extract basic entities (Parties, Dates, Monetary values)
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
