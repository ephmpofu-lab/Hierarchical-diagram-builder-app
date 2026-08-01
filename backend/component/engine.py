"""Component Tree track (Module 11, Dual Tree Architecture) -- distinct from
backend/decompose/engine.py's Workflow Tree track. This module implements the pre-stages
that precede Stage 0 (Component Attribute Enumeration), per
ARCHITEQ-Dual-Tree-Architecture.md and rules/principles/component-decomposition.md.

Stage -3 (Requirements Engineering) is the only stage implemented so far (sub-plan 11a).
"""

from typing import List

from ..intelligence.stages import _ask_json
from ..models import ExtractedRequirement


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
