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
    further into atomic steps (spec section 4's own breadth-first requirement)."""
    data = _ask_json(
        system=(
            "You are Stage 2 (Sub-task Generation) of a Decomposition Engine. Given a "
            "Layer's Input Contract and Output Contract, propose the minimal set of "
            "Sub-tasks (transformations) needed to move from the input artifacts to the "
            "output artifacts. Propose at most 3 sub-tasks, named by function, never by "
            "implementation/vendor. "
            'Respond with strict JSON only: {"sub_tasks": [{"label": str}]}'
        ),
        prompt=(
            f"Layer: {entry.layer}\nInput Contract: {entry.input_contract}\n"
            f"Output Contract: {entry.output_contract}\n\nReasoning context:\n{reasoning_context}"
        ),
        max_tokens=500,
    )
    return data.get("sub_tasks", [])


def _generate_atomic_steps_for_subtask(
    entry: LayerChecklistEntry, sub_task_label: str, produced_so_far: List[str], reasoning_context: str
) -> List[dict]:
    """Stage 3's initial proposal, before the Atomicity Test runs."""
    produced_lines = "\n".join(f"- {label}" for label in produced_so_far) or "(none yet)"
    data = _ask_json(
        system=(
            "You are Stage 3 (Atomic Step Generation) of a Decomposition Engine. Given a "
            "Sub-task within a Layer, propose candidate Atomic steps. Each step has "
            "exactly one action, one named input (consumes), one named output (produces), "
            "a requires list (labels of EARLIER atomic steps -- from this or a prior layer "
            "-- whose output this one needs), variables (every configurable parameter, "
            "including ones with sensible defaults), pillar_tags (any of "
            f"{', '.join(WELL_ARCHITECTED_PILLARS)} this step genuinely addresses, or "
            "an empty list -- never force a tag that doesn't fit), and rules (the real "
            "validation or business constraints governing this step, e.g. \"accepted "
            "formats: pdf, docx, txt\" or \"max file size: 50MB\" -- only where a genuine "
            "constraint exists; an empty list is correct for a step with none, never "
            "invent one). Name steps by function, never by implementation/vendor. Propose "
            "at most 3 atomic steps. "
            'Respond with strict JSON only: {"atomic_steps": [{"label": str, "consumes": '
            'str, "produces": str, "requires": [str], "terminal_output": bool, '
            '"variables": [{"name": str, "default": str or null, "description": str}], '
            '"pillar_tags": [str], "rules": [str], "notes": str}]}'
        ),
        prompt=(
            f"Layer: {entry.layer}\nSub-task: {sub_task_label}\n"
            f"Layer Input Contract: {entry.input_contract}\nLayer Output Contract: {entry.output_contract}\n"
            f"Outputs already produced earlier in the tree:\n{produced_lines}\n\n"
            f"Reasoning context:\n{reasoning_context}"
        ),
        max_tokens=1500,
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
) -> List[dict]:
    """Runs Stage 3's proposal, the Atomicity Test, and recursive splitting on failure --
    bounded by MAX_ATOMICITY_SPLIT_DEPTH so a step that can't be cleanly split doesn't loop
    forever; the last attempt is kept (never silently dropped) for the Validator's own final
    pass to surface if it's still imperfect."""
    n8n_schemas = load_schemas()
    candidates = _generate_atomic_steps_for_subtask(entry, sub_task_label, produced_so_far, reasoning_context)
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
    return accepted


def _run_stages_2_and_3(tree: DomainTaskTree, checklist: DomainChecklist, reasoning_context: str) -> None:
    """Stage 2 (every layer's sub-tasks) then Stage 3 (every sub-task's atomic steps),
    processed in checklist order so each layer's generation can see every earlier layer's
    already-produced outputs -- the checklist's own order becomes the first topological
    pass (spec section 6, point 3)."""
    atomic_label_to_id: Dict[str, str] = {}
    produced_so_far: List[str] = []
    layer_id_by_label = {tree.nodes[nid].label: nid for nid in tree.root_ids}

    for entry in checklist.mandatory_layers:
        layer_id = layer_id_by_label.get(entry.layer)
        if layer_id is None:
            continue
        sub_task_specs = _generate_subtasks_for_layer(entry, reasoning_context)
        sub_task_ids = []
        for sub_task_spec in sub_task_specs:
            sub_id = str(uuid.uuid4())
            sub_task_ids.append(sub_id)
            sub_label = sub_task_spec.get("label", "")
            tree.nodes[sub_id] = TaskTreeNode(id=sub_id, label=sub_label, level="Sub-task", parent_id=layer_id)

            atomic_specs = _generate_and_test_atomic_steps(entry, sub_label, produced_so_far, reasoning_context)
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


def propose_tree(domain: str, reasoning_context: str, checklist: DomainChecklist) -> DomainTaskTree:
    """Orchestrates the full build order: Stage 0/1 (deterministic) -> Stage 2/3 (per-layer,
    per-sub-task AI calls with Atomicity testing) -> Stage 4 (variable grounding) -> the
    Validator. On failure, retries the whole of stages 1-4 (checklist/Stage-0 output never
    changes) with the specific violations appended to every stage's reasoning context --
    each stage's own regenerated content naturally responds to whichever violations
    actually name it."""
    context = reasoning_context
    tree = None
    for _ in range(MAX_DECOMPOSITION_RETRIES):
        tree = instantiate_layers(domain, checklist)
        _run_stages_2_and_3(tree, checklist, context)
        exhaust_variables(tree)
        result = validate_tree(tree, checklist)
        if result.passed:
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
