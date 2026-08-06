"""Planning Artifacts (Module 12, R38-R40) tests. See ARCHITEQ-PRD.md's Planning Artifacts
section and .agent/plans/12b.real-planning-artifact-generation.md. Every generator in
backend/planning_artifacts.py must derive its output only from the supplied domain fixture
(frozen Workflow Tree, Component Tree, Data Architecture) -- never from this repository's own
ARCHITEQ-*.md files, and never fabricated. AI calls are never used here (deterministic
generators only), matching this project's own established convention."""

import pytest
from fastapi.testclient import TestClient

from app import app
from backend.auth import AuthenticatedUser, require_auth
from backend.component import repository as component_repo
from backend.data_architecture import repository as data_architecture_repo
from backend.models import (
    Attribute,
    Component,
    ComponentTree,
    DataArchitecture,
    DataAttribute,
    DataEntity,
    DomainTaskTree,
    ExtractedRequirement,
    TaskTreeNode,
)
from backend.planning_artifacts import build_artifacts
from backend.taxonomy import repository as taxonomy_repo

TEST_DOMAIN = "__wp_planning_artifacts_test__"

ARCHITEQ_SELF_DOC_MARKERS = ["Universal PRD Framework", "ARCHITEQ-TDD.md", "dev-process.md", "RULES-INDEX"]


@pytest.fixture
def authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp-planning-artifacts-test-user", email="planning-artifacts@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _workflow_tree() -> DomainTaskTree:
    layer = TaskTreeNode(id="l1", label="Ingestion", level="Layer", children=["s1"])
    sub_task = TaskTreeNode(id="s1", label="Load documents", level="Sub-task", parent_id="l1", children=["a1", "a2"])
    step1 = TaskTreeNode(
        id="a1", label="Read PDF file", level="Atomic step", parent_id="s1",
        consumes="raw_pdf", produces="raw_text",
    )
    step2 = TaskTreeNode(
        id="a2", label="Store extracted text", level="Atomic step", parent_id="s1",
        consumes="raw_text", produces="stored_text", terminal_output=True, requires=["a1"],
    )
    return DomainTaskTree(
        domain=TEST_DOMAIN, root_ids=["l1"],
        nodes={"l1": layer, "s1": sub_task, "a1": step1, "a2": step2},
    )


def _component_tree(*, ui_tagged: bool) -> ComponentTree:
    return ComponentTree(
        domain=TEST_DOMAIN,
        requirements=[ExtractedRequirement(text="Ingest a PDF document", prd_requirement_id="R1", domain=TEST_DOMAIN)],
        components=[
            Component(label="Document Uploader", realizes_capability="Ingestion", domain=TEST_DOMAIN, is_ui_tagged=ui_tagged),
        ],
        attributes=[Attribute(name="max_size_mb", type="int", component_label="Document Uploader", domain=TEST_DOMAIN)],
    )


def _data_architecture() -> DataArchitecture:
    return DataArchitecture(
        domain=TEST_DOMAIN,
        entities=[
            DataEntity(
                id="D01", name="documents", domain=TEST_DOMAIN,
                attributes=[DataAttribute(name="id", type="UUID", is_primary_key=True, nullable=False)],
            ),
        ],
    )


# ---- build_artifacts: always derived only from the supplied fixture ----

def test_prd_and_tdd_are_always_built_from_the_supplied_workflow_tree():
    artifacts = build_artifacts(TEST_DOMAIN, _workflow_tree(), None, None)
    by_id = {a["id"]: a for a in artifacts}
    assert by_id["prd"]["status"] == "built"
    assert by_id["tdd"]["status"] == "built"
    assert "Read PDF file" in by_id["tdd"]["markdown"]
    assert "Store extracted text" in by_id["tdd"]["markdown"]
    assert TEST_DOMAIN in by_id["prd"]["markdown"]


def test_generators_never_use_architeqs_own_repository_documentation_as_content():
    artifacts = build_artifacts(TEST_DOMAIN, _workflow_tree(), _component_tree(ui_tagged=True), _data_architecture())
    for artifact in artifacts:
        blob = artifact["markdown"] + artifact["description"]
        for marker in ARCHITEQ_SELF_DOC_MARKERS:
            assert marker not in blob, f"{artifact['id']} leaked ARCHITEQ self-documentation: {marker!r}"


def test_prd_uses_component_tree_extracted_requirements_when_available():
    artifacts = build_artifacts(TEST_DOMAIN, _workflow_tree(), _component_tree(ui_tagged=True), None)
    prd = next(a for a in artifacts if a["id"] == "prd")
    assert "R1: Ingest a PDF document" in prd["markdown"]


def test_prd_falls_back_to_workflow_steps_without_a_component_tree():
    artifacts = build_artifacts(TEST_DOMAIN, _workflow_tree(), None, None)
    prd = next(a for a in artifacts if a["id"] == "prd")
    assert "Read PDF file" in prd["markdown"]


# ---- App Flow / Design Brief: gated on Component Tree presence (R33/CD10) ----

def test_app_flow_and_design_brief_are_unavailable_without_a_component_tree():
    artifacts = build_artifacts(TEST_DOMAIN, _workflow_tree(), None, None)
    by_id = {a["id"]: a for a in artifacts}
    for artifact_id in ("app_flow", "design_brief"):
        assert by_id[artifact_id]["status"] == "missing"
        assert "Component Tree" in by_id[artifact_id]["blocked_reason"]


def test_app_flow_and_design_brief_list_real_ui_tagged_components():
    artifacts = build_artifacts(TEST_DOMAIN, _workflow_tree(), _component_tree(ui_tagged=True), None)
    by_id = {a["id"]: a for a in artifacts}
    for artifact_id in ("app_flow", "design_brief"):
        assert by_id[artifact_id]["status"] == "built"
        assert "Document Uploader" in by_id[artifact_id]["markdown"]


def test_app_flow_and_design_brief_state_not_applicable_when_no_component_is_ui_tagged():
    artifacts = build_artifacts(TEST_DOMAIN, _workflow_tree(), _component_tree(ui_tagged=False), None)
    by_id = {a["id"]: a for a in artifacts}
    for artifact_id in ("app_flow", "design_brief"):
        assert by_id[artifact_id]["status"] == "built"
        assert "Not applicable" in by_id[artifact_id]["markdown"]
        assert "Document Uploader" not in by_id[artifact_id]["markdown"]


# ---- Backend Schema: gated on Data Architecture presence (R41) ----

def test_backend_schema_is_unavailable_without_a_data_architecture():
    artifacts = build_artifacts(TEST_DOMAIN, _workflow_tree(), None, None)
    backend_schema = next(a for a in artifacts if a["id"] == "backend_schema")
    assert backend_schema["status"] == "missing"
    assert "Data Architecture" in backend_schema["blocked_reason"]


def test_backend_schema_lists_real_entities_when_data_architecture_exists():
    artifacts = build_artifacts(TEST_DOMAIN, _workflow_tree(), None, _data_architecture())
    backend_schema = next(a for a in artifacts if a["id"] == "backend_schema")
    assert backend_schema["status"] == "built"
    assert "D01 documents" in backend_schema["markdown"]


# ---- Engineering Plan: always built, real roadmap ----

def test_engineering_plan_renders_the_real_roadmap():
    artifacts = build_artifacts(TEST_DOMAIN, _workflow_tree(), None, None)
    engineering_plan = next(a for a in artifacts if a["id"] == "engineering_plan")
    assert engineering_plan["status"] == "built"
    assert "Ingestion" in engineering_plan["markdown"]
    assert "Read PDF file" in engineering_plan["markdown"]


# ---- API endpoint ----

def test_planning_artifacts_endpoint_requires_auth():
    client = TestClient(app)
    response = client.get(f"/api/decompose/domains/{TEST_DOMAIN}/planning-artifacts")
    assert response.status_code in (401, 403)


def test_planning_artifacts_endpoint_404s_without_a_frozen_workflow_tree(authed_client):
    response = authed_client.get("/api/decompose/domains/__definitely_not_a_real_domain__/planning-artifacts")
    assert response.status_code == 404


def test_planning_artifacts_endpoint_returns_all_six_real_artifacts(authed_client):
    taxonomy_repo.save_tree(_workflow_tree())
    component_repo.save_component_tree(_component_tree(ui_tagged=True))
    data_architecture_repo.save_data_architecture(_data_architecture())
    try:
        response = authed_client.get(f"/api/decompose/domains/{TEST_DOMAIN}/planning-artifacts")
        assert response.status_code == 200
        body = response.json()
        assert {a["id"] for a in body} == {"prd", "tdd", "app_flow", "design_brief", "backend_schema", "engineering_plan"}
        assert all(a["status"] == "built" for a in body)
    finally:
        taxonomy_repo._TAXONOMIES_DIR.joinpath(f"{TEST_DOMAIN}.json").unlink(missing_ok=True)
        component_repo._COMPONENT_TREES_DIR.joinpath(f"{TEST_DOMAIN}.json").unlink(missing_ok=True)
        data_architecture_repo._DATA_ARCHITECTURES_DIR.joinpath(f"{TEST_DOMAIN}.json").unlink(missing_ok=True)
