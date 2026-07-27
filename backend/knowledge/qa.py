"""Knowledge validation and QA (Phase 6 §6). Four checks, run against a concept once it is
submitted for review: schema, consistency (related references resolve), duplicate/conflict,
and completeness. A Critical finding blocks the concept from reaching Active; a Warning is
surfaced but never blocks -- QA is a human review aid, not a fully automated gate (§6's own
framing: "a human review step, not an automated gate alone")."""

from typing import List

from ..models import KnowledgeConcept, QAFinding, QAReport


def run_qa(concept: KnowledgeConcept, other_concepts: List[KnowledgeConcept]) -> QAReport:
    findings: List[QAFinding] = []
    # Deliberately NOT filtered by concept_id -- the duplicate/conflict check below needs to
    # find another entry sharing this exact concept_id, which a naive self-exclusion would hide.
    by_id = {c.concept_id: c for c in other_concepts}

    # Schema validation -- required core fields present and non-blank. Types are already
    # enforced by the Pydantic model; this catches blank strings the type system allows.
    for field_name, value in (
        ("name", concept.name),
        ("category", concept.category),
        ("definition", concept.definition),
    ):
        if not value or not value.strip():
            findings.append(QAFinding(severity="Critical", message=f"'{field_name}' is required"))

    # Consistency validation -- every related reference must resolve to a real concept
    # (in the existing repository or elsewhere in the same ingestion batch); "no dangling
    # edges" is a hard invariant here (§6), the same severity the architecture's own broken-
    # reference check already treats as blocking, not merely advisory.
    for related_id in concept.related:
        if related_id not in by_id and related_id != concept.concept_id:
            findings.append(
                QAFinding(severity="Critical", message=f"related concept '{related_id}' does not exist")
            )

    # Duplicate/conflict validation -- a same-id concept with materially different content
    # is a conflict for human resolution, UNLESS this concept explicitly declares itself a
    # deliberate revision of that other concept via `supersedes`.
    existing_same_id = by_id.get(concept.concept_id)
    if existing_same_id and existing_same_id.definition != concept.definition:
        if concept.supersedes != existing_same_id.concept_id:
            findings.append(
                QAFinding(
                    severity="Critical",
                    message=(
                        f"concept_id '{concept.concept_id}' conflicts with existing content "
                        "of the same id; set supersedes if this is a deliberate revision"
                    ),
                )
            )

    # Completeness validation -- rules/validation blocks, where the concept's category
    # implies they matter, should be non-empty. Informational only, never blocking.
    if not concept.rules:
        findings.append(QAFinding(severity="Warning", message="no rules recorded for this concept"))
    if not concept.validation_criteria:
        findings.append(QAFinding(severity="Warning", message="no validation criteria recorded"))

    passed = not any(f.severity == "Critical" for f in findings)
    return QAReport(concept_id=concept.concept_id, passed=passed, findings=findings)
