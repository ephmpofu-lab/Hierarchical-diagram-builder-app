"""Component Tree track (Module 11, Dual Tree Architecture) -- distinct from
backend/decompose/engine.py's Workflow Tree track. This module implements the pre-stages
that precede Stage 0 (Component Attribute Enumeration), per
ARCHITEQ-Dual-Tree-Architecture.md and rules/principles/component-decomposition.md.

Stage -3 (Requirements Engineering) is the only stage implemented so far (sub-plan 11a).
"""

from typing import List

from ..intelligence.stages import _ask_json
from ..models import Capability, Component, ExtractedRequirement


def extract_requirements(
    domain: str, prd_text: str, reasoning_context: str
) -> List[ExtractedRequirement]:
    """Stage -3 -- extracts a requirements list relevant to `domain` from the project's own
    PRD text (R24, CD1). Preserves each requirement's own PRD id (R1, R2, ...) verbatim,
    never inventing a new one. An item with no resolvable id is dropped -- a defensive
    filter, not yet a full Validator pass (CD1's traced_requirements[] check happens once
    Capabilities exist, sub-plan 11b)."""
    data = _ask_json(
        system=(
            "You are extracting functional and non-functional requirements from a "
            "project's PRD (Product Requirements Document) for one specific domain "
            "within that project. Read the PRD's own Requirements section and select "
            "only the requirements relevant to the given domain. For each one, preserve "
            "the PRD's own requirement id (e.g. R1, R2) exactly as written there -- never "
            "invent a new id, never renumber. If a genuinely relevant requirement has no "
            "clear id in the PRD text, omit it rather than guessing one. "
            'Respond with strict JSON only: {"requirements": [{"text": str, '
            '"prd_requirement_id": str}]}'
        ),
        prompt=f"Domain: {domain}\n\nPRD text:\n{prd_text}",
        max_tokens=1500,
    )
    extracted = []
    for item in data.get("requirements", []):
        prd_requirement_id = (item.get("prd_requirement_id") or "").strip()
        if not prd_requirement_id:
            continue
        extracted.append(ExtractedRequirement(
            text=item.get("text", ""), prd_requirement_id=prd_requirement_id, domain=domain,
        ))
    return extracted


def identify_capabilities(
    domain: str, requirements: List[ExtractedRequirement], reasoning_context: str
) -> List[Capability]:
    """Stage -2 -- groups Stage -3's extracted requirements into discrete capabilities
    (R25, CD1). A capability whose traced_requirements[] is empty after filtering against
    the real input requirement ids is rejected outright, not returned with an empty list --
    this is CD1's own predicate, not a separate Validator pass layered on top."""
    requirements_list = "\n".join(f"- [{r.prd_requirement_id}] {r.text}" for r in requirements)
    data = _ask_json(
        system=(
            "You are grouping a list of extracted requirements into discrete capabilities "
            "for one domain. A capability is a coherent grouping of one or more related "
            "requirements (e.g. requirements about accepting and validating file uploads "
            "become the capability 'Document Ingestion'). Every capability must list the "
            "exact requirement ids from the given list that it groups -- never invent a "
            "requirement id that isn't in the list, and never propose a capability with no "
            "requirements behind it. "
            'Respond with strict JSON only: {"capabilities": [{"label": str, '
            '"traced_requirement_ids": [str]}]}'
        ),
        prompt=f"Domain: {domain}\n\nRequirements:\n{requirements_list}\n\nReasoning context:\n{reasoning_context}",
        max_tokens=1500,
    )
    valid_ids = {r.prd_requirement_id for r in requirements}
    capabilities = []
    for item in data.get("capabilities", []):
        traced = [rid for rid in item.get("traced_requirement_ids", []) if rid in valid_ids]
        if not traced:
            continue
        capabilities.append(Capability(label=item.get("label", ""), traced_requirements=traced, domain=domain))
    return capabilities


def decompose_capability(capability: Capability, reasoning_context: str) -> List[Component]:
    """Stage -1 -- decomposes one capability into the components required to realize it
    (R26, CD2, CD3). Every returned Component is stamped with capability.label directly --
    CD2's realizes_capability requirement is satisfied by construction, never left to the
    model to supply or omit. Breadth-first ordering (CD3) is enforced by the future Stage -1
    orchestrator (11d) calling this once per capability, not by this function in isolation."""
    traced = ", ".join(capability.traced_requirements)
    data = _ask_json(
        system=(
            "You are decomposing one capability into the components required to realize "
            "it. A component is a distinct structural part of the system (e.g. the "
            "capability 'Document Ingestion' decomposes into components like 'Upload "
            "Source', 'File Validator', 'Text Extractor'). Propose every component needed "
            "-- do not omit one just because it seems minor, and do not invent components "
            "unrelated to this capability. "
            'Respond with strict JSON only: {"components": [{"label": str}]}'
        ),
        prompt=(
            f"Capability: {capability.label}\nTraced requirement ids: {traced}\n\n"
            f"Reasoning context:\n{reasoning_context}"
        ),
        max_tokens=1000,
    )
    components = []
    for item in data.get("components", []):
        label = (item.get("label") or "").strip()
        if not label:
            continue
        components.append(Component(label=label, realizes_capability=capability.label, domain=capability.domain))
    return components
