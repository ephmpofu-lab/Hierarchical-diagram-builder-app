-- Phase 12 Implementation Roadmap, WP10 (Event-driven layer). Strictly additive -- a new
-- table only, nothing existing touched.
--
-- Cycle records (Phase 11 sections 5-6): the async counterpart to the existing synchronous
-- /api/intelligence/reason and /api/projects/{id}/nodes/{id}/decompose endpoints. A Cycle
-- tracks one background run of the already-existing, unmodified Orchestrator (WP7/WP8) --
-- events and the final result are stored as jsonb (same precedent as
-- knowledge_concepts.extended from WP3) since both are genuinely open-ended/nested shapes,
-- while status/kind/objective/node_id stay real, independently queryable columns.
--
-- Deliberately its own narrow table, not folded into the projects/nodes row-per-field
-- pattern: a background cycle updates its own row directly, independent of the rest of the
-- project, rather than going through the existing whole-project load-mutate-save cycle
-- (which would mean holding a long-lived in-memory Project snapshot across a multi-stage AI
-- run and risking clobbering an unrelated concurrent edit on save).

-- project_id is nullable: a "reasoning" cycle wraps the existing project-independent
-- /api/intelligence/reason endpoint (WP5), which never belonged to any project (it
-- produces proposals only, with no commit path) -- a "decomposition" cycle is always
-- scoped to the project owning the node being decomposed.
create table if not exists cycles (
  id uuid primary key,
  project_id uuid references projects(id) on delete cascade,
  kind text not null,
  status text not null default 'Running',
  objective text,
  node_id uuid references nodes(id) on delete set null,
  error text,
  events jsonb not null default '[]'::jsonb,
  result jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists cycles_project_id_idx on cycles(project_id);
