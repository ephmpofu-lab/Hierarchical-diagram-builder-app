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
