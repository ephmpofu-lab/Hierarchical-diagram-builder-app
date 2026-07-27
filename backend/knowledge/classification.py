"""Knowledge organization and classification (Phase 6 §4). Classification maps directly
onto the Enterprise Knowledge Base's own top-level folder structure -- already established,
not invented for this phase. A concept's `category` must be one of these eight; the
classifier's job here is to validate that mapping, not to guess intent from free text."""

KB_CATEGORIES = {
    "Core Concept": "TOGAF/",
    "Governance Rule": "Governance/",
    "Principle": "Governance/",
    "Pattern": "Patterns/",
    "Reasoning Rule": "Rules/",
    "Relationship Definition": "Relationships/",
    "Prompt Template": "Prompts/",
    "Validation Criterion": "Validation/",
    "Decomposition Rule": "Decomposition/",
}


def classify(category: str) -> str:
    """Normalizes and validates a raw category string against the known taxonomy.
    Raises ValueError for anything unrecognized -- callers (ingestion/QA) turn that into a
    reported error rather than a crash, since one bad concept must not abort a whole batch."""
    normalized = category.strip()
    for known in KB_CATEGORIES:
        if known.lower() == normalized.lower():
            return known
    raise ValueError(
        f"Unrecognized category '{category}'. Must be one of: {', '.join(KB_CATEGORIES)}"
    )
