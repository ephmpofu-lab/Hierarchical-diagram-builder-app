"""Decomposition Engine -- the one-time, per-domain authoring pipeline (doc section 4.2;
build order per the ARCHITEQ Decomposition Engine spec, section 4). Runs four strict,
breadth-first stages across the WHOLE tree before moving to the next -- Stage 0/1 (Domain
Resolution / Layer Instantiation, deterministic, no AI call), Stage 2 (Sub-task Generation,
one AI call per layer), Stage 3 (Atomic Step Generation, with the formal Atomicity Test and
recursive splitting on failure), Stage 4 (Variable Exhaustion, grounded in the real Node
Mapper schema). This only runs when a domain has no frozen tree yet -- once a human
approves (backend/taxonomy/repository.save_tree/save_checklist), it's frozen and this never
runs again for that domain. Build order (this file) is discarded after validation; the
separate topological/execution order (backend/render/python_renderer.py's
_topological_order, reused by node_mapper.py) is what both renderers actually consume."""

import json
import uuid
from typing import Dict, List

from pydantic import ValidationError

from ..intelligence.stages import _ask_json, ReasoningStageError
from ..models import DomainChecklist, DomainTaskTree, LayerChecklistEntry, TaskTreeNode, Variable
from ..render.node_mapper import load_schemas, match_schema
from ..taxonomy import repository as taxonomy_repo
from ..validator.principles import TDSP_STAGES, WELL_ARCHITECTED_PILLARS, check_atomicity_for_node
from ..validator.service import validate_tree

# Small fixed constants, not adaptive -- same posture as MAX_GOVERNANCE_LOOPS
# (intelligence/pipeline.py) and MAX_DISCOVERY_TURNS (discovery/service.py).
MAX_DECOMPOSITION_RETRIES = 3
MAX_ATOMICITY_SPLIT_DEPTH = 3


def propose_checklist(domain: str, reasoning_context: str) -> DomainChecklist:
    """First-draft checklist for a brand-new domain (doc section 4.4's "app drafts, user
    approves" answer), grounded in TDSP (spec section 2.1) -- a human reviews/edits this
    once before it locks. Only offers the model the real, fixed TDSP stage ids, never lets
    it invent new ones."""
    stage_list = ", ".join(TDSP_STAGES)
    data = _ask_json(
        system=(
            "You are proposing a domain checklist grounded in the Team Data Science "
            "Process (TDSP) for an engineering decomposition system's ML/AI pipeline "
            "domains. Propose 4-10 mandatory top-level layers (e.g. for a RAG pipeline: "
            "Ingestion, Preprocessing, Embedding, Storage, Retrieval, Augmentation, "
            "Generation, Evaluation). For EACH layer, map it to exactly one of these TDSP "
            f"stage ids: {stage_list} -- or set cross_cutting: true instead if the layer "
            "genuinely isn't domain-vertical work but a cross-cutting concern (rare; most "
            "layers map to a real stage). Also declare each layer's input_contract "
            "(artifact names it consumes) and output_contract (artifact names it must "
            "produce) -- these anchor later sub-task generation. "
            'Respond with strict JSON only: {"derived_from": "tdsp", "mandatory_layers": '
            '[{"layer": str, "tdsp_stage": str or null, "cross_cutting": bool, '
            '"input_contract": [str], "output_contract": [str]}]}'
        ),
        prompt=f"Domain: {domain}\n\nReasoning context:\n{reasoning_context}",
        max_tokens=1500,
    )
    entries = [LayerChecklistEntry(**entry) for entry in data.get("mandatory_layers", [])]
    return DomainChecklist(domain=domain, derived_from=data.get("derived_from", "tdsp"), mandatory_layers=entries)


def instantiate_layers(domain: str, checklist: DomainChecklist) -> DomainTaskTree:
    """Stage 0/1 -- Domain Resolution + Layer Instantiation. Deterministic, no AI call:
    layer labels come straight from the checklist, so they can never drift from it (unlike
    before, where the AI invented layer names later caught only by P7 after the fact)."""
    nodes: Dict[str, TaskTreeNode] = {}
    root_ids: List[str] = []
    for entry in checklist.mandatory_layers:
        layer_id = str(uuid.uuid4())
        root_ids.append(layer_id)
        nodes[layer_id] = TaskTreeNode(id=layer_id, label=entry.layer, level="Layer")
    return DomainTaskTree(domain=domain, root_ids=root_ids, nodes=nodes)


def _generate_subtasks_for_layer(entry: LayerChecklistEntry, reasoning_context: str) -> List[dict]:
    """Stage 2 -- one AI call per layer, anchored to that layer's own Input/Output
    Contract. Run once per layer, for every layer, before any layer's sub-tasks decompose
    further into atomic steps (spec section 4's own breadth-first requirement).

    Returns a list of branches (spec addendum, Fix C -- layer repetition): normally exactly
    one, meaning no repetition. More than one only when the grounded reality genuinely
    diverges (e.g. two structurally different ingestion sources needing two separate
    Preprocessing branches) -- never split arbitrarily. The orchestrator
    (_run_stages_2_and_3) reuses this layer's own already-created node for branch 0 and
    creates additional same-label Layer nodes for branches 1+."""
    data = _ask_json(
        system=(
            "You are Stage 2 (Sub-task Generation) of a Decomposition Engine. Given a "
            "Layer's Input Contract and Output Contract, propose the minimal set of "
            "Sub-tasks (transformations) needed to move from the input artifacts to the "
            "output artifacts. Propose at most 3 sub-tasks, named by function, never by "
            "implementation/vendor. Normally return exactly ONE branch with branch_label: "
            "null. Only return more than one branch if this Layer's real-world work "
            "genuinely splits into separate parallel workflows (e.g. two structurally "
            "different input sources each needing their own sub-tasks) -- never split "
            "arbitrarily just to have more than one. "
            'Respond with strict JSON only: {"branches": [{"branch_label": str or null, '
            '"sub_tasks": [{"label": str}]}]}'
        ),
        prompt=(
            f"Layer: {entry.layer}\nInput Contract: {entry.input_contract}\n"
            f"Output Contract: {entry.output_contract}\n\nReasoning context:\n{reasoning_context}"
        ),
        max_tokens=500,
    )
    branches = data.get("branches", [])
    return branches or [{"branch_label": None, "sub_tasks": []}]


def run_operator_simulation(entry: LayerChecklistEntry, sub_task_label: str, reasoning_context: str) -> List[str]:
    """Stage 2.5 (spec addendum Fix A) -- Operator trace: simulates a real person doing this
    Sub-task by hand today, with no automation. Grounds Stage 3 in what actually happens,
    rather than an abstract, invented description."""
    data = _ask_json(
        system=(
            "You are the Decomposition Engine's Grounding Simulation -- Operator trace. "
            "Simulate a real person performing this Sub-task by hand today, with no "
            "automation. Output an ordered list of the actual micro-actions a human would "
            "take, in order -- concrete and specific to this real sub-task, never generic. "
            'Respond with strict JSON only: {"actions": [str]}'
        ),
        prompt=(
            f"Layer: {entry.layer}\nSub-task: {sub_task_label}\n"
            f"Layer Input Contract: {entry.input_contract}\nLayer Output Contract: {entry.output_contract}\n\n"
            f"Reasoning context:\n{reasoning_context}"
        ),
        max_tokens=600,
    )
    return data.get("actions", [])


def run_builder_simulation(entry: LayerChecklistEntry, sub_task_label: str, reasoning_context: str) -> List[str]:
    """Stage 2.5 -- Builder trace: simulates a developer implementing this Sub-task in
    code. This is the PRIMARY trace (merge_traces below) -- it is what actually becomes
    code/nodes, whereas the Operator trace only fills genuine gaps."""
    data = _ask_json(
        system=(
            "You are the Decomposition Engine's Grounding Simulation -- Builder trace. "
            "Simulate a developer implementing this Sub-task in code. Output an ordered "
            "list of the actual implementation-level operations needed to automate it -- "
            "concrete, specific operations (e.g. receive file object, validate file type, "
            "read file bytes, handle unsupported format), never an abstract description. "
            'Respond with strict JSON only: {"actions": [str]}'
        ),
        prompt=(
            f"Layer: {entry.layer}\nSub-task: {sub_task_label}\n"
            f"Layer Input Contract: {entry.input_contract}\nLayer Output Contract: {entry.output_contract}\n\n"
            f"Reasoning context:\n{reasoning_context}"
        ),
        max_tokens=600,
    )
    return data.get("actions", [])


def merge_traces(operator_trace: List[str], builder_trace: List[str], reasoning_context: str) -> List[str]:
    """Stage 2.5 -- merges the two traces into one ordered candidate action list. Builder
    trace is primary; Operator trace only fills genuine gaps (e.g. a progress indicator or
    confirmation step a real user still needs that the Builder trace omitted)."""
    data = _ask_json(
        system=(
            "You are the Decomposition Engine's Grounding Simulation -- trace merge. You "
            "are given an Operator trace (what a human does by hand) and a Builder trace "
            "(the implementation-level operations a developer needs). Merge them into ONE "
            "ordered action list: the Builder trace is primary -- it is what actually "
            "becomes code/nodes. Use the Operator trace only to catch anything a real user "
            "still needs that the Builder trace omitted (e.g. a progress indicator, a "
            "confirmation step). Do not duplicate actions that are effectively the same. "
            'Respond with strict JSON only: {"actions": [str]}'
        ),
        prompt=(
            f"Operator trace:\n{json.dumps(operator_trace)}\n\n"
            f"Builder trace:\n{json.dumps(builder_trace)}\n\nReasoning context:\n{reasoning_context}"
        ),
        max_tokens=700,
    )
    actions = data.get("actions", [])
    return actions or builder_trace  # fall back to the builder trace alone if the merge call returns nothing usable


def structure_trace_into_atomic_specs(
    entry: LayerChecklistEntry, sub_task_label: str, merged_trace: List[str],
    produced_so_far: List[str], reasoning_context: str,
) -> List[dict]:
    """Stage 3's initial proposal, revised (spec addendum Fix A): grounded in a real trace
    of actual micro-actions (Stage 2.5), not an invented description. Preserves the trace's
    own ordering/granularity as a strong prior -- merging over-granular adjacent actions is
    prompt guidance here, not a separate mechanical detection loop (only "too broad" is
    mechanically checkable, by the Atomicity Test that runs after this, in
    _generate_and_test_atomic_steps)."""
    produced_lines = "\n".join(f"- {label}" for label in produced_so_far) or "(none yet)"
    data = _ask_json(
        system=(
            "You are Stage 3 (Atomic Step Generation) of a Decomposition Engine, given a "
            "grounded trace of the real micro-actions this Sub-task requires (from a "
            "Grounding Simulation, not invented). Turn the trace into candidate Atomic "
            "steps, preserving its ordering and granularity as a strong prior: normally one "
            "atomic step per trace action, UNLESS two adjacent trace actions are so small "
            "they obviously belong to one real function/node together, in which case merge "
            "them into one step now -- never invent actions the trace didn't include, and "
            "never merge away a genuinely distinct operation. Each resulting step has "
            "exactly one action, one named input (consumes), one named output (produces), "
            "a requires list (labels of EARLIER atomic steps -- from this or a prior layer "
            "-- whose output this one needs), variables (every configurable parameter, "
            "including sensible defaults), pillar_tags (any of "
            f"{', '.join(WELL_ARCHITECTED_PILLARS)} this step genuinely addresses, or "
            "empty), and rules (real constraints, e.g. \"accepted formats: pdf, docx, "
            "txt\", or empty if none genuinely apply). Name steps by function, never by "
            "implementation/vendor. "
            'Respond with strict JSON only: {"atomic_steps": [{"label": str, "consumes": '
            'str, "produces": str, "requires": [str], "terminal_output": bool, '
            '"variables": [{"name": str, "default": str or null, "description": str}], '
            '"pillar_tags": [str], "rules": [str], "notes": str}]}'
        ),
        prompt=(
            f"Layer: {entry.layer}\nSub-task: {sub_task_label}\n"
            f"Layer Input Contract: {entry.input_contract}\nLayer Output Contract: {entry.output_contract}\n"
            f"Grounded trace (ordered):\n{json.dumps(merged_trace)}\n\n"
            f"Outputs already produced earlier in the tree:\n{produced_lines}\n\n"
            f"Reasoning context:\n{reasoning_context}"
        ),
        max_tokens=1800,
    )
    return data.get("atomic_steps", [])


def _split_step(candidate: dict, violation_messages: List[str], reasoning_context: str) -> List[dict]:
    """Stage 3's correction step -- an AI call, not heuristic string surgery, since one of
    the five Atomicity criteria (hidden implementation choice) genuinely needs judgment.
    The first resulting piece keeps the original's consumes/external requires; the LAST
    keeps the original's exact produces value and terminal_output flag, so anything already
    depending on that output still resolves after the split."""
    violation_lines = "\n".join(f"- {m}" for m in violation_messages)
    data = _ask_json(
        system=(
            "You are the Decomposition Engine's Atomicity correction step. A candidate "
            "Atomic step failed the Atomicity Test. Split it into 2 or more steps such "
            "that each one independently satisfies: exactly one action/one named input/"
            "one named output, no hidden implementation choice, and maps to one real "
            "implementation unit. Chain the resulting steps in order via requires -- the "
            "FIRST piece keeps the original's consumes and any external requires; the "
            "LAST piece keeps the original's exact produces value and terminal_output "
            "flag, so anything downstream that already depends on that output still "
            "resolves. Distribute the original's variables, pillar_tags, and rules across "
            "the pieces sensibly -- whichever piece a constraint actually governs. "
            'Respond with strict JSON only: {"atomic_steps": [{"label": str, "consumes": '
            'str, "produces": str, "requires": [str], "terminal_output": bool, '
            '"variables": [{"name": str, "default": str or null, "description": str}], '
            '"pillar_tags": [str], "rules": [str], "notes": str}]}'
        ),
        prompt=(
            f"Original candidate step:\n{json.dumps(candidate)}\n\n"
            f"Atomicity violations:\n{violation_lines}\n\nReasoning context:\n{reasoning_context}"
        ),
        max_tokens=800,
    )
    return data.get("atomic_steps", [])


def _generate_and_test_atomic_steps(
    entry: LayerChecklistEntry, sub_task_label: str, produced_so_far: List[str], reasoning_context: str
) -> "tuple[List[dict], Dict[str, List[str]]]":
    """Runs Stage 2.5 (Grounding Simulation: Operator + Builder + merge), Stage 3's
    trace-grounded structuring, the Atomicity Test, and recursive splitting on failure --
    bounded by MAX_ATOMICITY_SPLIT_DEPTH so a step that can't be cleanly split doesn't loop
    forever; the last attempt is kept (never silently dropped) for the Validator's own final
    pass to surface if it's still imperfect. Returns (accepted atomic-step specs, the
    grounding record) -- the caller (_run_stages_2_and_3) collects grounding records across
    the whole tree, and propose_tree persists them (taxonomy_repo.save_grounding) only once
    the tree they belong to actually passes validation."""
    operator_trace = run_operator_simulation(entry, sub_task_label, reasoning_context)
    builder_trace = run_builder_simulation(entry, sub_task_label, reasoning_context)
    merged_trace = merge_traces(operator_trace, builder_trace, reasoning_context)
    grounding_record = {
        "operator_trace": operator_trace, "builder_trace": builder_trace, "merged_trace": merged_trace,
    }

    n8n_schemas = load_schemas()
    candidates = structure_trace_into_atomic_specs(entry, sub_task_label, merged_trace, produced_so_far, reasoning_context)
    accepted: List[dict] = []
    queue = [(c, 0) for c in candidates]
    while queue:
        candidate, depth = queue.pop(0)
        temp_node = TaskTreeNode(
            id="temp", label=candidate.get("label", ""), level="Atomic step",
            consumes=candidate.get("consumes"), produces=candidate.get("produces"),
            notes=candidate.get("notes", ""),
        )
        violations = check_atomicity_for_node(temp_node, n8n_schemas)
        if not violations or depth >= MAX_ATOMICITY_SPLIT_DEPTH:
            accepted.append(candidate)
            continue
        split_pieces = _split_step(candidate, [v.message for v in violations], reasoning_context)
        if not split_pieces:
            accepted.append(candidate)  # nothing usable came back -- keep the original
            continue
        queue.extend((piece, depth + 1) for piece in split_pieces)
    return accepted, grounding_record


def _run_stages_2_and_3(tree: DomainTaskTree, checklist: DomainChecklist, reasoning_context: str) -> Dict[str, dict]:
    """Stage 2 (every layer's sub-tasks, now possibly multiple branches per layer -- Fix C)
    then Stage 3 (every branch's sub-tasks' atomic steps), processed in checklist order so
    each layer's generation can see every earlier layer's already-produced outputs -- the
    checklist's own order becomes the first topological pass (spec section 6, point 3).
    Returns every sub-task's grounding record (Stage 2.5), keyed by that sub-task's own
    node id -- propose_tree persists this only once the whole tree passes validation."""
    atomic_label_to_id: Dict[str, str] = {}
    produced_so_far: List[str] = []
    layer_id_by_label = {tree.nodes[nid].label: nid for nid in tree.root_ids}
    grounding_by_subtask: Dict[str, dict] = {}

    for entry in checklist.mandatory_layers:
        original_layer_id = layer_id_by_label.get(entry.layer)
        if original_layer_id is None:
            continue
        branches = _generate_subtasks_for_layer(entry, reasoning_context)

        for branch_index, branch in enumerate(branches):
            if branch_index == 0:
                # Branch 0 always reuses Stage 1's already-created node -- repetition never
                # changes the common, single-branch case's ids.
                layer_id = original_layer_id
            else:
                # Fix C -- layer repetition: additional branches get a NEW node sharing the
                # SAME label as the checklist entry (never a modified label). Same label is
                # deliberate: check_reference_architecture_conformance already iterates every
                # root_id individually, and check_p7_coverage_checklist groups by label
                # (fixed below) -- both work with zero extra special-casing this way. The
                # branch_label distinguishes it for a human via `notes` only.
                layer_id = str(uuid.uuid4())
                tree.nodes[layer_id] = TaskTreeNode(
                    id=layer_id, label=entry.layer, level="Layer",
                    notes=branch.get("branch_label") or "",
                )
                tree.root_ids.append(layer_id)

            sub_task_ids = []
            for sub_task_spec in branch.get("sub_tasks", []):
                sub_id = str(uuid.uuid4())
                sub_task_ids.append(sub_id)
                sub_label = sub_task_spec.get("label", "")
                tree.nodes[sub_id] = TaskTreeNode(id=sub_id, label=sub_label, level="Sub-task", parent_id=layer_id)

                atomic_specs, grounding_record = _generate_and_test_atomic_steps(
                    entry, sub_label, produced_so_far, reasoning_context
                )
                grounding_by_subtask[sub_id] = {"sub_task_label": sub_label, **grounding_record}
                atomic_ids = []
                for spec in atomic_specs:
                    step_id = str(uuid.uuid4())
                    atomic_ids.append(step_id)
                    label = spec.get("label", "")
                    atomic_label_to_id[label] = step_id
                    variables = [
                        Variable(name=v.get("name", ""), default=v.get("default"), description=v.get("description", ""))
                        for v in spec.get("variables", [])
                    ]
                    tree.nodes[step_id] = TaskTreeNode(
                        id=step_id, label=label, level="Atomic step", parent_id=sub_id,
                        consumes=spec.get("consumes"), produces=spec.get("produces"),
                        terminal_output=bool(spec.get("terminal_output", False)),
                        requires=spec.get("requires", []) or [],  # still raw labels -- resolved below
                        variables=variables, pillar_tags=spec.get("pillar_tags", []) or [],
                        rules=spec.get("rules", []) or [],
                        notes=spec.get("notes", ""),
                    )
                    if spec.get("produces"):
                        produced_so_far.append(spec["produces"])
                tree.nodes[sub_id].children = atomic_ids
            tree.nodes[layer_id].children = sub_task_ids

    # Resolve every atomic step's requires (raw labels) into real ids -- same "never invent
    # references" posture as before: an unresolvable label is silently dropped.
    for node in tree.nodes.values():
        if node.level == "Atomic step":
            node.requires = [atomic_label_to_id[r] for r in node.requires if r in atomic_label_to_id]

    return grounding_by_subtask


def exhaust_variables(tree: DomainTaskTree) -> None:
    """Stage 4 -- for every Atomic step, ground its variables in the real implementation
    schema. The only structured, real parameter schema this app has at build time is the
    vendored n8n catalog (there's no equivalent structured "Python function signature"
    catalog to look up against); any of that schema's own default parameters not already
    declared get added."""
    schemas = load_schemas()
    for node in tree.nodes.values():
        if node.level != "Atomic step":
            continue
        schema = match_schema(node, schemas)
        declared = {v.name for v in node.variables}
        for key, default_value in schema.get("default_parameters", {}).items():
            if key not in declared:
                node.variables.append(Variable(
                    name=key, default=str(default_value),
                    description=f"Default parameter of the matched {schema['display_name']} implementation.",
                ))


def _save_grounding_for_tree(domain: str, grounding_by_subtask: Dict[str, dict]) -> None:
    """Writes the grounding cache (spec addendum Section 2a) once -- ONLY for the winning,
    validated attempt's own (now-permanently-frozen) sub-task ids. Each sub-task starts at
    grounding_version 1; regroup_subtask's confirm step is what appends later versions."""
    sub_tasks = {
        sub_id: {
            "sub_task_label": record["sub_task_label"],
            "versions": [{
                "grounding_version": 1,
                "operator_trace": record["operator_trace"],
                "builder_trace": record["builder_trace"],
                "merged_trace": record["merged_trace"],
            }],
        }
        for sub_id, record in grounding_by_subtask.items()
    }
    taxonomy_repo.save_grounding(domain, {"domain": domain, "sub_tasks": sub_tasks})


def propose_tree(domain: str, reasoning_context: str, checklist: DomainChecklist) -> DomainTaskTree:
    """Orchestrates the full build order: Stage 0/1 (deterministic) -> Stage 2/2.5/3
    (per-layer, per-sub-task Grounding Simulation + Atomicity testing) -> Stage 4 (variable
    grounding) -> the Validator. On failure, retries the whole of stages 1-4 (checklist/
    Stage-0 output never changes) with the specific violations appended to every stage's
    reasoning context -- each stage's own regenerated content naturally responds to
    whichever violations actually name it. The grounding cache is written once, only for
    the attempt that actually passes (decision 4, plan doc) -- ids are fresh every retry, so
    a mid-pipeline cache hit was never possible anyway; this is an audit trail plus the
    substrate regroup_subtask reads and appends to, not a redundant-work optimization."""
    context = reasoning_context
    tree = None
    for _ in range(MAX_DECOMPOSITION_RETRIES):
        tree = instantiate_layers(domain, checklist)
        grounding_by_subtask = _run_stages_2_and_3(tree, checklist, context)
        exhaust_variables(tree)
        result = validate_tree(tree, checklist)
        if result.passed:
            _save_grounding_for_tree(domain, grounding_by_subtask)
            return tree
        violation_lines = "\n".join(f"- {v.message}" for v in result.violations)
        context = (
            f"{reasoning_context}\n\nYour previous attempt had these violations -- avoid "
            f"them this time:\n{violation_lines}"
        )
    return tree  # last attempt, even if still failing -- caller surfaces violations for human review


def refine_tree(tree: DomainTaskTree, instruction: str) -> DomainTaskTree:
    """AMENDMENT 4 item 6 -- the persistent Command/Refine Input's backend. One AI call
    proposing a TARGETED mutation to an already-frozen tree from a natural-language
    instruction (e.g. "also add a rate-limiting step to Retrieval") -- not a regeneration
    through Stages 1-4. The model is given the tree's own flat, id-keyed JSON directly and
    told to echo every untouched node's id back unchanged, so nothing downstream that
    already references those ids breaks; new nodes get a fresh id the model invents. The
    caller (api.py) validates the result and only re-freezes (taxonomy_repo.save_tree) if
    it passes -- refine_tree itself never writes to disk."""
    data = _ask_json(
        system=(
            "You are the Decomposition Engine's refinement step. You are given a complete, "
            "already-frozen task tree as JSON (root_ids, and nodes: a flat id-keyed map of "
            "TaskTreeNode -- id/label/level/parent_id/children/requires/consumes/produces/"
            "terminal_output/variables/pillar_tags/rules/notes) and a natural-language "
            "instruction describing ONE change to make. Apply only that change -- add, "
            "modify, or remove the minimal set of nodes needed; never relabel, restructure, "
            "or remove anything the instruction didn't ask about. CRITICAL: every existing "
            "node you don't change must be returned byte-for-byte identical, same id -- "
            "anything downstream referencing it by id depends on this. For any new node, "
            "invent a new, unique id string not already used. Update parent_id/children/"
            "requires consistently for whatever you add or remove. Every atomic step still "
            "needs consumes and produces; any new output must be consumed downstream or "
            "marked terminal_output; declare rules (real constraints, e.g. \"max file "
            "size: 50MB\") only where they genuinely exist -- an empty list is fine. "
            'Respond with strict JSON only, the exact same shape as the tree you were '
            'given: {"domain": str, "version": int, "root_ids": [str], "nodes": '
            '{"<id>": {"id": str, "label": str, "level": str, "parent_id": str or null, '
            '"children": [str], "requires": [str], "consumes": str or null, "produces": '
            'str or null, "terminal_output": bool, "variables": [{"name": str, "default": '
            'str or null, "description": str}], "pillar_tags": [str], "rules": [str], '
            '"notes": str}}}'
        ),
        prompt=f"Current tree:\n{json.dumps(tree.model_dump())}\n\nInstruction: {instruction}",
        max_tokens=16000,
    )
    try:
        return DomainTaskTree(**data)
    except (ValidationError, TypeError) as exc:
        raise ReasoningStageError(f"Refine step returned a malformed tree: {data!r} ({exc})") from exc


def regroup_subtask(entry: LayerChecklistEntry, sub_task_label: str, reasoning_context: str) -> Dict[str, List[str]]:
    """Manually-triggered re-grounding for ONE already-frozen sub-task (spec addendum
    Section 2a's refinement mechanism) -- re-runs Operator+Builder+Merge using that
    sub-task's own still-valid Layer/label context. Returns the new version UN-SAVED; the
    caller (api.py) is responsible for explicit confirmation before appending it to that
    sub-task's versions[] (taxonomy_repo.save_grounding) -- this function never writes.
    Deliberately does not touch the frozen tree.json or regenerate atomic steps -- re-
    deriving atomic steps from a corrected trace and merging them into a live tree is a
    real, separate follow-up action, out of scope here."""
    operator_trace = run_operator_simulation(entry, sub_task_label, reasoning_context)
    builder_trace = run_builder_simulation(entry, sub_task_label, reasoning_context)
    merged_trace = merge_traces(operator_trace, builder_trace, reasoning_context)
    return {"operator_trace": operator_trace, "builder_trace": builder_trace, "merged_trace": merged_trace}
