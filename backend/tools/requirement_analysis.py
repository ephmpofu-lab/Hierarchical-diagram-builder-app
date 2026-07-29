"""Requirement Analysis Tool (ADR-006, WP16d) -- backend/tools/tool.py's
REQUIREMENT_ANALYSIS_TOOL entry, upgraded from partial to built.

Evidence base: Requirements Engineering's established "requirement smell" literature --
specifically INCOSE's Guide for Writing Requirements (weak/ambiguous terms that make a
requirement unverifiable) and IEEE 830's completeness/verifiability/consistency criteria.
These are deterministic, well-documented word/pattern checks, not a judgment call --
exactly why this can be a rule-based tool rather than an LLM asked to "review this
requirement," which would be neither reproducible nor citable to a specific standard.

WP1's Requirement model (id/description/parent_id/origin_node_id/status) has no fields
for acceptance criteria or ownership -- the "no interactive discovery loop" gap WP0b
named is about capturing those upstream, which this tool does not solve. What this tool
does solve: given a requirement's text (and whatever structural facts are already known),
deterministically flag the specific, named quality smells a human reviewer would
otherwise have to catch by eye every time.

Deliberately NOT wired into requirement creation/editing yet -- same reasoning as
WP16a-c: this is a new, additive check, not a blocking gate on the existing Requirement
endpoints. Exists today as its own independently callable tool."""

import re

from ..models import RequirementQualityResult, RequirementQualitySignals

# INCOSE Guide for Writing Requirements' own named categories of weak/ambiguous terms.
_WEAK_WORDS = {
    "etc", "and/or", "tbd", "as needed", "user-friendly", "easy to use",
    "appropriate", "adequate", "efficient", "flexible", "if possible",
    "if necessary", "but not limited to", "state of the art",
}
_VAGUE_QUANTIFIERS = {"some", "many", "few", "several", "most", "minimal"}
_OBLIGATION_MODALS = {"shall", "must", "will"}


def assess(signals: RequirementQualitySignals) -> RequirementQualityResult:
    text = signals.description.lower()
    findings: list[str] = []

    found_weak = sorted(w for w in _WEAK_WORDS if w in text)
    if found_weak:
        findings.append(
            f"Ambiguous language (INCOSE Guide for Writing Requirements): contains "
            f"{', '.join(repr(w) for w in found_weak)}."
        )

    found_vague = sorted(w for w in _VAGUE_QUANTIFIERS if re.search(rf"\b{re.escape(w)}\b", text))
    if found_vague:
        findings.append(
            f"Vague quantifier: contains {', '.join(repr(w) for w in found_vague)} "
            f"instead of a measurable amount."
        )

    if text.count(" and ") >= 2:
        findings.append(
            "Likely a compound requirement: multiple ' and 's suggest several distinct "
            "requirements bundled into one, which IEEE 830 recommends splitting so each "
            "can be independently verified."
        )

    if not any(modal in text for modal in _OBLIGATION_MODALS):
        findings.append(
            "Missing an explicit obligation modal ('shall'/'must'/'will') -- INCOSE's "
            "convention for stating a requirement as a clear, testable obligation."
        )

    if not signals.has_acceptance_criteria:
        findings.append("No acceptance criteria recorded -- IEEE 830's verifiability criterion is unmet.")

    if not signals.has_assigned_owner:
        findings.append("No owner assigned -- cannot be traced to an accountable stakeholder.")

    verdict = "Needs Revision" if findings else "Well-Formed"
    return RequirementQualityResult(verdict=verdict, findings=findings, signals=signals)


def explain(result: RequirementQualityResult) -> str:
    """Optional: phrase already-computed findings in prose. Never adds or removes a
    finding -- mirrors WP16a-c's own explain() split."""
    from ..ai import service as ai_service

    prompt = (
        f"In two or three sentences, explain to a non-technical stakeholder why this "
        f"requirement was assessed as '{result.verdict}', given these findings: "
        f"{'; '.join(result.findings) or 'none'}"
    )
    response = ai_service.complete(
        system="You explain requirements-quality findings in plain language for a non-technical audience.",
        prompt=prompt,
        max_tokens=200,
    )
    return response.text.strip()
