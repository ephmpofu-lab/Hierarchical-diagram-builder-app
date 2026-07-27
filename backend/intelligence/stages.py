"""The 8-stage Enterprise Reasoning Pipeline (Phase 4 section 3). Each stage is one AI
Service call (WP4/ADR-002 -- never a vendor SDK directly), individually testable and
individually observable, matching the approved architecture's own stage-by-stage
input/output table rather than collapsing the pipeline into one opaque call."""

import json
from typing import List, Tuple

from pydantic import ValidationError

from ..ai import service as ai_service
from ..ai.provider import AIProviderError
from ..models import ProposedNode, ProposedRelationship, ProposedRisk

DOMAINS = ("Business", "Data", "Application", "Technology")


class ReasoningStageError(Exception):
    """A pipeline stage's AI call failed, or returned output that could not be parsed
    or validated against the expected shape."""


def _ask_json(system: str, prompt: str, max_tokens: int = 800) -> dict:
    # effort left at the AIProvider default ("none") deliberately -- WP4 found live that any
    # nonzero reasoning effort can consume the whole max_tokens budget on hidden reasoning and
    # return empty visible text with no error. A per-stage effort override, if a specific
    # stage's quality later needs deeper reasoning, is a real future refinement, not this MVP.
    try:
        result = ai_service.complete(system=system, prompt=prompt, max_tokens=max_tokens, json_mode=True)
    except AIProviderError as exc:
        raise ReasoningStageError(f"AI provider call failed: {exc}") from exc
    try:
        return json.loads(result.text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ReasoningStageError(f"Stage returned non-JSON output: {result.text!r}") from exc


def _ask_text(system: str, prompt: str, max_tokens: int = 500) -> str:
    try:
        result = ai_service.complete(system=system, prompt=prompt, max_tokens=max_tokens)
    except AIProviderError as exc:
        raise ReasoningStageError(f"AI provider call failed: {exc}") from exc
    return result.text.strip()


def _build(model_cls, items) -> list:
    built = []
    for item in items:
        try:
            built.append(model_cls(**item))
        except (ValidationError, TypeError) as exc:
            raise ReasoningStageError(f"Stage returned malformed {model_cls.__name__}: {item!r} ({exc})") from exc
    return built


def select_domains(objective: str, reasoning_context: str) -> List[str]:
    """Phase 4 section 5. Which of the four fixed TOGAF domains (Meta Model, Phase 3) an
    objective belongs to is mechanical routing, not EA judgment content -- the fixed
    4-domain set and "Business cascades to the other three" (ARC-0002) are part of this
    engine's own design, not something reasoned from retrieved knowledge. Any deeper
    domain-purpose nuance comes from `reasoning_context` when the Knowledge Base has
    relevant content; this system prompt deliberately states only the structural fact,
    never substantive EA content, so the engine still never hard-codes EA knowledge."""
    data = _ask_json(
        system=(
            "You are the domain-selection stage of an enterprise-architecture reasoning "
            "pipeline. The four TOGAF architecture domains are Business, Data, Application, "
            "and Technology. A Business-domain objective typically influences the other "
            "three; a narrowly technical objective may not. Respond with strict JSON only: "
            '{"primary": "<one of Business|Data|Application|Technology>", '
            '"influenced": [<zero or more of the other three>]}'
        ),
        prompt=f"Reasoning context:\n{reasoning_context}\n\nObjective:\n{objective}",
        max_tokens=200,
    )
    primary = data.get("primary")
    if primary not in DOMAINS:
        raise ReasoningStageError(f"Domain selection returned an unrecognized primary domain: {primary!r}")
    influenced = [d for d in data.get("influenced", []) if d in DOMAINS and d != primary]
    return [primary] + influenced


def business_analysis(objective: str, reasoning_context: str) -> str:
    """Stage 1 (ARC-0002). Why does this matter to the business?"""
    return _ask_text(
        system=(
            "You are the business-analysis stage of an enterprise-architecture reasoning "
            "pipeline. Explain, in 2-4 sentences, why the given objective matters to the "
            "business -- its motivation, not its implementation."
        ),
        prompt=f"Reasoning context:\n{reasoning_context}\n\nObjective:\n{objective}",
    )


def capability_analysis(objective: str, business_motivation: str) -> str:
    """Stage 2 (ARC-0006 Conceptual). What capability is required?"""
    return _ask_text(
        system=(
            "You are the capability-analysis stage. Given the business motivation, state "
            "in 1-3 sentences which business capability (or capabilities) this objective "
            "requires the enterprise to have or extend."
        ),
        prompt=f"Business motivation:\n{business_motivation}\n\nObjective:\n{objective}",
    )


def architecture_thinking(objective: str, capability_summary: str, reasoning_context: str) -> List[ProposedNode]:
    """Stage 3 (ARC-0001). How does this fit the wider structure? Produces a draft
    skeleton (candidate nodes) -- not a full recursive decomposition (Phase 5, WP8)."""
    data = _ask_json(
        system=(
            "You are the architecture-thinking stage of an enterprise-architecture "
            "reasoning pipeline. Given the required capability, propose at most 5 candidate "
            "architecture components (a draft skeleton, not a full decomposition) that "
            "would realize it -- the most essential ones, not an exhaustive list. Respond "
            'with strict JSON only: {"nodes": [{"label": str, "node_type": str or null, '
            '"notes": str}]}'
        ),
        prompt=(
            f"Reasoning context:\n{reasoning_context}\n\nCapability required:\n{capability_summary}"
            f"\n\nObjective:\n{objective}"
        ),
        max_tokens=1500,
    )
    return _build(ProposedNode, data.get("nodes", []))


def dependency_reasoning(objective: str, nodes: List[ProposedNode]) -> List[ProposedRelationship]:
    """Stage 4 (ARC-0008). What does this need to share information/services with?"""
    labels = [n.label for n in nodes]
    data = _ask_json(
        system=(
            "You are the dependency-reasoning stage. Given a draft set of architecture "
            "components, propose at most 8 relationships (data flow, dependency) between "
            "them -- only the ones that matter, not an exhaustive list. Only reference the "
            'given labels. Respond with strict JSON only: {"relationships": '
            '[{"from_label": str, "to_label": str, "label": str or null, '
            '"reference_type": str or null}]}'
        ),
        prompt=f"Components:\n{labels}\n\nObjective:\n{objective}",
        max_tokens=1500,
    )
    candidates = data.get("relationships", [])
    valid = [r for r in candidates if r.get("from_label") in labels and r.get("to_label") in labels]
    return _build(ProposedRelationship, valid)


def risk_reasoning(
    objective: str, nodes: List[ProposedNode], relationships: List[ProposedRelationship]
) -> List[ProposedRisk]:
    """Stage 5 (ARC-0021). What could go wrong?"""
    data = _ask_json(
        system=(
            "You are the risk-reasoning stage. Given the proposed architecture skeleton, "
            "identify at most the 5 most significant risks it introduces -- not an "
            'exhaustive list. Respond with strict JSON only: {"risks": [{"description": '
            'str, "classification": str or null, "initial_level": "Critical" or "High" '
            'or "Medium" or "Low"}]}'
        ),
        prompt=f"Components: {[n.label for n in nodes]}\nRelationship count: {len(relationships)}\n\nObjective:\n{objective}",
        max_tokens=1500,
    )
    return _build(ProposedRisk, data.get("risks", []))


def governance_reasoning(objective: str, nodes: List[ProposedNode], reasoning_context: str) -> Tuple[bool, List[str]]:
    """Stage 6 (ARC-0007, ARC-0016). Does this comply with our principles? A violation
    loops reasoning back to stage 3 (ARC-0003's "iterative, not waterfall" ADM
    characterisation, Phase 4 section 3's own design)."""
    data = _ask_json(
        system=(
            "You are the governance-reasoning stage. Check the proposed architecture "
            "components against any retrieved governance principles for violations. If no "
            "principles were retrieved, respond compliant -- there is nothing to check "
            "against. Respond with strict JSON only: "
            '{"compliant": bool, "violations": [str]}'
        ),
        prompt=f"Components: {[n.label for n in nodes]}\n\nGovernance context:\n{reasoning_context}",
        max_tokens=800,
    )
    return bool(data.get("compliant", True)), [str(v) for v in data.get("violations", [])]


def technology_reasoning(objective: str, nodes: List[ProposedNode]) -> List[ProposedNode]:
    """Stage 7 (ARC-0002 Technology, ARC-0006 Physical). With what will this be realised?
    Annotates each node's notes with a technology recommendation rather than inventing new
    nodes -- Solution Building Block selection refines stage 3's skeleton, it doesn't
    replace it."""
    labels = [n.label for n in nodes]
    data = _ask_json(
        system=(
            "You are the technology-reasoning stage. For each given component, suggest a "
            "brief (one sentence) technology/solution-building-block note, or an empty "
            'string if none is warranted yet. Respond with strict JSON only: '
            '{"annotations": [{"label": str, "technology_notes": str}]}'
        ),
        prompt=f"Components:\n{labels}\n\nObjective:\n{objective}",
        max_tokens=1200,
    )
    notes_by_label = {a["label"]: a.get("technology_notes", "") for a in data.get("annotations", []) if "label" in a}
    for node in nodes:
        note = notes_by_label.get(node.label)
        if note:
            node.notes = f"{node.notes} {note}".strip()
    return nodes


def implementation_reasoning(objective: str, nodes: List[ProposedNode]) -> str:
    """Stage 8 (ARC-0005). How far should this decompose right now? Produces a plan
    description only -- actually executing recursive decomposition is Phase 5/WP8's job,
    not this pipeline's."""
    return _ask_text(
        system=(
            "You are the implementation-reasoning stage. Briefly (one sentence each) "
            "describe, per component, whether it looks ready for further decomposition or "
            "already looks like a directly-executable task. Do not decompose it yourself."
        ),
        prompt=f"Components:\n{[n.label for n in nodes]}\n\nObjective:\n{objective}",
        max_tokens=1000,
    )
