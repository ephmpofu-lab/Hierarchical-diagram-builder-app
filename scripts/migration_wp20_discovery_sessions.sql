-- Discovery Session (Journey 4, WP20). Strictly additive -- a new table only, nothing
-- existing touched.
--
-- The one genuinely stateful AI surface in this app (backend/ai/provider.py's own
-- docstring: every other reasoning surface holds "no memory across calls"). Mirrors
-- cycles' own shape (migration_wp10_cycles.sql) -- a narrow table, turns/topic_coverage/
-- report stored as jsonb (genuinely open-ended/nested shapes), status/turn_count/
-- created_project_id as real, independently queryable columns.
--
-- owner_id is nullable for the same reason projects.owner_id is (see schema.sql's own
-- comment): with a real, live FK to auth.users(id), a NOT NULL constraint would make this
-- table untestable without a real Supabase account -- every existing test's authed_client
-- fixture uses a fake, non-existent user id, exactly as WP2's own
-- test_owner_id_column_is_fk_constrained_to_real_supabase_users demonstrates. Every route
-- already requires login, so owner_id is always populated with a real id in actual use --
-- this is a testability accommodation, not a real-world nullable case, same as projects.
create table if not exists discovery_sessions (
  id uuid primary key,
  owner_id uuid references auth.users(id) on delete cascade,
  status text not null default 'InProgress',
  created_project_id uuid references projects(id) on delete set null,
  turns jsonb not null default '[]'::jsonb,
  topic_coverage jsonb not null default '{}'::jsonb,
  turn_count int not null default 0,
  report jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists discovery_sessions_owner_id_idx on discovery_sessions(owner_id);
