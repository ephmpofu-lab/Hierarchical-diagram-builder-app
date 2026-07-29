"""Test Design Tool (ADR-006, WP16i) -- backend/tools/tool.py's TEST_DESIGN_TOOL entry,
upgraded from not_built to built.

Evidence base: ISTQB's Foundation Level syllabus, which defines four test levels by what
each one targets -- Component (Unit) Testing (a component in isolation), Integration
Testing (interactions between components), System Testing (the complete system's
end-to-end behaviour), Acceptance Testing (validation against business/user acceptance
criteria) -- and the Test Pyramid's qualitative principle (favour many fast component
tests over few slow end-to-end ones).

Deliberately does NOT fabricate a numeric test-count ratio (e.g. "70% unit, 20%
integration, 10% E2E") -- neither ISTQB nor the Test Pyramid's originator (Mike Cohn)
prescribe exact percentages, only a qualitative "many/some/few" shape, so inventing a
precise split would be exactly the kind of fabricated precision "Evidence-Based Tool
Engineering" was written to rule out. Instead this maps explicit, present/absent
characteristics of one component directly onto the ISTQB level(s) that characteristic
implies -- multiple levels can legitimately apply to the same component.

Deliberately NOT wired into any existing endpoint yet -- same reasoning as WP16a-h.
Exists today as its own independently callable tool."""

from ..models import TestDesignResult, TestDesignSignals

_LEVEL_CHECKS = [
    ("is_standalone_component", "Component Testing"),
    ("has_external_dependencies", "Integration Testing"),
    ("represents_end_to_end_behavior", "System Testing"),
    ("has_business_acceptance_criteria", "Acceptance Testing"),
]


def assess(signals: TestDesignSignals) -> TestDesignResult:
    recommended = [level for field, level in _LEVEL_CHECKS if getattr(signals, field)]

    if recommended:
        rationale = (
            f"{len(recommended)}/{len(_LEVEL_CHECKS)} ISTQB test levels apply based on "
            f"the signals present: {', '.join(recommended)}."
        )
    else:
        rationale = (
            "No signal indicates any ISTQB test level's defining characteristic is "
            "present -- nothing to recommend testing for from this input alone."
        )

    return TestDesignResult(recommended_levels=recommended, rationale=rationale, signals=signals)


def explain(result: TestDesignResult) -> str:
    """Optional: phrase already-computed recommendations in prose. Never adds or
    removes a recommended level -- mirrors WP16a-h's own explain() split."""
    from ..ai import service as ai_service

    prompt = (
        f"In two or three sentences, explain to a non-technical stakeholder why these "
        f"test levels were recommended: {', '.join(result.recommended_levels) or 'none'}, "
        f"given: {result.rationale}"
    )
    response = ai_service.complete(
        system="You explain test-design recommendations in plain language for a non-technical audience.",
        prompt=prompt,
        max_tokens=200,
    )
    return response.text.strip()
