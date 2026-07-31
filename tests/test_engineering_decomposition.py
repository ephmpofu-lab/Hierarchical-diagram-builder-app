"""Engineering Decomposition & Solution Generation pipeline tests (supersedes the TOGAF
Architecture Generation direction -- see the plan doc). Covers backend/validator/ (the
formal P1 Atomicity Test, P2-P7, the new P8 Cross-Cutting Coverage rule, and the reference-
architecture-conformance category -- see AMENDMENT 3 in the plan doc), backend/taxonomy/
repository.py (file-based load/save round trip), backend/intent/service.py (rule-based +
LLM-fallback intent parsing), backend/decompose/engine.py (the 4-stage build order: Layer
Instantiation, per-layer Sub-task Generation, per-sub-task Atomic Step Generation with
recursive Atomicity-Test splitting, Variable Exhaustion), backend/render/python_renderer.py
(dependency-ordered code blocks), backend/render/node_mapper.py + n8n_exporter.py, and the
/api/decompose/* endpoints end to end. AI calls are mocked throughout via each module's own
_ask_json entry point (never spend real money on every test run) -- engine.py now makes a
DIFFERENT call per stage, so mocks route on a marker string in the `system` prompt ("Stage
2", "Stage 3", "Atomicity correction") rather than returning one fixed shape. Any file-based
taxonomy/checklist writes use a __WP_DECOMPOSE_TEST__-prefixed domain name and clean up via
try/finally so the real `rag` domain files are never touched.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app import app
from backend.auth import AuthenticatedUser, require_auth
from backend.decompose import engine as decompose_engine
from backend.intelligence.stages import ReasoningStageError
from backend.intent import service as intent_service
from backend.models import (
    DomainChecklist,
    DomainTaskTree,
    IntentResult,
    LayerChecklistEntry,
    TaskTreeNode,
    Variable,
)
from backend.render import node_mapper
from backend.render.n8n_exporter import export_workflow
from backend.render.python_renderer import render_python
from backend.taxonomy import repository as taxonomy_repo
from backend.validator import principles
from backend.validator.service import validate_tree

TEST_DOMAIN = "__wp_decompose_test__"

# All 5 Well-Architected pillar tags, split across two groups for convenience in tests that
# need full tree-wide P8 coverage without every node carrying every tag.
_PILLARS_A = ["security_relevant", "observability_relevant"]
_PILLARS_B = ["performance_relevant", "ops_relevant", "governance_relevant"]


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp-decompose-test-user", email="decompose@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _atomic(id_, label, *, consumes=None, requires=None, produces=None, terminal_output=False,
            variables=None, pillar_tags=None, rules=None, notes="", parent_id=None):
    return TaskTreeNode(
        id=id_, label=label, level="Atomic step", parent_id=parent_id, consumes=consumes,
        requires=requires or [], produces=produces, terminal_output=terminal_output,
        variables=variables or [], pillar_tags=pillar_tags or [], rules=rules or [], notes=notes,
    )


def _sub_task(id_, label, children, parent_id=None):
    return TaskTreeNode(id=id_, label=label, level="Sub-task", parent_id=parent_id, children=children)


def _layer(id_, label, children):
    return TaskTreeNode(id=id_, label=label, level="Layer", children=children)


def _valid_tree() -> DomainTaskTree:
    # Layer -> Sub-task -> two Atomic steps, one consuming the other's output, the second
    # marked terminal_output -- passes every structural principle (P1-P8) and, paired with
    # _checklist("Ingestion"), the reference-architecture category too.
    step_a = _atomic("a1", "Read source file", consumes="source_config", produces="raw_text",
                      pillar_tags=_PILLARS_A, parent_id="s1")
    step_b = _atomic("a2", "Split text into chunks", consumes="raw_text", requires=["a1"], produces="chunks",
                      terminal_output=True, variables=[Variable(name="chunk_size", default="500")],
                      pillar_tags=_PILLARS_B, parent_id="s1")
    sub = _sub_task("s1", "Load and chunk", ["a1", "a2"], parent_id="l1")
    layer = _layer("l1", "Ingestion", ["s1"])
    return DomainTaskTree(
        domain=TEST_DOMAIN, root_ids=["l1"],
        nodes={"l1": layer, "s1": sub, "a1": step_a, "a2": step_b},
    )


def _checklist(*layer_names, stage="data_acquisition_ingestion") -> DomainChecklist:
    return DomainChecklist(domain=TEST_DOMAIN, derived_from="tdsp", mandatory_layers=[
        LayerChecklistEntry(layer=name, tdsp_stage=stage, input_contract=[], output_contract=[])
        for name in layer_names
    ])


def _stage_router(stage2=None, stage3=None, split=None):
    """Routes a mocked _ask_json call by a marker string in its `system` prompt --
    engine.py's own stages each state which one they are (see engine.py's system prompts)."""
    def _mock(system, prompt, max_tokens=1500):
        if "Stage 2" in system and stage2 is not None:
            return stage2
        if "Stage 3" in system and stage3 is not None:
            return stage3
        if "Atomicity correction" in system and split is not None:
            return split
        raise AssertionError(f"Unexpected _ask_json call, no mock registered: {system[:60]!r}")
    return _mock


# ---------- Unit tests: P1 (formal 5-criterion Atomicity Test) ----------


def test_atomicity_criterion1_conjunction_in_label():
    tree = _valid_tree()
    tree.nodes["a1"].label = "Read and parse source file"
    violations = principles.check_p1_atomicity(tree)
    assert any("criterion 1" in v.message and v.principle_id == "P1" for v in violations)


def test_atomicity_criterion2_missing_consumes():
    tree = _valid_tree()
    tree.nodes["a1"].consumes = None
    violations = principles.check_p1_atomicity(tree)
    assert any("criterion 2" in v.message for v in violations)


def test_atomicity_criterion3_missing_produces():
    tree = _valid_tree()
    tree.nodes["a1"].produces = None
    violations = principles.check_p1_atomicity(tree)
    assert any("criterion 3" in v.message for v in violations)


def test_atomicity_criterion4_hidden_implementation_choice():
    tree = _valid_tree()
    tree.nodes["a1"].label = "Choose chunking strategy depending on the document type"
    violations = principles.check_p1_atomicity(tree)
    assert any("criterion 4" in v.message for v in violations)


def test_atomicity_criterion5_matches_multiple_implementation_units():
    tree = _valid_tree()
    tree.nodes["a1"].label = "Call retrieval API then store results in database"
    violations = principles.check_p1_atomicity(tree)
    assert any("criterion 5" in v.message for v in violations)


def test_atomicity_passes_clean_step_on_all_five_criteria():
    assert principles.check_p1_atomicity(_valid_tree()) == []


# ---------- Unit tests: P2-P7 (unchanged structural checks) ----------


def test_p2_no_skip_flags_layer_with_atomic_step_child():
    tree = _valid_tree()
    tree.nodes["l1"].children = ["a1"]  # Layer -> Atomic step directly, skipping Sub-task
    violations = principles.check_p2_no_skip(tree)
    assert any(v.principle_id == "P2" for v in violations)


def test_p2_no_skip_flags_atomic_step_with_children():
    tree = _valid_tree()
    tree.nodes["a1"].children = ["a2"]
    violations = principles.check_p2_no_skip(tree)
    assert any(v.principle_id == "P2" for v in violations)


def test_p3_flags_inline_default_not_declared_as_variable():
    tree = _valid_tree()
    tree.nodes["a1"].notes = "uses chunk_overlap=50 internally"
    violations = principles.check_p3_variable_exhaustion(tree)
    assert len(violations) == 1
    assert "chunk_overlap" in violations[0].message


def test_p3_passes_when_default_is_declared():
    tree = _valid_tree()
    tree.nodes["a1"].notes = "uses chunk_size=500 internally"
    tree.nodes["a1"].variables = [Variable(name="chunk_size", default="500")]
    assert principles.check_p3_variable_exhaustion(tree) == []


def test_p4_flags_missing_produces():
    tree = _valid_tree()
    tree.nodes["a2"].produces = None
    violations = principles.check_p4_dependency(tree)
    assert any(v.principle_id == "P4" and v.node_id == "a2" for v in violations)


def test_p5_flags_unconsumed_non_terminal_output():
    tree = _valid_tree()
    tree.nodes["a2"].terminal_output = False  # produces "chunks", nothing requires "a2"
    violations = principles.check_p5_no_orphan(tree)
    assert any(v.principle_id == "P5" and v.node_id == "a2" for v in violations)


def test_p5_passes_when_flagged_terminal():
    assert principles.check_p5_no_orphan(_valid_tree()) == []


def test_p6_flags_implementation_name():
    tree = _valid_tree()
    tree.nodes["a1"].label = "Call OpenAI embeddings API"
    violations = principles.check_p6_tool_agnosticism(tree)
    assert any(v.principle_id == "P6" for v in violations)


def test_p7_flags_missing_mandatory_layer():
    tree = _valid_tree()
    checklist = _checklist("Ingestion", "Retrieval")
    violations = principles.check_p7_coverage_checklist(tree, checklist)
    assert any(v.principle_id == "P7" and "Retrieval" in v.message for v in violations)


def test_p7_flags_empty_mandatory_layer():
    tree = _valid_tree()
    tree.nodes["l1"].children = []
    checklist = _checklist("Ingestion")
    violations = principles.check_p7_coverage_checklist(tree, checklist)
    assert any(v.principle_id == "P7" and "empty" in v.message for v in violations)


def test_p7_passes_when_one_of_two_same_labeled_layers_is_non_empty():
    # Layer repetition (Fix C): a second Layer node sharing "Ingestion"'s label but empty
    # must not fail P7 as long as at least one same-labeled instance has real content --
    # the old {label: id} dict silently kept only the LAST one, which this guards against.
    tree = _valid_tree()
    tree.nodes["l1_empty"] = TaskTreeNode(id="l1_empty", label="Ingestion", level="Layer", children=[])
    tree.root_ids.append("l1_empty")
    checklist = _checklist("Ingestion")
    violations = principles.check_p7_coverage_checklist(tree, checklist)
    assert violations == []


def test_p7_flags_mandatory_layer_when_every_same_labeled_instance_is_empty():
    tree = _valid_tree()
    tree.nodes["l1"].children = []
    tree.nodes["l1_empty"] = TaskTreeNode(id="l1_empty", label="Ingestion", level="Layer", children=[])
    tree.root_ids.append("l1_empty")
    checklist = _checklist("Ingestion")
    violations = principles.check_p7_coverage_checklist(tree, checklist)
    assert any(v.principle_id == "P7" and "empty" in v.message for v in violations)


# ---------- Unit tests: P8 (Cross-Cutting Concerns) ----------


def test_p8_flags_every_missing_pillar_tree_wide():
    tree = _valid_tree()
    for node in tree.nodes.values():
        node.pillar_tags = []
    violations = principles.check_p8_cross_cutting_coverage(tree)
    assert {v.principle_id for v in violations} == {"P8"}
    assert len(violations) == len(principles.WELL_ARCHITECTED_PILLARS)


def test_p8_passes_when_all_pillars_covered_anywhere_in_tree():
    assert principles.check_p8_cross_cutting_coverage(_valid_tree()) == []


def test_p8_does_not_require_per_layer_coverage():
    # a1 alone only carries 2 of the 5 tags -- still fine, P8 is tree-wide, not per-node/layer.
    tree = _valid_tree()
    assert set(tree.nodes["a1"].pillar_tags) != set(principles.WELL_ARCHITECTED_PILLARS)
    assert principles.check_p8_cross_cutting_coverage(tree) == []


# ---------- Unit tests: reference-architecture conformance (TDSP + C4) ----------


def test_refarch_flags_layer_with_no_checklist_entry():
    tree = _valid_tree()
    checklist = DomainChecklist(domain=TEST_DOMAIN, derived_from="tdsp", mandatory_layers=[])
    violations = principles.check_reference_architecture_conformance(tree, checklist)
    assert any(v.principle_id == "RefArch" for v in violations)


def test_refarch_flags_invalid_tdsp_stage():
    tree = _valid_tree()
    checklist = DomainChecklist(domain=TEST_DOMAIN, derived_from="tdsp", mandatory_layers=[
        LayerChecklistEntry(layer="Ingestion", tdsp_stage="not_a_real_stage", cross_cutting=False),
    ])
    violations = principles.check_reference_architecture_conformance(tree, checklist)
    assert any(v.principle_id == "RefArch" for v in violations)


def test_refarch_passes_cross_cutting_layer_without_tdsp_stage():
    tree = _valid_tree()
    checklist = DomainChecklist(domain=TEST_DOMAIN, derived_from="tdsp", mandatory_layers=[
        LayerChecklistEntry(layer="Ingestion", tdsp_stage=None, cross_cutting=True),
    ])
    assert principles.check_reference_architecture_conformance(tree, checklist) == []


def test_refarch_passes_valid_tdsp_mapping():
    assert principles.check_reference_architecture_conformance(_valid_tree(), _checklist("Ingestion")) == []


def test_c4_flags_invalid_nesting_level():
    tree = _valid_tree()
    tree.nodes["a1"].level = "Weird Level"
    violations = principles.check_reference_architecture_conformance(tree, _checklist("Ingestion"))
    assert any(v.principle_id == "C4" for v in violations)


# ---------- Unit tests: Validator (3 categories together) ----------


def test_validate_tree_passes_clean_tree_against_matching_checklist():
    result = validate_tree(_valid_tree(), _checklist("Ingestion"))
    assert result.passed
    assert result.violations == []


def test_validate_tree_fails_and_reports_every_category():
    tree = _valid_tree()
    tree.nodes["a1"].label = "Read and parse via OpenAI"  # P1 criterion 1 + P6
    checklist = _checklist("Retrieval")  # P7 (Ingestion missing) + RefArch (layer has no entry)
    result = validate_tree(tree, checklist)
    assert not result.passed
    ids = {v.principle_id for v in result.violations}
    assert {"P1", "P6", "P7", "RefArch"}.issubset(ids)


# ---------- Unit tests: taxonomy repository (file-based round trip) ----------


def test_taxonomy_repository_round_trips_tree_and_checklist():
    tree = _valid_tree()
    checklist = _checklist("Ingestion")
    try:
        taxonomy_repo.save_tree(tree)
        taxonomy_repo.save_checklist(checklist)

        assert TEST_DOMAIN in taxonomy_repo.list_domains()
        loaded_tree = taxonomy_repo.load_tree(TEST_DOMAIN)
        loaded_checklist = taxonomy_repo.load_checklist(TEST_DOMAIN)
        assert loaded_tree.domain == TEST_DOMAIN
        assert loaded_tree.nodes["a2"].requires == ["a1"]
        assert loaded_checklist.derived_from == "tdsp"
        assert [e.layer for e in loaded_checklist.mandatory_layers] == ["Ingestion"]
    finally:
        tree_path = taxonomy_repo._TAXONOMIES_DIR / f"{TEST_DOMAIN}.json"
        checklist_path = taxonomy_repo._CHECKLISTS_DIR / f"{TEST_DOMAIN}.json"
        tree_path.unlink(missing_ok=True)
        checklist_path.unlink(missing_ok=True)


def test_taxonomy_repository_returns_none_for_unknown_domain():
    assert taxonomy_repo.load_tree("__definitely_not_a_real_domain__") is None
    assert taxonomy_repo.load_checklist("__definitely_not_a_real_domain__") is None


# ---------- Unit tests: Intent Parser ----------


def test_parse_intent_rule_based_match(monkeypatch):
    monkeypatch.setattr(intent_service.taxonomy_repo, "list_domains", lambda: ["rag", "etl"])
    result = intent_service.parse_intent("I want to develop a RAG pipeline for support docs")
    assert result.domain == "rag"
    assert result.confidence >= 0.6
    assert result.tree_available is True


def test_parse_intent_falls_back_to_llm_when_no_rule_match(monkeypatch):
    monkeypatch.setattr(intent_service.taxonomy_repo, "list_domains", lambda: ["rag"])
    monkeypatch.setattr(
        intent_service, "_ask_json",
        lambda system, prompt, max_tokens=300: {
            "domain": "chatbot", "confidence": 0.8, "extracted_constraints": {"latency": "low"}
        },
    )
    result = intent_service.parse_intent("Build me something that talks to customers")
    assert result.domain == "chatbot"
    assert result.confidence == 0.8
    assert result.extracted_constraints == {"latency": "low"}
    assert result.tree_available is False


# ---------- Unit tests: Decomposition Engine -- Stage 0/1 (deterministic) ----------


def test_instantiate_layers_creates_one_node_per_checklist_entry_in_order():
    checklist = _checklist("Ingestion", "Preprocessing", "Embedding")
    tree = decompose_engine.instantiate_layers(TEST_DOMAIN, checklist)
    labels_in_order = [tree.nodes[nid].label for nid in tree.root_ids]
    assert labels_in_order == ["Ingestion", "Preprocessing", "Embedding"]
    assert all(tree.nodes[nid].level == "Layer" for nid in tree.root_ids)
    assert all(tree.nodes[nid].children == [] for nid in tree.root_ids)  # not decomposed yet


# ---------- Unit tests: Decomposition Engine -- Stage 3 Atomicity splitting ----------


def test_generate_and_test_atomic_steps_splits_a_failing_candidate(monkeypatch):
    entry = LayerChecklistEntry(layer="Ingestion", tdsp_stage="data_acquisition_ingestion",
                                 input_contract=["source_config"], output_contract=["chunks"])
    bad_candidate = {"label": "Fetch and chunk the document", "consumes": "source_config",
                      "produces": "chunks", "requires": [], "terminal_output": True,
                      "variables": [], "pillar_tags": [], "notes": ""}
    split_pieces = [
        {"label": "Fetch the document", "consumes": "source_config", "produces": "raw_document",
         "requires": [], "terminal_output": False, "variables": [], "pillar_tags": [], "notes": ""},
        {"label": "Chunk the document", "consumes": "raw_document", "produces": "chunks",
         "requires": ["Fetch the document"], "terminal_output": True, "variables": [], "pillar_tags": [], "notes": ""},
    ]
    mock = _stage_router(stage3={"atomic_steps": [bad_candidate]}, split={"atomic_steps": split_pieces})
    monkeypatch.setattr(decompose_engine, "_ask_json", mock)

    result = decompose_engine._generate_and_test_atomic_steps(entry, "Load", [], "context")
    assert [c["label"] for c in result] == ["Fetch the document", "Chunk the document"]


def test_split_step_response_preserves_rules_per_piece(monkeypatch):
    entry = LayerChecklistEntry(layer="Ingestion", tdsp_stage="data_acquisition_ingestion",
                                 input_contract=["source_config"], output_contract=["chunks"])
    bad_candidate = {"label": "Fetch and chunk the document", "consumes": "source_config",
                      "produces": "chunks", "requires": [], "terminal_output": True,
                      "variables": [], "pillar_tags": [], "rules": ["max file size: 50MB"], "notes": ""}
    split_pieces = [
        {"label": "Fetch the document", "consumes": "source_config", "produces": "raw_document",
         "requires": [], "terminal_output": False, "variables": [], "pillar_tags": [],
         "rules": ["max file size: 50MB"], "notes": ""},
        {"label": "Chunk the document", "consumes": "raw_document", "produces": "chunks",
         "requires": ["Fetch the document"], "terminal_output": True, "variables": [],
         "pillar_tags": [], "rules": [], "notes": ""},
    ]
    mock = _stage_router(stage3={"atomic_steps": [bad_candidate]}, split={"atomic_steps": split_pieces})
    monkeypatch.setattr(decompose_engine, "_ask_json", mock)

    result = decompose_engine._generate_and_test_atomic_steps(entry, "Load", [], "context")
    assert result[0]["rules"] == ["max file size: 50MB"]
    assert result[1]["rules"] == []


def test_generate_and_test_atomic_steps_accepts_clean_candidate_without_splitting(monkeypatch):
    entry = LayerChecklistEntry(layer="Ingestion", tdsp_stage="data_acquisition_ingestion")
    clean_candidate = {"label": "Fetch the document", "consumes": "source_config",
                        "produces": "raw_document", "requires": [], "terminal_output": False,
                        "variables": [], "pillar_tags": [], "notes": ""}

    def _mock(system, prompt, max_tokens=1500):
        if "Atomicity correction" in system:
            raise AssertionError("should not need to split a clean candidate")
        return {"atomic_steps": [clean_candidate]}

    monkeypatch.setattr(decompose_engine, "_ask_json", _mock)
    result = decompose_engine._generate_and_test_atomic_steps(entry, "Load", [], "context")
    assert result == [clean_candidate]


# ---------- Unit tests: Decomposition Engine -- full propose_tree orchestration ----------


def test_propose_tree_runs_all_stages_and_produces_a_valid_tree(monkeypatch):
    stage2 = {"branches": [{"branch_label": None, "sub_tasks": [{"label": "Load and chunk"}]}]}
    stage3 = {"atomic_steps": [
        {"label": "Read source file", "consumes": "source_config", "produces": "raw_text",
         "requires": [], "terminal_output": False, "variables": [], "pillar_tags": _PILLARS_A,
         "rules": ["accepted formats: pdf, docx, txt"], "notes": ""},
        {"label": "Split text into chunks", "consumes": "raw_text", "requires": ["Read source file"],
         "produces": "chunks", "terminal_output": True,
         "variables": [{"name": "chunk_size", "default": "500", "description": ""}],
         "pillar_tags": _PILLARS_B, "rules": [], "notes": ""},
    ]}
    monkeypatch.setattr(decompose_engine, "_ask_json", _stage_router(stage2=stage2, stage3=stage3))
    checklist = _checklist("Ingestion")

    tree = decompose_engine.propose_tree(TEST_DOMAIN, "a RAG pipeline", checklist)
    assert tree.domain == TEST_DOMAIN
    atomic_steps = [n for n in tree.nodes.values() if n.level == "Atomic step"]
    assert len(atomic_steps) == 2
    chunker = next(n for n in atomic_steps if n.label == "Split text into chunks")
    reader = next(n for n in atomic_steps if n.label == "Read source file")
    assert chunker.requires == [reader.id]
    # rules[] round-trips from Stage 3's response into the frozen tree (Fix B); an empty
    # list on another step is not itself flagged (never forced non-empty).
    assert reader.rules == ["accepted formats: pdf, docx, txt"]
    assert chunker.rules == []
    # Stage 4 grounded variables in the real n8n schema too, not just Stage 3's own list.
    assert any(v.name == "chunk_size" for v in reader.variables) or any(v.name == "chunk_size" for v in chunker.variables)
    result = validate_tree(tree, checklist)
    assert result.passed


def test_propose_tree_retries_the_whole_pipeline_on_validation_failure(monkeypatch):
    stage2 = {"branches": [{"branch_label": None, "sub_tasks": [{"label": "Load"}]}]}
    calls = {"stage3": 0}
    bad_step = {"label": "Read source file", "consumes": "source_config", "produces": "raw_text",
                "requires": [], "terminal_output": False,  # P5 orphan: nothing consumes raw_text
                "variables": [], "pillar_tags": _PILLARS_A + _PILLARS_B, "notes": ""}
    good_step = {**bad_step, "terminal_output": True}  # now a legitimate dead end, P5 satisfied

    def _mock(system, prompt, max_tokens=1500):
        if "Stage 2" in system:
            return stage2
        if "Stage 3" in system:
            calls["stage3"] += 1
            return {"atomic_steps": [bad_step if calls["stage3"] == 1 else good_step]}
        raise AssertionError("should not need Atomicity correction for this candidate")

    monkeypatch.setattr(decompose_engine, "_ask_json", _mock)
    checklist = _checklist("Ingestion")
    tree = decompose_engine.propose_tree(TEST_DOMAIN, "a RAG pipeline", checklist)
    assert calls["stage3"] == 2
    assert validate_tree(tree, checklist).passed


# ---------- Unit tests: layer repetition (spec addendum Fix C) ----------


def test_generate_subtasks_for_layer_defaults_to_one_branch_when_ai_omits_branches(monkeypatch):
    entry = LayerChecklistEntry(layer="Ingestion", tdsp_stage="data_acquisition_ingestion")
    monkeypatch.setattr(decompose_engine, "_ask_json", lambda system, prompt, max_tokens=500: {})
    branches = decompose_engine._generate_subtasks_for_layer(entry, "context")
    assert branches == [{"branch_label": None, "sub_tasks": []}]


def test_multi_branch_stage2_creates_two_same_labeled_layer_nodes(monkeypatch):
    stage2 = {"branches": [
        {"branch_label": None, "sub_tasks": [{"label": "Handle PDFs"}]},
        {"branch_label": "Web-sourced documents", "sub_tasks": [{"label": "Handle web pages"}]},
    ]}
    stage3 = {"atomic_steps": [{
        "label": "Pull rows", "consumes": "source_config", "produces": "rows", "requires": [],
        "terminal_output": True, "variables": [], "pillar_tags": _PILLARS_A + _PILLARS_B,
        "rules": [], "notes": "",
    }]}
    monkeypatch.setattr(decompose_engine, "_ask_json", _stage_router(stage2=stage2, stage3=stage3))
    checklist = _checklist("Ingestion")

    tree = decompose_engine.propose_tree(TEST_DOMAIN, "a RAG pipeline with two sources", checklist)

    layer_nodes = [tree.nodes[nid] for nid in tree.root_ids]
    assert len(layer_nodes) == 2
    assert all(n.label == "Ingestion" for n in layer_nodes)
    # branch 0 has no distinguishing note; branch 1 carries the branch_label via notes.
    notes = sorted(n.notes for n in layer_nodes)
    assert notes == ["", "Web-sourced documents"]
    # Both branches got their own real sub-task/atomic-step content, not a shared/empty one.
    assert all(n.children for n in layer_nodes)

    result = validate_tree(tree, checklist)
    assert result.passed


def test_propose_checklist(monkeypatch):
    monkeypatch.setattr(
        decompose_engine, "_ask_json",
        lambda system, prompt, max_tokens=1500: {
            "derived_from": "tdsp",
            "mandatory_layers": [
                {"layer": "Extract", "tdsp_stage": "data_acquisition_ingestion", "cross_cutting": False,
                 "input_contract": [], "output_contract": ["raw_rows"]},
                {"layer": "Transform", "tdsp_stage": "data_preprocessing", "cross_cutting": False,
                 "input_contract": ["raw_rows"], "output_contract": ["clean_rows"]},
                {"layer": "Load", "tdsp_stage": "deployment", "cross_cutting": False,
                 "input_contract": ["clean_rows"], "output_contract": ["loaded_table"]},
            ],
        },
    )
    checklist = decompose_engine.propose_checklist(TEST_DOMAIN, "an ETL pipeline")
    assert checklist.domain == TEST_DOMAIN
    assert checklist.derived_from == "tdsp"
    assert [e.layer for e in checklist.mandatory_layers] == ["Extract", "Transform", "Load"]
    assert checklist.mandatory_layers[0].tdsp_stage == "data_acquisition_ingestion"


# ---------- Unit tests: Stage 4 (Variable Exhaustion, grounded in the Node Mapper schema) ----------


def test_exhaust_variables_adds_matched_schemas_own_default_parameters():
    tree = _valid_tree()
    tree.nodes["a1"].label = "Call retrieval API"  # matches n8n-nodes-base.httpRequest
    tree.nodes["a1"].variables = []
    decompose_engine.exhaust_variables(tree)
    names = {v.name for v in tree.nodes["a1"].variables}
    assert "method" in names and "url" in names  # HTTP Request's own default_parameters


def test_exhaust_variables_never_overwrites_an_already_declared_variable():
    tree = _valid_tree()
    tree.nodes["a1"].label = "Call retrieval API"
    tree.nodes["a1"].variables = [Variable(name="method", default="POST", description="already set")]
    decompose_engine.exhaust_variables(tree)
    method_vars = [v for v in tree.nodes["a1"].variables if v.name == "method"]
    assert len(method_vars) == 1
    assert method_vars[0].default == "POST"


# ---------- Unit tests: Python Renderer ----------


def test_render_python_orders_by_dependency():
    tree = _valid_tree()
    blocks = render_python(tree)
    assert [b.label for b in blocks] == ["Read source file", "Split text into chunks"]
    assert "def read_source_file()" in blocks[0].code
    assert "chunk_size=500" in blocks[1].code  # numeric default, not quoted
    assert "return chunks" in blocks[1].code


def test_render_python_puts_no_default_args_before_defaulted_ones():
    # Python syntax requires this ordering -- a real bug found live: the tree's own
    # variable order isn't guaranteed to already satisfy it.
    tree = _valid_tree()
    tree.nodes["a1"].variables = [
        Variable(name="batch_size", default="100"),
        Variable(name="access_credentials", default=None),
    ]
    blocks = render_python(tree)
    block = next(b for b in blocks if b.step_id == "a1")
    signature = block.code.splitlines()[0]
    assert signature.index("access_credentials") < signature.index("batch_size")


def test_render_python_handles_no_dependencies():
    tree = _valid_tree()
    tree.nodes["a2"].requires = []
    blocks = render_python(tree)
    assert len(blocks) == 2  # order among independent steps is deterministic (stable by id)


# ---------- API endpoint tests ----------


def test_intent_endpoint_requires_auth():
    client = TestClient(app)
    response = client.post("/api/decompose/intent", json={"text": "build a RAG"})
    assert response.status_code == 401


def test_intent_endpoint_rejects_empty_text(authed_client):
    response = authed_client.post("/api/decompose/intent", json={"text": "   "})
    assert response.status_code == 400


def test_intent_endpoint_returns_result(authed_client, monkeypatch):
    monkeypatch.setattr(
        "backend.api.parse_intent",
        lambda text: IntentResult(domain="rag", confidence=0.9, tree_available=True),
    )
    response = authed_client.post("/api/decompose/intent", json={"text": "build a RAG system"})
    assert response.status_code == 200
    assert response.json()["domain"] == "rag"


def test_domains_endpoint_lists_known_domains(authed_client):
    response = authed_client.get("/api/decompose/domains")
    assert response.status_code == 200
    assert "rag" in response.json()


def test_get_domain_tree_404_for_unknown_domain(authed_client):
    response = authed_client.get("/api/decompose/domains/__definitely_not_a_real_domain__/tree")
    assert response.status_code == 404


def test_draft_and_approve_domain_end_to_end(authed_client, monkeypatch):
    stage2 = {"branches": [{"branch_label": None, "sub_tasks": [{"label": "Pull rows"}]}]}
    stage3 = {"atomic_steps": [{
        "label": "Query source table", "consumes": "source_config", "produces": "rows",
        "requires": [], "terminal_output": True, "variables": [],
        "pillar_tags": _PILLARS_A + _PILLARS_B, "notes": "",
    }]}
    monkeypatch.setattr(
        "backend.api.propose_checklist",
        lambda domain, ctx: DomainChecklist(domain=domain, derived_from="tdsp", mandatory_layers=[
            LayerChecklistEntry(layer="Extract", tdsp_stage="data_acquisition_ingestion",
                                 input_contract=["source_config"], output_contract=["rows"]),
        ]),
    )
    monkeypatch.setattr(decompose_engine, "_ask_json", _stage_router(stage2=stage2, stage3=stage3))

    try:
        draft_response = authed_client.post(
            f"/api/decompose/domains/{TEST_DOMAIN}/draft", json={"reasoning_context": "a small ETL job"}
        )
        assert draft_response.status_code == 200
        draft = draft_response.json()
        assert draft["validation"]["passed"] is True

        approve_response = authed_client.post(
            f"/api/decompose/domains/{TEST_DOMAIN}/approve",
            json={"checklist": draft["checklist"], "tree": draft["tree"]},
        )
        assert approve_response.status_code == 201
        assert TEST_DOMAIN in taxonomy_repo.list_domains()

        render_response = authed_client.post("/api/decompose/render/python", json={"domain": TEST_DOMAIN})
        assert render_response.status_code == 200
        assert len(render_response.json()) == 1
    finally:
        tree_path = taxonomy_repo._TAXONOMIES_DIR / f"{TEST_DOMAIN}.json"
        checklist_path = taxonomy_repo._CHECKLISTS_DIR / f"{TEST_DOMAIN}.json"
        tree_path.unlink(missing_ok=True)
        checklist_path.unlink(missing_ok=True)


def test_render_python_endpoint_404_for_unknown_domain(authed_client):
    response = authed_client.post("/api/decompose/render/python", json={"domain": "__definitely_not_a_real_domain__"})
    assert response.status_code == 404


# ---------- Unit tests: Node Mapper + JSON Exporter ----------


def test_map_tree_matches_known_keywords_to_real_node_types():
    tree = _valid_tree()
    tree.nodes["a1"].label = "Call retrieval API"  # should match HTTP Request
    tree.nodes["a2"].label = "Store chunks in database"  # should match Postgres
    nodes, connections = node_mapper.map_tree(tree)
    by_step = {n.step_id: n for n in nodes}
    assert by_step["a1"].type == "n8n-nodes-base.httpRequest"
    assert by_step["a2"].type == "n8n-nodes-base.postgres"


def test_map_tree_falls_back_to_code_node_for_unmatched_step():
    tree = _valid_tree()
    tree.nodes["a1"].label = "Frobnicate the widget"  # matches no known keyword
    nodes, _ = node_mapper.map_tree(tree)
    node = next(n for n in nodes if n.step_id == "a1")
    assert node.type == "n8n-nodes-base.code"
    assert "Frobnicate the widget" in node.parameters["jsCode"]


def test_map_tree_never_drops_a_declared_variable_on_fallback():
    tree = _valid_tree()
    tree.nodes["a1"].label = "Frobnicate the widget"
    tree.nodes["a1"].variables = [Variable(name="widget_id", default="42", description="which widget")]
    nodes, _ = node_mapper.map_tree(tree)
    node = next(n for n in nodes if n.step_id == "a1")
    assert "widget_id" in node.parameters["jsCode"]


def test_map_tree_produces_connection_from_dependency_to_dependent():
    nodes, connections = node_mapper.map_tree(_valid_tree())
    by_step = {n.step_id: n for n in nodes}
    source_name = by_step["a1"].name
    target_name = by_step["a2"].name
    assert connections[source_name]["main"][0][0]["node"] == target_name


def test_map_tree_disambiguates_duplicate_labels():
    tree = _valid_tree()
    tree.nodes["a2"].label = tree.nodes["a1"].label  # force a name collision
    nodes, _ = node_mapper.map_tree(tree)
    names = [n.name for n in nodes]
    assert len(names) == len(set(names))  # every name still unique on the canvas


def test_export_workflow_wraps_mapped_nodes_and_connections():
    workflow = export_workflow(_valid_tree())
    assert workflow.name == TEST_DOMAIN
    assert len(workflow.nodes) == 2
    assert workflow.connections  # non-empty, a1 -> a2


def test_render_n8n_endpoint_404_for_unknown_domain(authed_client):
    response = authed_client.post("/api/decompose/render/n8n", json={"domain": "__definitely_not_a_real_domain__"})
    assert response.status_code == 404


def test_render_n8n_endpoint_returns_importable_shape(authed_client):
    response = authed_client.post("/api/decompose/render/n8n", json={"domain": "rag"})
    assert response.status_code == 200
    body = response.json()
    assert "nodes" in body and "connections" in body
    assert len(body["nodes"]) > 0
    for node in body["nodes"]:
        assert node["type"].startswith("n8n-nodes-base.")


# ---------- Unit + endpoint tests: refine_tree (AMENDMENT 4 item 6) ----------


def test_refine_tree_preserves_untouched_node_ids_and_adds_new_one(monkeypatch):
    original = _valid_tree()
    refined_dump = original.model_dump()
    refined_dump["nodes"]["a3"] = {
        "id": "a3", "label": "Count chunks", "level": "Atomic step", "parent_id": "s1",
        "children": [], "requires": ["a2"], "consumes": "chunks", "produces": "chunk_count",
        "terminal_output": True, "variables": [], "pillar_tags": [], "notes": "",
    }
    refined_dump["nodes"]["s1"]["children"] = ["a1", "a2", "a3"]
    monkeypatch.setattr(decompose_engine, "_ask_json", lambda system, prompt, max_tokens=16000: refined_dump)

    refined = decompose_engine.refine_tree(original, "add a step that counts the chunks")

    assert set(refined.nodes) == {"l1", "s1", "a1", "a2", "a3"}
    assert refined.nodes["a1"] == original.nodes["a1"]  # untouched, byte-identical
    assert refined.nodes["a3"].label == "Count chunks"
    assert refined.nodes["s1"].children == ["a1", "a2", "a3"]


def test_refine_tree_malformed_response_raises_reasoning_stage_error(monkeypatch):
    monkeypatch.setattr(decompose_engine, "_ask_json", lambda system, prompt, max_tokens=16000: {"not": "a tree"})
    with pytest.raises(ReasoningStageError):
        decompose_engine.refine_tree(_valid_tree(), "do something")


def test_refine_domain_endpoint_requires_auth():
    client = TestClient(app)
    response = client.post(f"/api/decompose/domains/{TEST_DOMAIN}/refine", json={"instruction": "x"})
    assert response.status_code == 401


def test_refine_domain_endpoint_404_for_unknown_domain(authed_client):
    response = authed_client.post(
        "/api/decompose/domains/__definitely_not_a_real_domain__/refine", json={"instruction": "x"}
    )
    assert response.status_code == 404


def test_refine_domain_endpoint_400_for_empty_instruction(authed_client):
    try:
        taxonomy_repo.save_tree(_valid_tree())
        taxonomy_repo.save_checklist(_checklist("Ingestion"))
        response = authed_client.post(f"/api/decompose/domains/{TEST_DOMAIN}/refine", json={"instruction": "   "})
        assert response.status_code == 400
    finally:
        taxonomy_repo._TAXONOMIES_DIR.joinpath(f"{TEST_DOMAIN}.json").unlink(missing_ok=True)
        taxonomy_repo._CHECKLISTS_DIR.joinpath(f"{TEST_DOMAIN}.json").unlink(missing_ok=True)


def test_refine_domain_endpoint_auto_freezes_on_pass(authed_client, monkeypatch):
    tree = _valid_tree()
    try:
        taxonomy_repo.save_tree(tree)
        taxonomy_repo.save_checklist(_checklist("Ingestion"))
        monkeypatch.setattr("backend.api.refine_tree", lambda current_tree, instruction: current_tree)

        response = authed_client.post(
            f"/api/decompose/domains/{TEST_DOMAIN}/refine", json={"instruction": "no-op refine"}
        )
        assert response.status_code == 200
        assert response.json()["validation"]["passed"] is True

        reloaded = taxonomy_repo.load_tree(TEST_DOMAIN)
        assert set(reloaded.nodes) == set(tree.nodes)  # re-saved (still) correctly
    finally:
        taxonomy_repo._TAXONOMIES_DIR.joinpath(f"{TEST_DOMAIN}.json").unlink(missing_ok=True)
        taxonomy_repo._CHECKLISTS_DIR.joinpath(f"{TEST_DOMAIN}.json").unlink(missing_ok=True)


def test_refine_domain_endpoint_does_not_save_on_validation_failure(authed_client, monkeypatch):
    tree = _valid_tree()
    try:
        taxonomy_repo.save_tree(tree)
        taxonomy_repo.save_checklist(_checklist("Ingestion"))
        broken_tree = _valid_tree()
        broken_tree.nodes["a2"].produces = None  # fails Atomicity criterion 3 / P4
        monkeypatch.setattr("backend.api.refine_tree", lambda current_tree, instruction: broken_tree)

        response = authed_client.post(
            f"/api/decompose/domains/{TEST_DOMAIN}/refine", json={"instruction": "break it"}
        )
        assert response.status_code == 200
        assert response.json()["validation"]["passed"] is False

        reloaded = taxonomy_repo.load_tree(TEST_DOMAIN)
        assert reloaded.nodes["a2"].produces == "chunks"  # untouched -- the broken tree was never written
    finally:
        taxonomy_repo._TAXONOMIES_DIR.joinpath(f"{TEST_DOMAIN}.json").unlink(missing_ok=True)
        taxonomy_repo._CHECKLISTS_DIR.joinpath(f"{TEST_DOMAIN}.json").unlink(missing_ok=True)


# ---------- Settings endpoint tests (AMENDMENT 4 item 7) ----------


def test_settings_principles_requires_auth():
    client = TestClient(app)
    response = client.get("/api/decompose/settings/principles")
    assert response.status_code == 401


def test_settings_principles_get_returns_real_p1_to_p7(authed_client):
    # rules/decomposition_principles.json documents P1-P7 only -- P8 (Cross-Cutting
    # Coverage) was added later as enforcement code (validator/principles.py) without a
    # matching citation entry here; this test reflects that actual, current file content.
    response = authed_client.get("/api/decompose/settings/principles")
    assert response.status_code == 200
    ids = {p["id"] for p in response.json()["principles"]}
    assert ids == {"P1", "P2", "P3", "P4", "P5", "P6", "P7"}


def test_settings_principles_put_round_trips_and_is_restored(authed_client):
    original = taxonomy_repo.load_principles_raw()
    try:
        modified = {"principles": [{"id": "P1", "name": "Test", "description": "x", "severity": "Reject"}]}
        put_response = authed_client.put("/api/decompose/settings/principles", json=modified)
        assert put_response.status_code == 200
        get_response = authed_client.get("/api/decompose/settings/principles")
        assert get_response.json() == modified
    finally:
        authed_client.put("/api/decompose/settings/principles", json=original)
        assert taxonomy_repo.load_principles_raw() == original


def test_settings_reference_architectures_lists_real_files(authed_client):
    response = authed_client.get("/api/decompose/settings/reference-architectures")
    assert response.status_code == 200
    assert set(response.json()) == {"tdsp", "c4_model", "well_architected", "solid"}


def test_settings_reference_architecture_get_404_for_unknown_name(authed_client):
    response = authed_client.get("/api/decompose/settings/reference-architectures/__not_real__")
    assert response.status_code == 404


def test_settings_reference_architecture_put_and_get_round_trip(authed_client):
    name = "__wp_decompose_test_ref_arch__"
    try:
        body = {"stages": [{"id": "x", "name": "X"}]}
        put_response = authed_client.put(f"/api/decompose/settings/reference-architectures/{name}", json=body)
        assert put_response.status_code == 200
        get_response = authed_client.get(f"/api/decompose/settings/reference-architectures/{name}")
        assert get_response.json() == body
        assert name in authed_client.get("/api/decompose/settings/reference-architectures").json()
    finally:
        taxonomy_repo._REFERENCE_ARCHITECTURES_DIR.joinpath(f"{name}.json").unlink(missing_ok=True)


def test_settings_checklists_lists_domains_including_rag(authed_client):
    response = authed_client.get("/api/decompose/settings/checklists")
    assert response.status_code == 200
    assert "rag" in response.json()


def test_settings_checklist_get_404_for_unknown_domain(authed_client):
    response = authed_client.get("/api/decompose/settings/checklists/__not_real__")
    assert response.status_code == 404


def test_settings_checklist_put_and_get_round_trip(authed_client):
    try:
        body = {"domain": TEST_DOMAIN, "derived_from": "tdsp", "mandatory_layers": []}
        put_response = authed_client.put(f"/api/decompose/settings/checklists/{TEST_DOMAIN}", json=body)
        assert put_response.status_code == 200
        get_response = authed_client.get(f"/api/decompose/settings/checklists/{TEST_DOMAIN}")
        assert get_response.json() == body
    finally:
        taxonomy_repo._CHECKLISTS_DIR.joinpath(f"{TEST_DOMAIN}.json").unlink(missing_ok=True)
