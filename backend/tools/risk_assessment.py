"""Risk Assessment Tool (ADR-006, WP16b) -- backend/tools/tool.py's RISK_ASSESSMENT_TOOL
entry, upgraded from partial to built.

Evidence base: ISO 31000's risk analysis step (combine likelihood and consequence to
derive a risk level via a documented matrix, never a single holistic judgment call), COSO
ERM's likelihood/impact scoring convention, NIST RMF's categorize-before-decide discipline.

WP5's risk_reasoning stage (backend/intelligence/stages.py) asks an LLM to pick
initial_level directly out of 4 fixed strings in one shot, with no documented derivation
-- exactly the "prompt-based, not evidence-based" gap WP0b named. This tool is the
deterministic replacement for that final step: given a likelihood and an impact rating on
ISO 31000-style 5-point scales, it computes the risk level from a fixed, auditable matrix
(likelihood score x impact score, banded into Critical/High/Medium/Low) rather than
asking an LLM to guess the combined severity directly.

Deliberately NOT wired into the live risk_reasoning stage yet -- same reasoning as
WP16a's AI Suitability Assessment Tool: that would change WP5's already-tested, shipped
behavior, and having the stage produce likelihood/impact separately (instead of a single
level) is itself an open design question this WP does not resolve. Exists today as its
own independently callable tool."""

from ..models import RiskAssessmentResult, RiskAssessmentSignals

_LIKELIHOOD_SCORE = {
    "Rare": 1,
    "Unlikely": 2,
    "Possible": 3,
    "Likely": 4,
    "Almost Certain": 5,
}
_IMPACT_SCORE = {
    "Negligible": 1,
    "Minor": 2,
    "Moderate": 3,
    "Major": 4,
    "Severe": 5,
}


def assess(signals: RiskAssessmentSignals) -> RiskAssessmentResult:
    if signals.likelihood not in _LIKELIHOOD_SCORE:
        raise ValueError(
            f"Unknown likelihood '{signals.likelihood}' -- must be one of {sorted(_LIKELIHOOD_SCORE)}"
        )
    if signals.impact not in _IMPACT_SCORE:
        raise ValueError(f"Unknown impact '{signals.impact}' -- must be one of {sorted(_IMPACT_SCORE)}")

    likelihood_score = _LIKELIHOOD_SCORE[signals.likelihood]
    impact_score = _IMPACT_SCORE[signals.impact]
    combined = likelihood_score * impact_score  # ISO 31000-style multiplicative risk matrix, max 25

    if combined >= 15:
        level = "Critical"
    elif combined >= 8:
        level = "High"
    elif combined >= 4:
        level = "Medium"
    else:
        level = "Low"

    return RiskAssessmentResult(
        level=level,
        rationale=(
            f"Likelihood '{signals.likelihood}' ({likelihood_score}/5) x impact "
            f"'{signals.impact}' ({impact_score}/5) = {combined}/25 on the risk matrix, "
            f"which maps to {level} per ISO 31000's likelihood-times-consequence convention."
        ),
        likelihood=signals.likelihood,
        impact=signals.impact,
    )


def explain(result: RiskAssessmentResult) -> str:
    """Optional: phrase an already-computed risk level in prose. Never re-derives
    `level` -- mirrors WP16a's own explain() split."""
    from ..ai import service as ai_service

    prompt = (
        f"In two or three sentences, explain to a non-technical stakeholder why this "
        f"risk was rated '{result.level}', given: {result.rationale}"
    )
    response = ai_service.complete(
        system="You explain risk assessments in plain language for a non-technical audience.",
        prompt=prompt,
        max_tokens=200,
    )
    return response.text.strip()
