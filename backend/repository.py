"""Storage-agnostic interfaces. `backend/storage.py` depends only on these Protocols, never
on a concrete database — swapping the backing implementation (Postgres today, something
else later) means writing a new class that satisfies these shapes, nothing more."""

from typing import List, Protocol

from .models import (
    GovernancePrinciple,
    GovernancePrincipleCreate,
    KnowledgeConcept,
    KnowledgeConceptCreate,
    KnowledgeRelationship,
    KnowledgeRelationshipCreate,
    Project,
    ProjectSummary,
    Template,
    TemplateNode,
    TemplateSummary,
)


class ProjectRepository(Protocol):
    def list_summaries(self, owner_id: str | None = None) -> List[ProjectSummary]: ...

    def load(self, project_id: str) -> Project: ...

    def save(self, project: Project) -> None: ...

    def create(self, name: str, owner_id: str | None = None) -> Project: ...

    def delete(self, project_id: str) -> None: ...

    def rename(self, project_id: str, name: str) -> Project: ...


class TemplateRepository(Protocol):
    def list_summaries(self) -> List[TemplateSummary]: ...

    def load(self, template_id: str) -> Template: ...

    def save_new(self, name: str, root: TemplateNode) -> Template: ...

    def delete(self, template_id: str) -> None: ...


class KnowledgeRepository(Protocol):
    """The Enterprise Knowledge Layer's storage abstraction (project-independent --
    Knowledge Domain + Standards Library, Phase 8 §2). Named but left unpopulated in the
    Phase 2 Blueprint ("interface defined now -- not yet populated"); this is that
    population, per the Phase 12 Implementation Roadmap's WP1."""

    def list_concepts(self) -> List[KnowledgeConcept]: ...

    def load_concept(self, concept_id: str) -> KnowledgeConcept: ...

    def save_concept(self, concept: KnowledgeConceptCreate) -> KnowledgeConcept: ...

    def delete_concept(self, concept_id: str) -> None: ...

    def list_relationships(self, concept_id: str) -> List[KnowledgeRelationship]: ...

    def save_relationship(self, relationship: KnowledgeRelationshipCreate) -> KnowledgeRelationship: ...

    def list_principles(self) -> List[GovernancePrinciple]: ...

    def save_principle(self, principle: GovernancePrincipleCreate) -> GovernancePrinciple: ...

    def delete_principle(self, principle_id: str) -> None: ...
