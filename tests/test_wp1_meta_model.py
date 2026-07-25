"""WP1 (Phase 12 Implementation Roadmap, Increment 1 -- Foundation) tests.

Covers: the new Pydantic models validate correctly, and the new Requirement /
TraceabilityLink / Risk / GovernanceDecision / ValidationFinding / RiskAssessment /
KnowledgeConcept / KnowledgeRelationship / GovernancePrinciple entities round-trip
correctly through the live Postgres-backed repositories (unit + integration, per the
Phase 12 §9 testing strategy).

Integration tests run against the real database (the same one the app uses) inside a
throwaway project/knowledge-concept, deleted in a `finally` block -- never left behind,
never touching real project data.
"""

import uuid
from datetime import datetime, timezone

import pytest

from backend import storage
from backend.models import (
    GovernanceDecision,
    GovernancePrincipleCreate,
    KnowledgeConceptCreate,
    KnowledgeRelationshipCreate,
    Project,
    Requirement,
    Risk,
    RiskAssessment,
    TraceabilityLink,
    ValidationFinding,
)

TEST_PREFIX = "__WP1_TEST__"


# ---------- Unit tests: model validation ----------


def test_project_defaults_include_new_entity_lists():
    project = Project(id="x", name="n", created_at="t", updated_at="t")
    assert project.requirements == []
    assert project.traceability_links == []
    assert project.risks == []
    assert project.governance_decisions == []
    assert project.validation_findings == []
    assert project.risk_assessments == []


def test_requirement_defaults_to_draft_status():
    req = Requirement(id="r1", description="Support SSO login")
    assert req.status == "Draft"
    assert req.parent_id is None


def test_risk_defaults_to_identified_status():
    risk = Risk(id="rk1", description="Vendor API rate limits")
    assert risk.status == "Identified"


# ---------- Integration tests: repository round-trip ----------


@pytest.fixture
def test_project():
    project = storage.create_project(f"{TEST_PREFIX}project")
    try:
        yield project
    finally:
        storage.delete_project(project.id)


def test_project_meta_model_entities_round_trip(test_project):
    root_id = next(iter(test_project.nodes))
    now = datetime.now(timezone.utc).isoformat()

    requirement = Requirement(
        id=str(uuid.uuid4()), description="Support SSO login", origin_node_id=root_id, status="Active"
    )
    sub_requirement = Requirement(
        id=str(uuid.uuid4()), description="Support SAML", parent_id=requirement.id, status="Draft"
    )
    link = TraceabilityLink(id=str(uuid.uuid4()), requirement_id=requirement.id, node_id=root_id)
    risk = Risk(
        id=str(uuid.uuid4()),
        description="Identity provider outage",
        classification="Availability",
        status="Classified",
        target_node_id=root_id,
    )
    decision = GovernanceDecision(
        id=str(uuid.uuid4()), timestamp=now, actor="enterprise-architect", decision_type="Approve",
        target_node_id=root_id, rationale="Meets principle P-1",
    )
    finding = ValidationFinding(
        id=str(uuid.uuid4()), timestamp=now, category="missing_owner", severity="Warning", target_node_id=root_id
    )
    assessment = RiskAssessment(
        id=str(uuid.uuid4()), timestamp=now, risk_id=risk.id, assessment_type="Initial", level="Medium"
    )

    test_project.requirements = [requirement, sub_requirement]
    test_project.traceability_links = [link]
    test_project.risks = [risk]
    test_project.governance_decisions = [decision]
    test_project.validation_findings = [finding]
    test_project.risk_assessments = [assessment]

    storage.save_project(test_project)
    reloaded = storage.load_project(test_project.id)

    assert {r.id for r in reloaded.requirements} == {requirement.id, sub_requirement.id}
    reloaded_sub = next(r for r in reloaded.requirements if r.id == sub_requirement.id)
    assert reloaded_sub.parent_id == requirement.id  # self-referential tree preserved

    assert len(reloaded.traceability_links) == 1
    assert reloaded.traceability_links[0].requirement_id == requirement.id
    assert reloaded.traceability_links[0].node_id == root_id

    assert len(reloaded.risks) == 1
    assert reloaded.risks[0].status == "Classified"

    assert len(reloaded.governance_decisions) == 1
    assert reloaded.governance_decisions[0].rationale == "Meets principle P-1"

    assert len(reloaded.validation_findings) == 1
    assert reloaded.validation_findings[0].severity == "Warning"

    assert len(reloaded.risk_assessments) == 1
    assert reloaded.risk_assessments[0].risk_id == risk.id


def test_governance_records_are_append_only_across_saves(test_project):
    now = datetime.now(timezone.utc).isoformat()
    first = GovernanceDecision(
        id=str(uuid.uuid4()), timestamp=now, actor="enterprise-architect", decision_type="Approve"
    )
    test_project.governance_decisions = [first]
    storage.save_project(test_project)

    reloaded = storage.load_project(test_project.id)
    second = GovernanceDecision(
        id=str(uuid.uuid4()), timestamp=now, actor="enterprise-architect", decision_type="Edit"
    )
    reloaded.governance_decisions = [second]  # deliberately omit `first` -- it must survive anyway
    storage.save_project(reloaded)

    final = storage.load_project(test_project.id)
    assert {d.id for d in final.governance_decisions} == {first.id, second.id}


@pytest.fixture
def test_concept():
    concept = storage.save_knowledge_concept(
        KnowledgeConceptCreate(
            concept_id=f"{TEST_PREFIX}ARC-0002",
            name="Architecture Domains",
            category="Core Concept",
            chapter_source=3,
            section_source="3.3",
            definition="TOGAF defines four architecture domains.",
            rules=["Enterprise Architecture shall include Business Architecture."],
            validation_criteria=["Business domain defined."],
        )
    )
    try:
        yield concept
    finally:
        storage.delete_knowledge_concept(concept.concept_id)


def test_knowledge_concept_round_trips(test_concept):
    reloaded = storage.load_knowledge_concept(test_concept.concept_id)
    assert reloaded.name == "Architecture Domains"
    assert reloaded.rules == ["Enterprise Architecture shall include Business Architecture."]
    assert reloaded.status == "Active"

    all_concepts = storage.list_knowledge_concepts()
    assert test_concept.concept_id in {c.concept_id for c in all_concepts}


def test_knowledge_relationship_and_governance_principle_round_trip(test_concept):
    second = storage.save_knowledge_concept(
        KnowledgeConceptCreate(
            concept_id=f"{TEST_PREFIX}ARC-0007",
            name="Architecture Principles",
            category="Core Concept",
            definition="Principles are enduring rules.",
        )
    )
    try:
        rel = storage.save_knowledge_relationship(
            KnowledgeRelationshipCreate(
                from_concept_id=test_concept.concept_id, to_concept_id=second.concept_id, relation_type="related"
            )
        )
        relationships = storage.list_knowledge_relationships(test_concept.concept_id)
        assert any(r.id == rel.id and r.to_concept_id == second.concept_id for r in relationships)

        principle = storage.save_governance_principle(
            GovernancePrincipleCreate(
                statement="Every Business Architecture shall be principle-driven.",
                applies_to_domain="Business",
                source_concept_id=test_concept.concept_id,
            )
        )
        try:
            principles = storage.list_governance_principles()
            assert any(p.id == principle.id for p in principles)
        finally:
            storage.delete_governance_principle(principle.id)
    finally:
        storage.delete_knowledge_concept(second.concept_id)
