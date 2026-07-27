"""Postgres-backed KnowledgeRepository -- the Enterprise Knowledge Layer's storage
abstraction (Knowledge Domain + Standards Library, Phase 8 §2). Project-independent,
same shape of independence as PostgresTemplateRepository: these rows aren't nested under
any single project."""

import uuid
from typing import List, Optional

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from ..models import (
    GovernancePrinciple,
    GovernancePrincipleCreate,
    KnowledgeConcept,
    KnowledgeConceptCreate,
    KnowledgeRelationship,
    KnowledgeRelationshipCreate,
)
from .connection import get_pool

_CONCEPT_COLUMNS = (
    "id, concept_id, name, category, chapter_source, section_source, definition, "
    "purpose, characteristics, rules, validation_criteria, related, extended, "
    "supersedes, status"
)


class PostgresKnowledgeRepository:
    def list_concepts(
        self, status: Optional[str] = None, category: Optional[str] = None
    ) -> List[KnowledgeConcept]:
        clauses = []
        params: list = []
        if status is not None:
            clauses.append("status = %s")
            params.append(status)
        if category is not None:
            clauses.append("category = %s")
            params.append(category)
        where = f"where {' and '.join(clauses)}" if clauses else ""
        with get_pool().connection() as conn:
            rows = conn.execute(
                f"select {_CONCEPT_COLUMNS} from knowledge_concepts {where} order by concept_id",
                params,
            ).fetchall()
        return [self._concept_from_row(r) for r in rows]

    def load_concept(self, concept_id: str) -> KnowledgeConcept:
        with get_pool().connection() as conn:
            row = conn.execute(
                f"select {_CONCEPT_COLUMNS} from knowledge_concepts where concept_id = %s",
                (concept_id,),
            ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Knowledge concept not found")
        return self._concept_from_row(row)

    def find_concepts(self, concept_ids: List[str]) -> List[KnowledgeConcept]:
        if not concept_ids:
            return []
        with get_pool().connection() as conn:
            rows = conn.execute(
                f"select {_CONCEPT_COLUMNS} from knowledge_concepts where concept_id = any(%s)",
                (list(concept_ids),),
            ).fetchall()
        return [self._concept_from_row(r) for r in rows]

    def save_concept(self, concept: KnowledgeConceptCreate) -> KnowledgeConcept:
        new_id = str(uuid.uuid4())
        with get_pool().connection() as conn:
            conn.execute(
                """
                insert into knowledge_concepts (
                    id, concept_id, name, category, chapter_source, section_source,
                    definition, purpose, characteristics, rules, validation_criteria,
                    related, extended, supersedes
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (concept_id) do update set
                    name = excluded.name, category = excluded.category,
                    chapter_source = excluded.chapter_source, section_source = excluded.section_source,
                    definition = excluded.definition, purpose = excluded.purpose,
                    characteristics = excluded.characteristics, rules = excluded.rules,
                    validation_criteria = excluded.validation_criteria, related = excluded.related,
                    extended = excluded.extended, supersedes = excluded.supersedes
                """,
                (
                    new_id,
                    concept.concept_id,
                    concept.name,
                    concept.category,
                    concept.chapter_source,
                    concept.section_source,
                    concept.definition,
                    concept.purpose,
                    concept.characteristics,
                    concept.rules,
                    concept.validation_criteria,
                    concept.related,
                    Jsonb(concept.extended),
                    concept.supersedes,
                ),
            )
        return self.load_concept(concept.concept_id)

    def set_status(self, concept_id: str, status: str) -> KnowledgeConcept:
        with get_pool().connection() as conn:
            result = conn.execute(
                "update knowledge_concepts set status = %s where concept_id = %s",
                (status, concept_id),
            )
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Knowledge concept not found")
        return self.load_concept(concept_id)

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

    def list_all_relationships(self) -> List[KnowledgeRelationship]:
        with get_pool().connection() as conn:
            rows = conn.execute(
                "select id, from_concept_id, to_concept_id, relation_type from knowledge_relationships"
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
            purpose=row[7],
            characteristics=list(row[8] or []),
            rules=list(row[9] or []),
            validation_criteria=list(row[10] or []),
            related=list(row[11] or []),
            extended=dict(row[12] or {}),
            supersedes=row[13],
            status=row[14],
        )
