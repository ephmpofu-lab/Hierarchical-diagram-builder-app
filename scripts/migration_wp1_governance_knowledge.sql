-- WP1: Enterprise meta-model extension (Phase 12 Implementation Roadmap, Increment 1 --
-- Foundation). Realizes the Phase 3 Enterprise Meta Model's Requirement, TraceabilityLink,
-- Risk, GovernanceDecision/ValidationFinding/RiskAssessment, KnowledgeConcept/
-- KnowledgeRelationship, and GovernancePrinciple entities.
--
-- ADDITIVE ONLY -- every statement below creates a new table. Nothing here alters, drops,
-- or rewrites any existing table (projects, nodes, comments, project_references,
-- concept_objects, activity_log, templates all stay exactly as they are). Safe to run
-- against the live database without any risk to existing project data.
--
-- Run this once in Supabase's SQL Editor, the same way scripts/schema.sql was originally run.

-- ---------- Project-scoped entities (Architecture Landscape + Requirements Repository +
-- ---------- Governance Repository domains, Phase 8 §2) ----------

create table requirements (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  parent_id uuid references requirements(id) on delete cascade,
  description text not null,
  origin_node_id uuid references nodes(id) on delete set null,
  status text not null default 'Draft'
);
create index idx_requirements_project_id on requirements(project_id);
create index idx_requirements_parent_id on requirements(parent_id);

create table traceability_links (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  requirement_id uuid not null references requirements(id) on delete cascade,
  node_id uuid not null references nodes(id) on delete cascade,
  link_type text not null default 'satisfies'
);
create index idx_traceability_links_project_id on traceability_links(project_id);
create index idx_traceability_links_requirement_id on traceability_links(requirement_id);
create index idx_traceability_links_node_id on traceability_links(node_id);

create table risks (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  description text not null,
  classification text,
  initial_level text,
  residual_level text,
  status text not null default 'Identified',
  target_node_id uuid references nodes(id) on delete set null
);
create index idx_risks_project_id on risks(project_id);

create table governance_decisions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  "timestamp" timestamptz not null default now(),
  actor text not null,
  decision_type text not null,
  target_node_id uuid references nodes(id) on delete set null,
  rationale text
);
create index idx_governance_decisions_project_id on governance_decisions(project_id);

create table validation_findings (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  "timestamp" timestamptz not null default now(),
  category text not null,
  severity text not null,
  target_node_id uuid references nodes(id) on delete set null
);
create index idx_validation_findings_project_id on validation_findings(project_id);

create table risk_assessments (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  "timestamp" timestamptz not null default now(),
  risk_id uuid not null references risks(id) on delete cascade,
  assessment_type text not null,
  level text not null
);
create index idx_risk_assessments_project_id on risk_assessments(project_id);
create index idx_risk_assessments_risk_id on risk_assessments(risk_id);

-- ---------- Project-independent entities (Knowledge Domain + Standards Library,
-- ---------- Phase 8 §2) -- enterprise-wide, mirroring the existing `templates` table's
-- ---------- project-independent shape, not nested under any single project. ----------

create table knowledge_concepts (
  id uuid primary key default gen_random_uuid(),
  concept_id text not null unique,  -- the Knowledge Base's own stable id, e.g. "ARC-0002"
  name text not null,
  category text not null,
  chapter_source integer,
  section_source text,
  definition text not null,
  rules text[] not null default '{}',
  validation_criteria text[] not null default '{}',
  related text[] not null default '{}',
  status text not null default 'Active'
);
create index idx_knowledge_concepts_category on knowledge_concepts(category);
create index idx_knowledge_concepts_status on knowledge_concepts(status);

create table knowledge_relationships (
  id uuid primary key default gen_random_uuid(),
  from_concept_id text not null references knowledge_concepts(concept_id) on delete cascade,
  to_concept_id text not null references knowledge_concepts(concept_id) on delete cascade,
  relation_type text not null
);
create index idx_knowledge_relationships_from on knowledge_relationships(from_concept_id);

create table governance_principles (
  id uuid primary key default gen_random_uuid(),
  statement text not null,
  applies_to_domain text,
  source_concept_id text references knowledge_concepts(concept_id) on delete set null
);
