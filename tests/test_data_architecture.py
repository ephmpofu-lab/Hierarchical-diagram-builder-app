"""Data Architecture Layer (Module 13) tests. See docs/ARCHITEQ-Data-Architecture-Layer-Spec.md
and ARCHITEQ-PRD.md R41-R50. AI calls are mocked throughout, matching this project's own
established convention (tests/test_engineering_decomposition.py's own docstring)."""

from backend.data_architecture import repository as data_architecture_repo
from backend.models import (
    DataAnchor,
    DataArchitecture,
    DataAttribute,
    DataEntity,
    DataRelationship,
)

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
