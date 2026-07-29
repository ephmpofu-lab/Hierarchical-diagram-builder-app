"""Governance Assessment Tool (ADR-006, WP16c) -- backend/tools/tool.py's
GOVERNANCE_ASSESSMENT_TOOL entry, upgraded from partial to built.

Evidence base: ISO/IEC 38500's six governance principles (Responsibility, Strategy,
Acquisition, Performance, Conformance, Human Behaviour), COBIT's governance/management
distinction, TOGAF's Architecture Contract / Compliance concept.

WP6's existing backend/governance/validation.py already does real, deterministic
structural and policy validation -- that work is untouched here, not duplicated. What was
missing, per WP0b's own finding, is an explicit, citable mapping onto ISO 38500's named
principles rather than an implicit "governance passed/failed" result. This tool adds that
layer: six independently assessed principles, with Conformance treated as a hard gate
(mirroring how WP6 already treats a Critical finding as blocking regardless of anything
else) -- no amount of Strategy/Performance/etc. compliance can offset an unresolved
Critical finding, exactly the same precedence WP6 established.

Deliberately NOT wired into WP6's validation.py or the live governance workflow -- same
reasoning as WP16a/WP16b: this is a new, additional lens (citable against ISO 38500), not
a replacement for the already-tested structural/policy pass. Exists today as its own
independently callable tool."""

from ..models import GovernanceAssessmentResult, GovernanceAssessmentSignals

_PRINCIPLE_SIGNAL_MAP = {
    "Responsibility": "has_assigned_owner",
    "Strategy": "aligns_with_documented_strategy",
    "Acquisition": "acquisition_is_justified",
    "Performance": "has_performance_monitoring",
    "Human Behaviour": "considers_human_impact",
}


def assess(signals: GovernanceAssessmentSignals) -> GovernanceAssessmentResult:
    other_satisfied = [name for name, field in _PRINCIPLE_SIGNAL_MAP.items() if getattr(signals, field)]
    other_unmet = [name for name, field in _PRINCIPLE_SIGNAL_MAP.items() if not getattr(signals, field)]

    if not signals.has_no_unresolved_critical_findings:
        return GovernanceAssessmentResult(
            verdict="Non-Conformant",
            rationale="Unresolved Critical findings are a hard gate under ISO 38500's "
            "Conformance principle -- no other principle can offset this, mirroring how "
            "WP6's own governance workflow treats a Critical finding as blocking "
            "regardless of anything else.",
            principles_satisfied=other_satisfied,  # still reported even though the gate failed
            principles_unmet=["Conformance"] + other_unmet,
            signals=signals,
        )

    other_count = len(other_satisfied)
    if other_count == len(_PRINCIPLE_SIGNAL_MAP):
        verdict = "Fully Conformant"
    elif other_count >= 3:
        verdict = "Substantially Conformant"
    else:
        verdict = "Partially Conformant"

    return GovernanceAssessmentResult(
        verdict=verdict,
        rationale=(
            f"Conformance gate passed (no unresolved Critical findings); "
            f"{other_count}/{len(_PRINCIPLE_SIGNAL_MAP)} of the remaining ISO 38500 "
            f"principles are satisfied ({', '.join(other_satisfied) or 'none'}), which "
            f"maps to {verdict}."
        ),
        principles_satisfied=["Conformance"] + other_satisfied,
        principles_unmet=other_unmet,
        signals=signals,
    )


def explain(result: GovernanceAssessmentResult) -> str:
    """Optional: phrase an already-computed verdict in prose. Never re-derives
    `verdict` -- mirrors WP16a/WP16b's own explain() split."""
    from ..ai import service as ai_service

    prompt = (
        f"In two or three sentences, explain to a non-technical stakeholder why this "
        f"was assessed as '{result.verdict}', given: {result.rationale}"
    )
    response = ai_service.complete(
        system="You explain governance assessments in plain language for a non-technical audience.",
        prompt=prompt,
        max_tokens=200,
    )
    return response.text.strip()
