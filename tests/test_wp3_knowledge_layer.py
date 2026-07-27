"""WP3 (Phase 12 Implementation Roadmap, Increment 2 -- Knowledge Layer MVP) tests.

Covers the Knowledge & Reasoning Framework (Phase 6) pipeline built in WP3: ingestion/
parsing of curated Markdown, classification, QA, the versioning lifecycle state machine,
and keyword + one-hop retrieval. Integration tests run against the real database inside
throwaway, uniquely-suffixed concept_ids, deleted in a `finally` block.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app import app
from backend import storage
from backend.auth import AuthenticatedUser, require_auth
from backend.knowledge import lifecycle
from backend.knowledge.classification import classify
from backend.knowledge.ingestion import parse_markdown
from backend.knowledge.qa import run_qa
from backend.knowledge.retrieval import retrieve
from backend.models import KnowledgeConcept, KnowledgeRelationship

TEST_PREFIX = "__WP3_TEST__"


def _cid() -> str:
    return f"{TEST_PREFIX}{uuid.uuid4().hex[:8]}"


# ---------- Unit tests: classification ----------


def test_classify_normalizes_case():
    assert classify("core concept") == "Core Concept"
    assert classify("Reasoning Rule") == "Reasoning Rule"


def test_classify_rejects_unknown_category():
    with pytest.raises(ValueError):
        classify("Not A Real Category")


# ---------- Unit tests: ingestion / parsing ----------


def test_parse_markdown_extracts_core_and_extended_fields():
    markdown = """
# Some heading

```yaml
id: ARC-TEST-01
name: Test Concept
category: Core Concept
chapter_source: 3
section_source: "3.4"
definition: A concept used only for testing.
purpose: Demonstrate parsing.
characteristics:
  - abstract
  - testable
rules:
  - Must be testable.
validation:
  - Has a definition.
related:
  - ARC-TEST-02
domains:
  - Business
lifecycle: Active
```
"""
    candidates, errors = parse_markdown(markdown)
    assert errors == []
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.concept_id == "ARC-TEST-01"
    assert candidate.category == "Core Concept"
    assert candidate.chapter_source == 3
    assert candidate.section_source == "3.4"
    assert candidate.purpose == "Demonstrate parsing."
    assert candidate.characteristics == ["abstract", "testable"]
    assert candidate.validation_criteria == ["Has a definition."]
    assert candidate.related == ["ARC-TEST-02"]
    assert candidate.extended == {"domains": ["Business"], "lifecycle": "Active"}


def test_parse_markdown_multiple_blocks_one_bad_does_not_abort_batch():
    markdown = """
```yaml
id: ARC-TEST-GOOD
name: Good Concept
category: Core Concept
definition: This one is fine.
```

```yaml
name: Missing Id
category: Core Concept
definition: This one is missing its id.
```
"""
    candidates, errors = parse_markdown(markdown)
    assert len(candidates) == 1
    assert candidates[0].concept_id == "ARC-TEST-GOOD"
    assert len(errors) == 1
    assert "missing required field 'id'" in errors[0]


def test_parse_markdown_no_yaml_blocks_reports_error():
    candidates, errors = parse_markdown("just some prose, no yaml here")
    assert candidates == []
    assert errors


def test_parse_markdown_unknown_category_reports_error_not_crash():
    markdown = """
```yaml
id: ARC-TEST-BAD-CAT
name: Bad Category
category: Not A Real Category
definition: Should be reported, not raised.
```
"""
    candidates, errors = parse_markdown(markdown)
    assert candidates == []
    assert "Unrecognized category" in errors[0]


# ---------- Unit tests: QA ----------


def _concept(**overrides) -> KnowledgeConcept:
    defaults = dict(
        id=str(uuid.uuid4()),
        concept_id=_cid(),
        name="Test Concept",
        category="Core Concept",
        definition="A definition.",
        rules=["A rule."],
        validation_criteria=["A criterion."],
        related=[],
        status="UnderReview",
    )
    defaults.update(overrides)
    return KnowledgeConcept(**defaults)


def test_qa_passes_clean_concept():
    report = run_qa(_concept(), [])
    assert report.passed
    assert report.findings == []


def test_qa_flags_dangling_related_reference_as_critical():
    report = run_qa(_concept(related=["does-not-exist"]), [])
    assert not report.passed
    assert any(f.severity == "Critical" for f in report.findings)


def test_qa_flags_conflicting_duplicate_concept_id_as_critical():
    existing = _concept(definition="Original definition.")
    revised = _concept(concept_id=existing.concept_id, definition="Different definition.")
    report = run_qa(revised, [existing])
    assert not report.passed


def test_qa_allows_conflict_when_explicitly_marked_as_supersession():
    existing = _concept(definition="Original definition.")
    revision = _concept(
        concept_id=existing.concept_id, definition="Different definition.", supersedes=existing.concept_id
    )
    report = run_qa(revision, [existing])
    assert report.passed


def test_qa_empty_rules_is_warning_only_not_blocking():
    report = run_qa(_concept(rules=[], validation_criteria=[]), [])
    assert report.passed
    assert all(f.severity == "Warning" for f in report.findings)


# ---------- Unit tests: lifecycle ----------


@pytest.mark.parametrize(
    "current,target,expected",
    [
        ("Proposed", "UnderReview", True),
        ("UnderReview", "Active", True),
        ("UnderReview", "Rejected", True),
        ("Active", "Superseded", True),
        ("Active", "Deprecated", True),
        ("Superseded", "Deprecated", True),
        ("Deprecated", "Archived", True),
        ("Proposed", "Active", False),  # cannot skip QA/governance
        ("Active", "Proposed", False),  # no going backwards
        ("Rejected", "Active", False),  # terminal
        ("Archived", "Active", False),  # terminal
    ],
)
def test_lifecycle_transitions_match_state_diagram(current, target, expected):
    assert lifecycle.can_transition(current, target) is expected


def test_require_transition_raises_on_invalid():
    with pytest.raises(ValueError):
        lifecycle.require_transition("Proposed", "Active")


# ---------- Unit tests: retrieval ----------


def test_retrieve_ranks_by_keyword_overlap_and_expands_one_hop():
    direct = _concept(name="Business Architecture", definition="Describes business capabilities.", status="Active")
    unrelated = _concept(name="Technology Standard", definition="Describes network protocols.", status="Active")
    hop = _concept(name="Capability Mapping", definition="Related structural concept.", status="Active")
    rel = KnowledgeRelationship(
        id=str(uuid.uuid4()), from_concept_id=direct.concept_id, to_concept_id=hop.concept_id, relation_type="related"
    )

    results = retrieve("business capabilities", [direct, unrelated, hop], [rel])
    result_ids = [c.concept_id for c in results]
    assert result_ids[0] == direct.concept_id  # best keyword match ranked first
    assert hop.concept_id in result_ids  # pulled in via one-hop expansion
    assert unrelated.concept_id not in result_ids


def test_retrieve_empty_objective_returns_nothing():
    assert retrieve("", [_concept(status="Active")], []) == []


# ---------- Integration tests: live DB round-trip through storage ----------


@pytest.fixture
def qa_authed_client():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(
        id="wp3-test-user", email="wp3@example.com", role="EnterpriseArchitect"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_ingest_endpoint_creates_proposed_concepts_and_reports_errors(qa_authed_client):
    concept_id = _cid()
    markdown = f"""
```yaml
id: {concept_id}
name: Ingested Concept
category: Core Concept
definition: Created through the ingest endpoint.
```

```yaml
name: Missing Id Again
category: Core Concept
definition: Should be reported as an error.
```
"""
    try:
        response = qa_authed_client.post("/api/knowledge/ingest", json={"markdown": markdown})
        assert response.status_code == 201
        body = response.json()
        assert len(body["created"]) == 1
        assert body["created"][0]["status"] == "Proposed"
        assert len(body["errors"]) == 1
    finally:
        storage.delete_knowledge_concept(concept_id)


def test_full_lifecycle_qa_approve_deprecate_archive(qa_authed_client):
    concept_id = _cid()
    try:
        response = qa_authed_client.post(
            "/api/knowledge/ingest",
            json={"markdown": f"```yaml\nid: {concept_id}\nname: Lifecycle Test\ncategory: Core Concept\n"
                               f"definition: Exercises the full lifecycle.\nrules:\n  - A rule.\n"
                               f"validation:\n  - A criterion.\n```"},
        )
        assert response.json()["created"][0]["status"] == "Proposed"

        qa_response = qa_authed_client.post(f"/api/knowledge/concepts/{concept_id}/submit-for-qa")
        assert qa_response.status_code == 200
        assert qa_response.json()["passed"] is True
        assert storage.load_knowledge_concept(concept_id).status == "UnderReview"

        approve_response = qa_authed_client.post(f"/api/knowledge/concepts/{concept_id}/approve")
        assert approve_response.json()["status"] == "Active"

        # Only Active concepts are retrievable.
        retrieved = qa_authed_client.get(
            "/api/knowledge/retrieve", params={"objective": "lifecycle test exercises"}
        ).json()
        assert concept_id in {c["concept_id"] for c in retrieved}

        deprecate_response = qa_authed_client.post(f"/api/knowledge/concepts/{concept_id}/deprecate")
        assert deprecate_response.json()["status"] == "Deprecated"

        retrieved_after_deprecation = qa_authed_client.get(
            "/api/knowledge/retrieve", params={"objective": "lifecycle test exercises"}
        ).json()
        assert concept_id not in {c["concept_id"] for c in retrieved_after_deprecation}

        archive_response = qa_authed_client.post(f"/api/knowledge/concepts/{concept_id}/archive")
        assert archive_response.json()["status"] == "Archived"

        # Terminal state -- cannot transition further.
        invalid_response = qa_authed_client.post(f"/api/knowledge/concepts/{concept_id}/deprecate")
        assert invalid_response.status_code == 400
    finally:
        storage.delete_knowledge_concept(concept_id)


def test_submit_for_qa_auto_rejects_on_critical_finding(qa_authed_client):
    concept_id = _cid()
    try:
        qa_authed_client.post(
            "/api/knowledge/ingest",
            json={
                "markdown": f"```yaml\nid: {concept_id}\nname: Dangling Ref\ncategory: Core Concept\n"
                f"definition: References a concept that does not exist.\nrelated:\n  - nonexistent-concept\n```"
            },
        )
        qa_response = qa_authed_client.post(f"/api/knowledge/concepts/{concept_id}/submit-for-qa")
        assert qa_response.json()["passed"] is False
        assert storage.load_knowledge_concept(concept_id).status == "Rejected"
    finally:
        storage.delete_knowledge_concept(concept_id)


def test_approve_cascades_supersede_to_the_replaced_concept(qa_authed_client):
    old_id = _cid()
    new_id = _cid()
    try:
        # Get the original concept to Active first.
        qa_authed_client.post(
            "/api/knowledge/ingest",
            json={
                "markdown": f"```yaml\nid: {old_id}\nname: Original\ncategory: Core Concept\n"
                f"definition: The original content.\n```"
            },
        )
        qa_authed_client.post(f"/api/knowledge/concepts/{old_id}/submit-for-qa")
        qa_authed_client.post(f"/api/knowledge/concepts/{old_id}/approve")
        assert storage.load_knowledge_concept(old_id).status == "Active"

        # Submit a revision that declares it supersedes the original.
        qa_authed_client.post(
            "/api/knowledge/ingest",
            json={
                "markdown": f"```yaml\nid: {new_id}\nname: Revised\ncategory: Core Concept\n"
                f"definition: The revised content.\nsupersedes: {old_id}\n```"
            },
        )
        qa_authed_client.post(f"/api/knowledge/concepts/{new_id}/submit-for-qa")
        approve_response = qa_authed_client.post(f"/api/knowledge/concepts/{new_id}/approve")
        assert approve_response.json()["status"] == "Active"

        # The concept it superseded should have flipped to Superseded automatically.
        assert storage.load_knowledge_concept(old_id).status == "Superseded"
    finally:
        storage.delete_knowledge_concept(new_id)
        storage.delete_knowledge_concept(old_id)


def test_relationship_endpoint_rejects_nonexistent_concepts(qa_authed_client):
    response = qa_authed_client.post(
        "/api/knowledge/relationships",
        json={"from_concept_id": "nope-1", "to_concept_id": "nope-2", "relation_type": "related"},
    )
    assert response.status_code == 404
