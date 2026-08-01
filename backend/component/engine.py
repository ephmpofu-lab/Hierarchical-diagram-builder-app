"""Component Tree track (Module 11, Dual Tree Architecture) -- distinct from
backend/decompose/engine.py's Workflow Tree track. This module implements the pre-stages
that precede Stage 0 (Component Attribute Enumeration), per
ARCHITEQ-Dual-Tree-Architecture.md and rules/principles/component-decomposition.md.

Stage -3 (Requirements Engineering) is the only stage implemented so far (sub-plan 11a).
"""

import re
from typing import Dict, List

from ..intelligence.stages import _ask_json
from ..models import Attribute, Capability, Component, DomainTaskTree, ExtractedRequirement

# A runaway-loop safety bound, NOT a depth ceiling (R21/CD9, amended by
# ARCHITEQ-Recursive-Depth-and-Completion-Tracking.md), same posture as
# MAX_ATOMICITY_SPLIT_DEPTH (backend/decompose/engine.py). A candidate that hits this bound
# while its name still needs splitting is NOT treated as a leaf -- check_attribute_leaf
# below is the whole-tree re-check that catches it, mirroring how check_p1_atomicity
# catches an Atomicity-Test straggler on the Workflow Tree side. Unlike the Workflow Tree
# (where check_p1_atomicity already existed), this check was genuinely missing until
# sub-plan 11h added it -- a real gap in 11d's own original scope, not a false alarm.
MAX_ATTRIBUTE_SPLIT_DEPTH = 3


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


def _attribute_needs_split(name: str) -> bool:
    """CD4's own literal test -- deliberately simpler than the Workflow Tree's formal
    5-criterion Atomicity Test (P1); CD4 states its own single criterion directly."""
    lowered = f" {name.lower()} "
    return " and " in lowered or "&" in name


def _split_attribute(name: str, type_: str, reasoning_context: str) -> List[dict]:
    """Stage 0's correction step for a compound attribute -- an AI call, mirroring
    _split_step's role for atomic steps at the attribute level."""
    data = _ask_json(
        system=(
            "You are the Component Tree's Stage 0 correction step. A candidate component "
            "attribute has a compound name (it contains 'and' or '&'), meaning it isn't "
            "actually a single named property with a single type. Split it into 2 or more "
            "attributes, each with its own single name and single type. "
            'Respond with strict JSON only: {"attributes": [{"name": str, "type": str}]}'
        ),
        prompt=f"Compound attribute: {name} ({type_})\n\nReasoning context:\n{reasoning_context}",
        max_tokens=500,
    )
    return data.get("attributes", [])


def enumerate_attributes(component: Component, reasoning_context: str) -> List[Attribute]:
    """Stage 0 -- enumerates one component's configuration attributes down to single-name,
    single-type leaves (R27, CD4). A candidate failing _attribute_needs_split is recursively
    split, bounded by MAX_ATTRIBUTE_SPLIT_DEPTH so a name that can't be cleanly split
    doesn't loop forever -- the last attempt is kept (never silently dropped), same posture
    as the Workflow Tree's own atomic-step split loop."""
    data = _ask_json(
        system=(
            "You are enumerating one component's configuration attributes down to the "
            "smallest meaningful unit. Each attribute must be a single named property with "
            "a single type (e.g. 'Batch Size: integer') -- never a compound description "
            "that would require an 'and' to describe its meaning. "
            'Respond with strict JSON only: {"attributes": [{"name": str, "type": str}]}'
        ),
        prompt=f"Component: {component.label}\n\nReasoning context:\n{reasoning_context}",
        max_tokens=1000,
    )
    final_attrs: List[Attribute] = []
    queue = [(c, 0) for c in data.get("attributes", [])]
    while queue:
        candidate, depth = queue.pop(0)
        name = (candidate.get("name") or "").strip()
        type_ = (candidate.get("type") or "").strip()
        if not name or not type_:
            continue
        # depth >= MAX_ATTRIBUTE_SPLIT_DEPTH with the name still needing a split is NOT
        # "good enough" -- check_attribute_leaf's later whole-tree pass re-runs
        # _attribute_needs_split against every attribute in the assembled Component Tree
        # and will surface this one as a real violation there (R21/CD9).
        if not _attribute_needs_split(name) or depth >= MAX_ATTRIBUTE_SPLIT_DEPTH:
            final_attrs.append(Attribute(
                name=name, type=type_, component_label=component.label, domain=component.domain,
            ))
            continue
        split_pieces = _split_attribute(name, type_, reasoning_context)
        if not split_pieces:
            final_attrs.append(Attribute(
                name=name, type=type_, component_label=component.label, domain=component.domain,
            ))
            continue
        queue.extend((piece, depth + 1) for piece in split_pieces)
    return final_attrs


def check_attribute_leaf(attributes: List[Attribute]) -> List[str]:
    """R21/CD9's real safety net for the Component Tree, mirroring
    backend/decompose/engine.py::check_p1_atomicity's role for the Workflow Tree -- re-runs
    _attribute_needs_split (the same test enumerate_attributes's inner loop already uses)
    against every attribute in the assembled tree, so a depth-capped-but-still-compound
    name from enumerate_attributes is genuinely caught here, never silently treated as a
    leaf. Returns one violation message per still-compound attribute name; empty if none."""
    violations = []
    for attr in attributes:
        if _attribute_needs_split(attr.name):
            violations.append(
                f"Attribute '{attr.name}' on component '{attr.component_label}' still requires "
                "splitting (CD4 attribute-leaf test) -- not a single named property with a single type"
            )
    return violations


def check_no_shared_attributes(attributes: List[Attribute]) -> List[str]:
    """R28/CD5 -- no two components claim the same attribute. Operates over the full set of
    attributes across every component in a domain, not per-component. Returns one
    human-readable violation message per attribute name claimed by more than one component;
    empty if none."""
    owners: Dict[str, set] = {}
    for attr in attributes:
        owners.setdefault(attr.name, set()).add(attr.component_label)
    violations = []
    for name, components in owners.items():
        if len(components) > 1:
            violations.append(
                f"Attribute '{name}' is claimed by more than one component: {', '.join(sorted(components))}"
            )
    return violations


def _canonical_name(name: str) -> str:
    """CD6's "canonical name" comparison -- lowercase, strip everything but letters/digits,
    so "Batch Size" and "batch_size" reconcile (both -> "batchsize"). Deliberately literal,
    not fuzzy/semantic matching -- see check_tree_reconciliation's own docstring for the
    real limitation this implies."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def check_tree_reconciliation(attributes: List[Attribute], tree: DomainTaskTree) -> List[str]:
    """R29/CD6, the Reconciliation Rule -- every Component Tree attribute must resolve to
    exactly one Workflow Tree variable (by canonical name) and vice versa. Returns one
    violation message per unmatched attribute or variable; empty if fully reconciled.

    Known limitation, not solved here: this only reconciles names that are the same words
    under formatting differences. It does not perform semantic matching between
    genuinely different-looking names for the same fact (e.g. the Dual-Tree-Architecture
    doc's own worked example, "Model" vs "model_name", would NOT reconcile under this
    check) -- that would need an explicit shared-alias mechanism at authoring time or a
    real AI judgment call, out of scope here."""
    variable_names = [
        variable.name
        for node in tree.nodes.values()
        if node.level == "Atomic step"
        for variable in node.variables
    ]
    attr_canon = {_canonical_name(a.name): a.name for a in attributes}
    var_canon = {_canonical_name(v): v for v in variable_names}

    violations = []
    for canon, original in attr_canon.items():
        if canon not in var_canon:
            violations.append(f"Component attribute '{original}' has no corresponding Workflow Tree variable")
    for canon, original in var_canon.items():
        if canon not in attr_canon:
            violations.append(f"Workflow Tree variable '{original}' has no corresponding Component attribute")
    return violations
