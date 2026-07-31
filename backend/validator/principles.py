"""P1-P8 (rules/decomposition_principles.json holds P1-P7's descriptive metadata;
rules/reference_architectures/ holds the TDSP/C4/Well-Architected/SOLID citations this
module's constants mirror -- same "cited spec vs. enforcement code" split this codebase
already established for P1-P7). Each check_* function takes the whole frozen tree (P7/P8/
the reference-architecture conformance check also take the domain's checklist) and returns
every violation found -- never raises, never stops at the first one, so a single correction
pass (backend/decompose/engine.py) can see the full picture. Kept as plain Python functions
rather than a JSON predicate language: a fixed, structurally-different set of rules doesn't
justify inventing a rule interpreter."""

import re
from typing import Dict, List

from ..models import DomainChecklist, DomainTaskTree, PrincipleViolation, TaskTreeNode
from ..render.node_mapper import load_schemas as _load_n8n_schemas

_CONJUNCTION_PATTERN = re.compile(r"\b(and|&)\b", re.IGNORECASE)
_CHOICE_PATTERN = re.compile(r"\b(or|either|depending on|based on the (type|kind))\b", re.IGNORECASE)
_INLINE_DEFAULT_PATTERN = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\S+")

# P6 -- implementation/vendor names a step's label must never be named after; function,
# not implementation ("generate embedding vector", not "call OpenAI API"). Binding to a
# real tool happens only at render time (backend/render/).
_IMPLEMENTATION_NAMES = (
    "openai", "gpt", "anthropic", "claude", "pinecone", "weaviate", "chroma", "postgres",
    "mysql", "mongodb", "redis", "aws", "azure", "gcp", "s3", "lambda", "docker",
    "kubernetes", "langchain", "llamaindex", "huggingface", "n8n",
)

# Mirrors rules/reference_architectures/tdsp.json exactly -- kept as a Python constant
# rather than re-read from disk on every check, the same "cited spec vs. enforcement code"
# split rules/decomposition_principles.json already established for P1-P7's own text.
TDSP_STAGES = (
    "business_understanding", "data_acquisition_ingestion", "data_preprocessing",
    "feature_engineering", "modeling", "deployment", "evaluation_acceptance",
)

# Mirrors rules/reference_architectures/well_architected.json exactly.
WELL_ARCHITECTED_PILLARS = (
    "security_relevant", "observability_relevant", "performance_relevant",
    "ops_relevant", "governance_relevant",
)

# C4 (rules/reference_architectures/c4_model.json): exactly these 3 real TaskTreeNode
# levels exist (Level 1 "Context" is the domain itself, never a node; Variable is Level 4's
# own parameters, not a 5th level) -- anything else is a nesting-depth violation.
_C4_LEVELS = ("Layer", "Sub-task", "Atomic step")


def _atomic_steps(tree: DomainTaskTree):
    return [n for n in tree.nodes.values() if n.level == "Atomic step"]


def check_atomicity_for_node(node: TaskTreeNode, n8n_schemas: dict = None) -> List[PrincipleViolation]:
    """The formal 5-criterion Atomicity Test (spec section 5) for ONE Atomic step, grounded
    in SOLID/SRP (rules/reference_architectures/solid.json). Exposed standalone (not just as
    part of check_p1_atomicity below) so backend/decompose/engine.py's Stage 3 can test a
    freshly-proposed candidate step before it's ever committed to a tree."""
    if n8n_schemas is None:
        n8n_schemas = _load_n8n_schemas()
    violations = []
    text = f"{node.label} {node.notes}"

    if _CONJUNCTION_PATTERN.search(node.label):  # criterion 1: single verb, single object
        violations.append(PrincipleViolation(
            principle_id="P1",
            message=f"Atomic step '{node.label}' fails Atomicity criterion 1 (single "
            "verb/object) -- reads as more than one action.",
            node_id=node.id,
        ))

    if not node.consumes:  # criterion 2: single named input
        violations.append(PrincipleViolation(
            principle_id="P1",
            message=f"Atomic step '{node.label}' fails Atomicity criterion 2 (single "
            "named input) -- no 'consumes' declared.",
            node_id=node.id,
        ))

    if not node.produces:  # criterion 3: single named output
        violations.append(PrincipleViolation(
            principle_id="P1",
            message=f"Atomic step '{node.label}' fails Atomicity criterion 3 (single "
            "named output) -- no 'produces' declared.",
            node_id=node.id,
        ))

    if _CHOICE_PATTERN.search(text):  # criterion 4: no hidden implementation choice
        violations.append(PrincipleViolation(
            principle_id="P1",
            message=f"Atomic step '{node.label}' fails Atomicity criterion 4 (hidden "
            "implementation choice) -- reads as a branch point, not one step.",
            node_id=node.id,
        ))

    # Criterion 5: maps to exactly one implementation unit -- a lookup against the real
    # Node Mapper schema catalog, not a judgment call (spec's own wording). A step whose
    # text matches keywords from more than one real (non-fallback) node type is a
    # concrete signal it secretly needs two implementation units.
    matched = [
        s["display_name"] for s in n8n_schemas["nodes"]
        if any(k in text.lower() for k in s["match_keywords"])
    ]
    if len(matched) > 1:
        violations.append(PrincipleViolation(
            principle_id="P1",
            message=f"Atomic step '{node.label}' fails Atomicity criterion 5 (one "
            f"implementation unit) -- matches multiple real node types "
            f"({', '.join(matched)}), suggesting it needs two.",
            node_id=node.id,
        ))
    return violations


def check_p1_atomicity(tree: DomainTaskTree) -> List[PrincipleViolation]:
    n8n_schemas = _load_n8n_schemas()
    violations = []
    for node in _atomic_steps(tree):
        violations.extend(check_atomicity_for_node(node, n8n_schemas))
    return violations


def check_p2_no_skip(tree: DomainTaskTree) -> List[PrincipleViolation]:
    # Operationalizes "breadth-first only" as a structural invariant on the finished tree:
    # a Layer's children must all be Sub-tasks, a Sub-task's children must all be Atomic
    # steps, and an Atomic step must be a leaf -- no level is ever skipped or reordered.
    expected_child_level = {"Layer": "Sub-task", "Sub-task": "Atomic step"}
    violations = []
    for node in tree.nodes.values():
        expected = expected_child_level.get(node.level)
        if expected is None:
            if node.children:
                violations.append(PrincipleViolation(
                    principle_id="P2",
                    message=f"'{node.label}' is an Atomic step but has children -- nothing decomposes past Atomic step.",
                    node_id=node.id,
                ))
            continue
        for child_id in node.children:
            child = tree.nodes.get(child_id)
            if child and child.level != expected:
                violations.append(PrincipleViolation(
                    principle_id="P2",
                    message=f"'{node.label}' ({node.level}) has a child '{child.label}' at level "
                    f"'{child.level}', skipping the required '{expected}' level.",
                    node_id=node.id,
                ))
    return violations


def check_p3_variable_exhaustion(tree: DomainTaskTree) -> List[PrincipleViolation]:
    # Can't verify a step lists *every* real-world parameter it touches, but can catch the
    # doc's own named failure mode: a default smuggled into prose (label/notes) instead of
    # declared as a Variable -- "chunk_overlap=50 is listed, never assumed silently."
    violations = []
    for node in _atomic_steps(tree):
        declared = {v.name for v in node.variables}
        for match in _INLINE_DEFAULT_PATTERN.finditer(f"{node.label} {node.notes}"):
            name = match.group(1)
            if name not in declared:
                violations.append(PrincipleViolation(
                    principle_id="P3",
                    message=f"Atomic step '{node.label}' mentions '{match.group(0)}' inline "
                    f"instead of declaring '{name}' as a Variable.",
                    node_id=node.id,
                ))
    return violations


def check_p4_dependency(tree: DomainTaskTree) -> List[PrincipleViolation]:
    violations = []
    for node in _atomic_steps(tree):
        if not node.produces:
            violations.append(PrincipleViolation(
                principle_id="P4",
                message=f"Atomic step '{node.label}' has no declared 'produces' output.",
                node_id=node.id,
            ))
    return violations


def check_p5_no_orphan(tree: DomainTaskTree) -> List[PrincipleViolation]:
    consumed_ids = {req_id for node in _atomic_steps(tree) for req_id in node.requires}
    violations = []
    for node in _atomic_steps(tree):
        if node.produces and not node.terminal_output and node.id not in consumed_ids:
            violations.append(PrincipleViolation(
                principle_id="P5",
                message=f"Atomic step '{node.label}' produces '{node.produces}' but nothing "
                "downstream consumes it, and it isn't flagged terminal_output.",
                node_id=node.id,
            ))
    return violations


def check_p6_tool_agnosticism(tree: DomainTaskTree) -> List[PrincipleViolation]:
    violations = []
    for node in _atomic_steps(tree):
        label_lower = node.label.lower()
        for name in _IMPLEMENTATION_NAMES:
            if name in label_lower:
                violations.append(PrincipleViolation(
                    principle_id="P6",
                    message=f"Atomic step '{node.label}' is named after an implementation "
                    f"('{name}') -- name it by function instead; binding happens at render time.",
                    node_id=node.id,
                ))
                break
    return violations


def check_p7_coverage_checklist(tree: DomainTaskTree, checklist: DomainChecklist) -> List[PrincipleViolation]:
    """Groups ALL root-level nodes by label (not a {label: id} dict, which would silently
    keep only the last same-labeled node) -- layer repetition (spec addendum Fix C) means
    more than one Layer node can legitimately share one label. Satisfied as long as AT
    LEAST ONE instance of a mandatory layer exists and is non-empty, matching Fix C's own
    stated rule."""
    ids_by_label: Dict[str, List[str]] = {}
    for nid in tree.root_ids:
        node = tree.nodes.get(nid)
        if node:
            ids_by_label.setdefault(node.label, []).append(nid)

    violations = []
    for entry in checklist.mandatory_layers:
        matching_ids = ids_by_label.get(entry.layer, [])
        if not matching_ids:
            violations.append(PrincipleViolation(
                principle_id="P7",
                message=f"Mandatory layer '{entry.layer}' is missing from the tree.",
            ))
        elif not any(tree.nodes[nid].children for nid in matching_ids):
            violations.append(PrincipleViolation(
                principle_id="P7",
                message=f"Mandatory layer '{entry.layer}' is present but empty "
                f"(checked {len(matching_ids)} instance(s)).",
                node_id=matching_ids[0],
            ))
    return violations


def check_p8_cross_cutting_coverage(tree: DomainTaskTree) -> List[PrincipleViolation]:
    """Spec section 3 -- every Well-Architected pillar must be addressed by at least one
    Atomic step SOMEWHERE in the whole tree; not required per-layer."""
    tagged_pillars = {tag for node in _atomic_steps(tree) for tag in node.pillar_tags}
    violations = []
    for pillar in WELL_ARCHITECTED_PILLARS:
        if pillar not in tagged_pillars:
            violations.append(PrincipleViolation(
                principle_id="P8",
                message=f"No atomic step addresses {pillar} anywhere in the tree.",
            ))
    return violations


def check_reference_architecture_conformance(tree: DomainTaskTree, checklist: DomainChecklist) -> List[PrincipleViolation]:
    """Spec section 7, category 2 -- (a) every layer maps to a named TDSP stage or is
    explicitly marked cross_cutting (checked against the checklist entry Stage 1 built that
    layer from); (b) nesting depth never exceeds C4's 3 real levels."""
    violations = []
    entries_by_layer = {entry.layer: entry for entry in checklist.mandatory_layers}
    for layer_id in tree.root_ids:
        layer = tree.nodes.get(layer_id)
        if layer is None:
            continue
        entry = entries_by_layer.get(layer.label)
        if entry is None:
            violations.append(PrincipleViolation(
                principle_id="RefArch",
                message=f"Layer '{layer.label}' has no matching checklist entry to justify it.",
                node_id=layer.id,
            ))
        elif not entry.cross_cutting and entry.tdsp_stage not in TDSP_STAGES:
            violations.append(PrincipleViolation(
                principle_id="RefArch",
                message=f"Layer '{layer.label}' maps to no valid TDSP stage and isn't marked cross_cutting.",
                node_id=layer.id,
            ))

    for node in tree.nodes.values():
        if node.level not in _C4_LEVELS:
            violations.append(PrincipleViolation(
                principle_id="C4",
                message=f"Node '{node.label}' has level '{node.level}', outside C4's fixed "
                f"nesting ({', '.join(_C4_LEVELS)}).",
                node_id=node.id,
            ))
    return violations


# Every principle checkable from the tree alone, in the spec's own P1-P8 order --
# validator/service.py runs these plus check_p7_coverage_checklist and
# check_reference_architecture_conformance (which additionally need the domain's checklist).
STRUCTURAL_CHECKS = (
    check_p1_atomicity,
    check_p2_no_skip,
    check_p3_variable_exhaustion,
    check_p4_dependency,
    check_p5_no_orphan,
    check_p6_tool_agnosticism,
    check_p8_cross_cutting_coverage,
)
