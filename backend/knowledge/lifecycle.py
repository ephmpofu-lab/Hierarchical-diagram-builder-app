"""Knowledge versioning and lifecycle (Phase 6 §9). Encodes the exact state diagram edges --
only Active concepts are ever served to new reasoning cycles (§5); Superseded/Deprecated/
Archived remain queryable for provenance but are never retrieved for new context assembly.

    Proposed --> UnderReview   (submitted for QA)
    UnderReview --> Rejected   (fails QA / conflicts)
    UnderReview --> Active     (approved by Knowledge Governance)
    Active --> Superseded      (a revised version is approved)
    Active --> Deprecated      (retired directly)
    Superseded --> Deprecated  (after a retention window)
    Deprecated --> Archived

"Superseded" here means an Active concept has been marked as replaced by a separate
concept (its own concept_id, cross-linked via that concept's `supersedes` field) -- not an
atomic rewrite under one shared identity. See models.py's KnowledgeConcept.supersedes for why."""

_ALLOWED_TRANSITIONS = {
    "Proposed": {"UnderReview"},
    "UnderReview": {"Rejected", "Active"},
    "Active": {"Superseded", "Deprecated"},
    "Superseded": {"Deprecated"},
    "Deprecated": {"Archived"},
    "Rejected": set(),
    "Archived": set(),
}

RETRIEVABLE_STATUS = "Active"


def can_transition(current: str, target: str) -> bool:
    return target in _ALLOWED_TRANSITIONS.get(current, set())


def require_transition(current: str, target: str) -> None:
    if not can_transition(current, target):
        raise ValueError(f"Cannot transition a knowledge concept from '{current}' to '{target}'")
