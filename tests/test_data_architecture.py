"""Data Architecture Layer (Module 13) tests. See docs/ARCHITEQ-Data-Architecture-Layer-Spec.md
and ARCHITEQ-PRD.md R41-R50. AI calls are mocked throughout, matching this project's own
established convention (tests/test_engineering_decomposition.py's own docstring)."""

from backend.data_architecture import engine as data_architecture_engine
from backend.data_architecture import repository as data_architecture_repo
from backend.models import (
    DataAnchor,
    DataArchitecture,
    DataAttribute,
    DataEntity,
    DataRelationship,
    DomainTaskTree,
    TaskTreeNode,
)


def _atomic(id_, label, *, consumes=None, produces=None, notes=""):
    return TaskTreeNode(id=id_, label=label, level="Atomic step", consumes=consumes, produces=produces, notes=notes)

TEST_DOMAIN = "__wp_data_architecture_test__"


def _sample_architecture() -> DataArchitecture:
    return DataArchitecture(
        domain=TEST_DOMAIN,
        entities=[
            DataEntity(
                id="D01", name="documents", domain=TEST_DOMAIN,
                attributes=[
                    DataAttribute(name="id", type="UUID", is_primary_key=True, nullable=False),
                    DataAttribute(name="filename", type="TEXT", nullable=False),
                ],
            ),
            DataEntity(
                id="D02", name="document_chunks", domain=TEST_DOMAIN,
                attributes=[
                    DataAttribute(name="id", type="UUID", is_primary_key=True, nullable=False),
                    DataAttribute(
                        name="document_id", type="UUID", is_foreign_key=True,
                        references_entity="D01", nullable=False,
                    ),
                ],
            ),
        ],
        relationships=[DataRelationship(from_entity="D01", to_entity="D02", cardinality="1:N")],
        anchors=[
            DataAnchor(domain=TEST_DOMAIN, node_id="a1", node_label="Extract Text Content", data_id="D01", operation="WRITE"),
            DataAnchor(domain=TEST_DOMAIN, node_id="a2", node_label="Split Text Into Chunks", data_id="D02", operation="WRITE"),
        ],
    )


def test_data_architecture_round_trips_through_save_and_load():
    tree = _sample_architecture()
    try:
        data_architecture_repo.save_data_architecture(tree)
        loaded = data_architecture_repo.load_data_architecture(TEST_DOMAIN)
        assert loaded == tree
    finally:
        data_architecture_repo._DATA_ARCHITECTURES_DIR.joinpath(f"{TEST_DOMAIN}.json").unlink(missing_ok=True)


def test_load_data_architecture_returns_none_for_unknown_domain():
    assert data_architecture_repo.load_data_architecture("__definitely_not_a_real_domain__") is None


# ---- Stage 5, Persistence Classification (13b) ----

def test_classify_atomic_step_operation_returns_real_operation(monkeypatch):
    monkeypatch.setattr(data_architecture_engine, "_ask_json", lambda **kwargs: {"operation": "WRITE"})
    step = _atomic("a1", "Store chunk in database")
    assert data_architecture_engine.classify_atomic_step_operation(step, "context") == "WRITE"


def test_classify_atomic_step_operation_transient_returns_none(monkeypatch):
    monkeypatch.setattr(data_architecture_engine, "_ask_json", lambda **kwargs: {"operation": "TRANSIENT"})
    step = _atomic("a1", "Normalize whitespace in text")
    assert data_architecture_engine.classify_atomic_step_operation(step, "context") is None


def test_classify_atomic_step_operation_rejects_invalid_value(monkeypatch):
    monkeypatch.setattr(data_architecture_engine, "_ask_json", lambda **kwargs: {"operation": "GARBAGE"})
    step = _atomic("a1", "Some step")
    assert data_architecture_engine.classify_atomic_step_operation(step, "context") is None


# ---- Stage 6, Entity Derivation (13b) ----

def test_derive_data_entities_deduplicates_same_real_entity(monkeypatch):
    mock_response = {
        "entities": [
            {"name": "document_chunks", "description": "Chunked document text", "attributes": [
                {"name": "id", "type": "UUID", "is_primary_key": True, "is_foreign_key": False, "references_entity_name": None, "nullable": False},
            ]},
        ],
        "step_entity_map": {"a1": "document_chunks", "a2": "document_chunks"},
    }
    monkeypatch.setattr(data_architecture_engine, "_ask_json", lambda **kwargs: mock_response)

    steps = [
        (_atomic("a1", "Split Text Into Chunks", produces="chunks"), "WRITE"),
        (_atomic("a2", "Attach Chunk Metadata", consumes="chunks"), "UPDATE"),
    ]
    entities, anchors, relationships = data_architecture_engine.derive_data_entities("rag", steps, "context")

    assert len(entities) == 1
    assert entities[0].name == "document_chunks"
    assert len(anchors) == 2
    assert {a.node_id: a.operation for a in anchors} == {"a1": "WRITE", "a2": "UPDATE"}
    assert all(a.data_id == entities[0].id for a in anchors)
    assert relationships == []


def test_derive_data_entities_resolves_real_foreign_key_relationship(monkeypatch):
    mock_response = {
        "entities": [
            {"name": "documents", "description": "", "attributes": [
                {"name": "id", "type": "UUID", "is_primary_key": True, "is_foreign_key": False, "references_entity_name": None, "nullable": False},
            ]},
            {"name": "document_chunks", "description": "", "attributes": [
                {"name": "id", "type": "UUID", "is_primary_key": True, "is_foreign_key": False, "references_entity_name": None, "nullable": False},
                {"name": "document_id", "type": "UUID", "is_primary_key": False, "is_foreign_key": True, "references_entity_name": "documents", "nullable": False},
            ]},
        ],
        "step_entity_map": {"a1": "documents", "a2": "document_chunks"},
    }
    monkeypatch.setattr(data_architecture_engine, "_ask_json", lambda **kwargs: mock_response)

    steps = [
        (_atomic("a1", "Store Document", produces="document"), "WRITE"),
        (_atomic("a2", "Split Text Into Chunks", consumes="document", produces="chunks"), "WRITE"),
    ]
    entities, anchors, relationships = data_architecture_engine.derive_data_entities("rag", steps, "context")

    by_name = {e.name: e for e in entities}
    assert by_name["documents"].id == "D01"
    assert by_name["document_chunks"].id == "D02"
    assert len(relationships) == 1
    assert relationships[0].from_entity == "D01"
    assert relationships[0].to_entity == "D02"
    assert relationships[0].cardinality == "1:N"


def test_derive_data_entities_empty_input_returns_empty_output():
    entities, anchors, relationships = data_architecture_engine.derive_data_entities("rag", [], "context")
    assert entities == [] and anchors == [] and relationships == []


# ---- SQL DDL Generator (13c) ----

def _fk_entity_pair():
    documents = DataEntity(
        id="D01", name="documents", domain=TEST_DOMAIN,
        attributes=[
            DataAttribute(name="doc_id", type="UUID", is_primary_key=True, nullable=False),
            DataAttribute(name="filename", type="TEXT", nullable=False),
        ],
    )
    chunks = DataEntity(
        id="D02", name="document_chunks", domain=TEST_DOMAIN,
        attributes=[
            DataAttribute(name="id", type="UUID", is_primary_key=True, nullable=False),
            DataAttribute(
                name="document_id", type="UUID", is_foreign_key=True,
                references_entity="D01", nullable=False,
            ),
            DataAttribute(name="metadata", type="JSONB"),
        ],
    )
    return documents, chunks


def test_render_sql_ddl_orders_referenced_table_first():
    documents, chunks = _fk_entity_pair()
    # Declared in "wrong" order (chunks before documents) -- output must still be correct.
    sql = data_architecture_engine.render_sql_ddl([chunks, documents])
    assert sql.index("CREATE TABLE documents") < sql.index("CREATE TABLE document_chunks")


def test_render_sql_ddl_uses_real_primary_key_name_not_hardcoded_id():
    documents, chunks = _fk_entity_pair()
    sql = data_architecture_engine.render_sql_ddl([documents, chunks])
    assert "REFERENCES documents(doc_id)" in sql


def test_render_sql_ddl_marks_pk_not_null_and_leaves_plain_columns_bare():
    documents, chunks = _fk_entity_pair()
    sql = data_architecture_engine.render_sql_ddl([documents, chunks])
    assert "doc_id UUID PRIMARY KEY" in sql
    assert "filename TEXT NOT NULL" in sql
    assert "metadata JSONB" in sql
    assert "metadata JSONB NOT NULL" not in sql
    assert "metadata JSONB PRIMARY KEY" not in sql


# ---- propose_data_architecture Orchestrator (13d) ----

def _workflow_tree_fixture() -> DomainTaskTree:
    return DomainTaskTree(domain="rag", root_ids=[], nodes={
        "a1": _atomic("a1", "Store Document", produces="document"),
        "a2": _atomic("a2", "Split Text Into Chunks", consumes="document", produces="chunks"),
        "a3": _atomic("a3", "Normalize Whitespace", consumes="chunks", produces="chunks"),
    })


def _data_architecture_stage_mock(**kwargs):
    system = kwargs.get("system", "")
    if "classifying one workflow Atomic step" in system:
        prompt = kwargs.get("prompt", "")
        if "Store Document" in prompt:
            return {"operation": "WRITE"}
        if "Split Text Into Chunks" in prompt:
            return {"operation": "WRITE"}
        return {"operation": "TRANSIENT"}  # Normalize Whitespace
    if "deriving the persistent data model" in system:
        return {
            "entities": [
                {"name": "documents", "description": "", "attributes": [
                    {"name": "id", "type": "UUID", "is_primary_key": True, "is_foreign_key": False, "references_entity_name": None, "nullable": False},
                ]},
                {"name": "document_chunks", "description": "", "attributes": [
                    {"name": "id", "type": "UUID", "is_primary_key": True, "is_foreign_key": False, "references_entity_name": None, "nullable": False},
                ]},
            ],
            "step_entity_map": {"a1": "documents", "a2": "document_chunks"},
        }
    raise AssertionError(f"unexpected system prompt: {system}")


def test_propose_data_architecture_happy_path(monkeypatch):
    tree = _workflow_tree_fixture()
    monkeypatch.setattr(data_architecture_engine, "_ask_json", _data_architecture_stage_mock)

    architecture, validation = data_architecture_engine.propose_data_architecture("rag", tree, "context")

    assert validation.passed
    assert len(architecture.entities) == 2
    assert len(architecture.anchors) == 2


def test_propose_data_architecture_transient_step_gets_no_anchor(monkeypatch):
    tree = _workflow_tree_fixture()
    monkeypatch.setattr(data_architecture_engine, "_ask_json", _data_architecture_stage_mock)

    architecture, _ = data_architecture_engine.propose_data_architecture("rag", tree, "context")

    assert all(a.node_id != "a3" for a in architecture.anchors)


def test_validate_data_architecture_catches_duplicate_entity_names():
    tree = _workflow_tree_fixture()
    architecture = DataArchitecture(
        domain="rag",
        entities=[
            DataEntity(id="D01", name="documents", domain="rag", attributes=[
                DataAttribute(name="id", type="UUID", is_primary_key=True),
            ]),
            DataEntity(id="D02", name="documents", domain="rag", attributes=[
                DataAttribute(name="id", type="UUID", is_primary_key=True),
            ]),
        ],
    )
    result = data_architecture_engine.validate_data_architecture(architecture, tree)
    assert not result.passed
    assert any("more than one entity" in v.message for v in result.violations)


def test_validate_data_architecture_catches_anchor_to_nonexistent_step():
    tree = _workflow_tree_fixture()
    architecture = DataArchitecture(
        domain="rag",
        entities=[DataEntity(id="D01", name="documents", domain="rag", attributes=[
            DataAttribute(name="id", type="UUID", is_primary_key=True),
        ])],
        anchors=[DataAnchor(domain="rag", node_id="__nonexistent__", node_label="?", data_id="D01", operation="WRITE")],
    )
    result = data_architecture_engine.validate_data_architecture(architecture, tree)
    assert not result.passed
    assert any("nonexistent Atomic step" in v.message for v in result.violations)
