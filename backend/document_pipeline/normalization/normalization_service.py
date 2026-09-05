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
        "SCOPE": "Scope of Services & Obligations",
        "INDEMNITY": "Indemnification & Hold Harmless",
        "IP": "Intellectual Property Rights",
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

    def _safe_float(self, val, default: float = 0.90) -> float:
        """Safely parses confidence score converting 'High', '95%', or floats without throwing ValueError."""
        if val is None:
            return default
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            val_clean = val.replace("%", "").strip()
            try:
                parsed = float(val_clean)
                return parsed / 100.0 if parsed > 1.0 else parsed
            except ValueError:
                val_lower = val.lower()
                if "high" in val_lower:
                    return 0.95
                elif "med" in val_lower:
                    return 0.80
                elif "low" in val_lower:
                    return 0.65
        return default

    def normalize_clauses(self, raw_clauses: list) -> list:
        """Applies normalization and strict type-safety to a list of extracted clauses."""
        normalized = []
        for clause in raw_clauses:
            if not isinstance(clause, dict):
                continue

            normalized_clause = {
                "clause_type": self.normalize_clause_type(
                    clause.get("clause_type")
                ),
                "extracted_text": str(
                    clause.get("extracted_text", "")
                ).strip(),
                "confidence_score": self._safe_float(
                    clause.get("confidence_score"), 0.90
                ),
                "risk_level": str(clause.get("risk_level", "LOW")).upper(),
                "risk_rationale": str(
                    clause.get(
                        "risk_rationale",
                        "Standard enterprise review parameters met.",
                    )
                ),
                "involved_party": str(
                    clause.get("involved_party", "Tata Group & Counterparty")
                ),
                "rag_reference_used": str(
                    clause.get("rag_reference_used", "POL-IND-2026-01")
                ),
                "page_reference": str(clause.get("page_reference", "N/A")),
                "obligation_owner": str(
                    clause.get("obligation_owner", "Compliance Team")
                ),
                "recommended_action": str(
                    clause.get("recommended_action", "Review")
                ),
            }
            normalized.append(normalized_clause)

        return normalized