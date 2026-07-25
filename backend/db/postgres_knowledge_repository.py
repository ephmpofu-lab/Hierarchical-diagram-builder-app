"""Postgres-backed KnowledgeRepository -- the Enterprise Knowledge Layer's storage
abstraction (Knowledge Domain + Standards Library, Phase 8 §2). Project-independent,
same shape of independence as PostgresTemplateRepository: these rows aren't nested under
any single project."""

import uuid
from typing import List

from fastapi import HTTPException

from ..models import (
    GovernancePrinciple,
    GovernancePrincipleCreate,
    KnowledgeConcept,
    KnowledgeConceptCreate,
    KnowledgeRelationship,
    KnowledgeRelationshipCreate,
)
from .connection import get_pool


class PostgresKnowledgeRepository:
    def list_concepts(self) -> List[KnowledgeConcept]:
        with get_pool().connection() as conn:
            rows = conn.execute(
                "select id, concept_id, name, category, chapter_source, section_source, "
                "definition, rules, validation_criteria, related, status "
                "from knowledge_concepts order by concept_id"
            ).fetchall()
        return [self._concept_from_row(r) for r in rows]

    def load_concept(self, concept_id: str) -> KnowledgeConcept:
        with get_pool().connection() as conn:
            row = conn.execute(
                "select id, concept_id, name, category, chapter_source, section_source, "
                "definition, rules, validation_criteria, related, status "
                "from knowledge_concepts where concept_id = %s",
                (concept_id,),
            ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Knowledge concept not found")
        return self._concept_from_row(row)

    def save_concept(self, concept: KnowledgeConceptCreate) -> KnowledgeConcept:
        new_id = str(uuid.uuid4())
        with get_pool().connection() as conn:
            conn.execute(
                """
                insert into knowledge_concepts (
                    id, concept_id, name, category, chapter_source, section_source,
                    definition, rules, validation_criteria, related
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (concept_id) do update set
                    name = excluded.name, category = excluded.category,
                    chapter_source = excluded.chapter_source, section_source = excluded.section_source,
                    definition = excluded.definition, rules = excluded.rules,
                    validation_criteria = excluded.validation_criteria, related = excluded.related
                """,
                (
                    new_id,
                    concept.concept_id,
                    concept.name,
                    concept.category,
                    concept.chapter_source,
                    concept.section_source,
                    concept.definition,
                    concept.rules,
                    concept.validation_criteria,
                    concept.related,
                ),
            )
        return self.load_concept(concept.concept_id)

    def delete_concept(self, concept_id: str) -> None:
        with get_pool().connection() as conn:
            result = conn.execute("delete from knowledge_concepts where concept_id = %s", (concept_id,))
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Knowledge concept not found")

    def list_relationships(self, concept_id: str) -> List[KnowledgeRelationship]:
        with get_pool().connection() as conn:
            rows = conn.execute(
                "select id, from_concept_id, to_concept_id, relation_type "
                "from knowledge_relationships where from_concept_id = %s",
                (concept_id,),
            ).fetchall()
        return [
            KnowledgeRelationship(id=str(r[0]), from_concept_id=r[1], to_concept_id=r[2], relation_type=r[3])
            for r in rows
        ]

    def save_relationship(self, relationship: KnowledgeRelationshipCreate) -> KnowledgeRelationship:
        new_id = str(uuid.uuid4())
        with get_pool().connection() as conn:
            conn.execute(
                """
                insert into knowledge_relationships (id, from_concept_id, to_concept_id, relation_type)
                values (%s, %s, %s, %s)
                """,
                (new_id, relationship.from_concept_id, relationship.to_concept_id, relationship.relation_type),
            )
        return KnowledgeRelationship(
            id=new_id,
            from_concept_id=relationship.from_concept_id,
            to_concept_id=relationship.to_concept_id,
            relation_type=relationship.relation_type,
        )

    def list_principles(self) -> List[GovernancePrinciple]:
        with get_pool().connection() as conn:
            rows = conn.execute(
                "select id, statement, applies_to_domain, source_concept_id from governance_principles"
            ).fetchall()
        return [
            GovernancePrinciple(id=str(r[0]), statement=r[1], applies_to_domain=r[2], source_concept_id=r[3])
            for r in rows
        ]

    def save_principle(self, principle: GovernancePrincipleCreate) -> GovernancePrinciple:
        new_id = str(uuid.uuid4())
        with get_pool().connection() as conn:
            conn.execute(
                """
                insert into governance_principles (id, statement, applies_to_domain, source_concept_id)
                values (%s, %s, %s, %s)
                """,
                (new_id, principle.statement, principle.applies_to_domain, principle.source_concept_id),
            )
        return GovernancePrinciple(
            id=new_id,
            statement=principle.statement,
            applies_to_domain=principle.applies_to_domain,
            source_concept_id=principle.source_concept_id,
        )

    def delete_principle(self, principle_id: str) -> None:
        with get_pool().connection() as conn:
            result = conn.execute("delete from governance_principles where id = %s", (principle_id,))
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Governance principle not found")

    @staticmethod
    def _concept_from_row(row) -> KnowledgeConcept:
        return KnowledgeConcept(
            id=str(row[0]),
            concept_id=row[1],
            name=row[2],
            category=row[3],
            chapter_source=row[4],
            section_source=row[5],
            definition=row[6],
            rules=list(row[7] or []),
            validation_criteria=list(row[8] or []),
            related=list(row[9] or []),
            status=row[10],
        )
