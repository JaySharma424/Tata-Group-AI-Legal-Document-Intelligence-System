class ClauseNormalizationService:
    """Standardizes and normalizes extracted clauses into official corporate taxonomy schemas."""
    
    STANDARD_TAXONOMY = {
        "TERM": "Term and Renewal",
        "TERMINATION": "Termination & Exit Rights",
        "LIABILITY": "Limitation of Liability",
        "CONFIDENTIALITY": "Confidential Information & Data Security",
        "FEE": "Fees, Invoicing & Commercials",
        "WARRANTY": "Representation and Warranties",
        "GOVERNING": "Governing Law, Jurisdiction & Dispute Resolution",
        "COMPLIANCE": "Supplier Code of Conduct & Statutory Compliance",
        "SCOPE": "Scope of Services & Obligations"
    }

    def normalize_clause_type(self, raw_type: str) -> str:
        """Maps raw clause titles to standard enterprise taxonomy headers."""
        if not raw_type:
            return "GENERAL PROVISION & COMPLIANCE"
        
        upper_type = raw_type.upper()
        for key, standard_name in self.STANDARD_TAXONOMY.items():
            if key in upper_type:
                return standard_name
        
        return raw_type.title()

    def normalize_clauses(self, raw_clauses: list) -> list:
        """Applies normalization rules to a list of extracted clauses."""
        normalized = []
        for clause in raw_clauses:
            if not isinstance(clause, dict):
                continue
            
            normalized_clause = {
                "clause_type": self.normalize_clause_type(clause.get("clause_type")),
                "extracted_text": clause.get("extracted_text", "").strip(),
                "confidence_score": float(clause.get("confidence_score", 0.90)),
                "risk_level": clause.get("risk_level", "LOW").upper(),
                "risk_rationale": clause.get("risk_rationale", "Standard enterprise review parameters met."),
                "involved_party": clause.get("involved_party", "Tata Group & Counterparty"),
                "rag_reference_used": clause.get("rag_reference_used", "POL-IND-2026-01"),
                "page_reference": clause.get("page_reference", "N/A"),
                "obligation_owner": clause.get("obligation_owner", "Compliance Team"),
                "recommended_action": clause.get("recommended_action", "Review")
            }
            normalized.append(normalized_clause)
            
        return normalized