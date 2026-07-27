"""The Decision & Approval Workflow (Phase 10 section 3) -- the canonical path every
proposal, AI-generated or manual, passes through:

    PROPOSAL -> confidence gate -> structural validation -> policy validation ->
    risk check -> COMMIT, or REJECT / HELD along the way.

This computes the workflow's outcome for a WP5 ReasoningResult in one pass rather than
literally pausing mid-pipeline for a human -- the diagram's intent (nothing commits
without the appropriate gate being satisfied) is preserved by never returning "approved"
unless every gate that applies has actually passed. Committing to a project is a
separate, later step (this WP does not implement it, matching WP5's own scope line)."""

from ..models import GovernanceReview, ReasoningResult
from .validation import validate_policy, validate_structure


def run_decision_workflow(result: ReasoningResult) -> GovernanceReview:
    findings = validate_structure(result) + validate_policy(result)

    if any(f.severity == "Critical" and f.category == "structural" for f in findings):
        return GovernanceReview(
            outcome="rejected",
            findings=findings,
            rationale="Structural validation found a Critical issue; a proposal with broken "
            "internal references cannot proceed.",
        )

    if any(f.severity == "Critical" and f.category == "policy" for f in findings):
        return GovernanceReview(
            outcome="rejected",
            findings=findings,
            rationale="Policy validation found an unresolved governance-principle violation.",
        )

    if result.requires_human_review:
        return GovernanceReview(
            outcome="held_pending_human_review",
            findings=findings,
            requires_human_review=True,
            requires_risk_acceptance=bool(result.proposed_risks),
            rationale=f"Confidence tier is {result.confidence_tier}; Phase 4 section 8 requires "
            "a human review before this proposal may proceed.",
        )

    if result.proposed_risks:
        return GovernanceReview(
            outcome="held_pending_risk_acceptance",
            findings=findings,
            requires_risk_acceptance=True,
            rationale="A Risk is only 'managed' once formally accepted (Phase 10 section 6) -- "
            "always a human act, never automatic.",
        )

    return GovernanceReview(
        outcome="approved",
        findings=findings,
        rationale="Passed structural and policy validation; High confidence; no unresolved risk.",
    )
