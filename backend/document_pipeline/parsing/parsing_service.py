import spacy
import fitz  # PyMuPDF for true PDF page counting

class ParsingService:
    # Class-level variable ensures the model is loaded only once per server lifetime
    _nlp = None

    @classmethod
    def _get_nlp(cls):
        if cls._nlp is None:
            print("Loading spaCy model lazily into memory...")
            # Load only when absolutely required
            cls._nlp = spacy.load("en_core_web_sm")
        return cls._nlp

    def parse(self, text: str, file_path: str = None, actual_confidence: float = 100.0) -> dict:
        # 1. OPTIMIZATION: Only load and run spaCy IF you actually need the 'doc' object
        # If parse_text() does NOT use spaCy, DELETE the following 2 lines to stop OOM crashes!
        nlp = self._get_nlp() 
        doc = nlp(text[:50000]) # Reduced char limit for memory safety on Render
        
        # 2. Pass the 'doc' if your parse_text needs it, otherwise just pass text
        raw_result = self.parse_text(text, doc=doc) 
        
        # 3. Calculate PDF page count efficiently (Memory safe)
        page_count = 1
        if file_path and file_path.lower().endswith('.pdf'):
            try:
                # Open just the metadata to get page count, don't read entire file into RAM
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
