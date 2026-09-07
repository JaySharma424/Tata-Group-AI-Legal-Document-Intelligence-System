class ClauseNormalizationService:
    """Normalizes extracted clauses while preserving vector DB citations, policy text, and taxonomy risk."""

    def normalize_clauses(self, raw_clauses: list) -> list:
        normalized = []
        for c in raw_clauses:
            if not isinstance(c, dict):
                continue
            normalized.append({
                "clause_type": str(c.get("clause_type") or "General Provision").title(),
                "extracted_text": str(c.get("extracted_text", "")).strip(),
                "confidence_score": float(c.get("confidence_score") or 0.50),
                "risk_level": str(c.get("risk_level") or "LOW").upper(),
                "taxonomy_risk": str(c.get("taxonomy_risk") or "MEDIUM").upper(),  # Preserves taxonomy data
                "risk_rationale": str(c.get("risk_rationale") or "Evaluated against policy guidelines."),
                "involved_party": str(c.get("involved_party", "Tata Group & Counterparty")),
                "rag_reference_used": str(c.get("rag_reference_used") or "MISSING-POLICY"),
                "matched_policy_text": str(c.get("matched_policy_text") or ""),
                "handling_guidelines": str(c.get("handling_guidelines") or ""),
                "page_reference": str(c.get("page_reference", "Section 1")),
                "obligation_owner": str(c.get("obligation_owner", "Compliance Team")),
                "recommended_action": str(c.get("recommended_action", "Review")),
                "proposed_redline": c.get("proposed_redline"),
            })
        return normalized