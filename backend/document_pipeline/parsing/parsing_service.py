import spacy
import fitz  # PyMuPDF for true PDF page counting

class ParsingService:
    def __init__(self):
        # Load the English NLP model
        try:
            self.nlp = spacy.load("en_core_web_sm")
            self.nlp.max_length = 5000000   
        except OSError:
            raise RuntimeError("spaCy model 'en_core_web_sm' not found. Please run: python -m spacy download en_core_web_sm")

    def parse(self, text: str, file_path: str = None) -> dict:
        """
        Wrapper method to match documents.py expectations while 
        leveraging parse_text logic and extracting true PDF page counts.
        """
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
            "ocr_confidence": 100.0,  # Default or derived confidence
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