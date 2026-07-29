"""AI Suitability Assessment Tool (ADR-006, WP16a) -- backend/tools/tool.py's
AI_SUITABILITY_ASSESSMENT_TOOL entry, upgraded from not_built to built.

Evidence base: NIST AI RMF's govern-before-build principle (use AI only where it is
actually warranted, not by default), ISO/IEC 42001's risk-proportionate AI management, and
standard decision theory (an ordered, documented rule priority over explicit signals,
rather than an unweighted vote or freeform judgment).

The classification itself is a deterministic decision tree over explicit boolean signals
-- it never calls an LLM. This mirrors WP6's own split between deterministic enforcement
and upstream LLM judgment (validation.py does not re-derive what WP5's governance_reasoning
stage already judged); here, `assess()` never re-derives what should be an explicit,
already-known signal, and `explain()` is a strictly optional, separate step that phrases an
already-decided result in prose -- it can never change `recommended_pattern`.

Rule order matters and is not incidental: full-determinism is checked first (NIST AI RMF's
"don't reach for AI where a rules engine or workflow will do"), Agentic AI is checked next
precisely because it is the highest-governance-burden pattern and should only be chosen
when explicitly signalled, never defaulted into."""

from ..models import AISuitabilityAssessment, AISuitabilitySignals


def assess(signals: AISuitabilitySignals) -> AISuitabilityAssessment:
    if signals.process_is_fully_deterministic and not signals.requires_natural_language_understanding_or_generation:
        return AISuitabilityAssessment(
            recommended_pattern="Rules Engine",
            rationale="The process is fully deterministic and needs no natural-language "
            "handling -- a rules engine or plain workflow automation satisfies it without "
            "AI, per NIST AI RMF's principle of using AI only where it is actually "
            "warranted.",
            signals=signals,
        )
    if signals.requires_multi_step_autonomous_tool_use:
        return AISuitabilityAssessment(
            recommended_pattern="Agentic AI",
            rationale="The task requires autonomous, multi-step tool orchestration -- the "
            "defining trait of an agentic pattern, and the highest-governance-burden "
            "option, so it is recommended only when this signal is explicitly present, "
            "never defaulted into.",
            signals=signals,
        )
    if signals.requires_external_knowledge_retrieval:
        return AISuitabilityAssessment(
            recommended_pattern="RAG",
            rationale="The task depends on retrieving external or proprietary knowledge "
            "at run time -- retrieval-augmented generation grounds responses in that "
            "knowledge rather than relying on a model's parametric memory.",
            signals=signals,
        )
    if signals.requires_pattern_prediction_from_historical_data:
        return AISuitabilityAssessment(
            recommended_pattern="Predictive AI",
            rationale="The task is a forecasting or classification problem over "
            "historical data -- a predictive model, not a generative one, is the "
            "appropriate fit.",
            signals=signals,
        )
    if signals.requires_natural_language_understanding_or_generation:
        return AISuitabilityAssessment(
            recommended_pattern="Generic LLM",
            rationale="The task needs open-ended natural-language understanding or "
            "generation with none of the higher-governance-burden signals present -- a "
            "direct LLM call is sufficient without a specialised pattern.",
            signals=signals,
        )
    return AISuitabilityAssessment(
        recommended_pattern="Workflow Automation",
        rationale="No signal indicates AI is required -- deterministic workflow "
        "automation is the safe default per NIST AI RMF's principle of avoiding AI where "
        "it isn't warranted.",
        signals=signals,
    )


def explain(assessment: AISuitabilityAssessment) -> str:
    """Optional: ask the AI Service to phrase an already-decided assessment in plain
    language for a non-technical stakeholder. Never re-decides `recommended_pattern` --
    the returned text is prose only, and callers must not parse it for the decision."""
    from ..ai import service as ai_service

    prompt = (
        f"In two or three sentences, explain to a non-technical stakeholder why "
        f"'{assessment.recommended_pattern}' is the recommended approach, given this "
        f"reasoning: {assessment.rationale}"
    )
    result = ai_service.complete(
        system="You explain technical AI-pattern recommendations in plain language for a non-technical audience.",
        prompt=prompt,
        max_tokens=200,
    )
    return result.text.strip()
