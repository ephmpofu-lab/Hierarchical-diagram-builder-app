-- SKAIDO Architect: PostgreSQL schema (Supabase)
-- Run this once in Supabase's SQL Editor (dashboard -> SQL Editor -> New query) before
-- running scripts/migrate_json_to_postgres.py.
--
-- Row-Level Security is deliberately NOT enabled on these tables yet -- the FastAPI backend
-- connects with a trusted, full-access connection (not a per-user Supabase session), so RLS
-- policies would have no auth context to evaluate against right now. `owner_id` is included
-- on `projects` so RLS can be added later without a disruptive schema change, once the auth
-- phase wires up real per-request identity.

create table projects (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  owner_id uuid references auth.users(id)  -- nullable for now; wired up in the auth phase
);

create table nodes (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  parent_id uuid references nodes(id) on delete cascade,
  sort_order integer not null default 0,      -- position among siblings
  label text not null default '',
  notes text not null default '',
  canvas_x double precision not null default 0,
  canvas_y double precision not null default 0,
  collapsed boolean not null default false,
  node_type text,
  status text,
  priority text,
  complexity text,
  risk_level text,
  tags text[] not null default '{}',
  owner text,
  shape text not null default 'rect',
  group_children boolean not null default false,
  is_group boolean not null default false,
  classification text,
  custom_color text,
  planning_status text,
  locked boolean not null default false
);
create index idx_nodes_project_id on nodes(project_id);
create index idx_nodes_parent_id on nodes(parent_id);

create table comments (
  id uuid primary key default gen_random_uuid(),
  node_id uuid not null references nodes(id) on delete cascade,
  text text not null,
  created_at timestamptz not null default now()
);
create index idx_comments_node_id on comments(node_id);

-- Named project_references, not "references" -- REFERENCES is a reserved SQL keyword.
create table project_references (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  from_id uuid not null,   -- points at a node OR concept_object id; resolved at read time,
  to_id uuid not null,     -- same as the current JSON-file behavior -- no FK constraint here
  label text,
  reference_type text,
  custom_color text,
  thickness text,
  direction text,
  animated boolean not null default false,
  connector_hidden boolean not null default false,
  line_style text,
  opacity double precision,
  show_arrowhead boolean not null default true,
  curve_style text,
  animation_speed double precision
);
create index idx_project_references_project_id on project_references(project_id);

create table concept_objects (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  type text not null,
  x double precision not null,
  y double precision not null,
  width double precision not null default 160,
  height double precision not null default 90,
  rotation double precision not null default 0,
  text text not null default '',
  color text,
  border_style text not null default 'solid',
  z_index integer not null default 0,
  locked boolean not null default false,
  group_id text
);
create index idx_concept_objects_project_id on concept_objects(project_id);

create table activity_log (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  "timestamp" timestamptz not null default now(),
  message text not null
);
create index idx_activity_log_project_id on activity_log(project_id);

-- Templates stay as a JSONB snapshot -- TemplateNode is a small, recursive, rarely-queried
-- tree with no independent query need, unlike the live project data above.
create table templates (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now(),
  root jsonb not null
);

-- ============================================================================
-- Enterprise Architecture Meta Model (Phase 3) -- added in WP1 of the Phase 12
-- Implementation Roadmap. See scripts/migration_wp1_governance_knowledge.sql for the
-- additive migration this was first applied through against the live database.
-- ============================================================================

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

-- Project-independent (Knowledge Domain + Standards Library, Phase 8 §2) -- enterprise-wide,
-- mirroring templates' project-independent shape.

create table knowledge_concepts (
  id uuid primary key default gen_random_uuid(),
  concept_id text not null unique,
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
