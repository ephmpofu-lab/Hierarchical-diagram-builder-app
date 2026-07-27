-- Phase 12 Implementation Roadmap, WP13b (Observability, Phase 11 section 13). Strictly
-- additive -- a new table only, nothing existing touched.
--
-- The technical substrate underneath Phase 10 section 10's Governance Performance
-- Monitoring (a business/process concern, still out of scope per WP6's own scope line):
-- AI service call metrics (latency, retry counts) and agent invocation success/failure
-- rates. project_id is nullable -- an AI call or reasoning-pipeline run isn't always tied
-- to a project (the same reasoning as cycles.project_id from WP10).

create table if not exists metrics_events (
  id uuid primary key,
  event_type text not null,       -- 'ai_call' | 'agent_invocation'
  subject text not null,          -- model name (ai_call) or agent name (agent_invocation)
  project_id uuid references projects(id) on delete cascade,
  success boolean not null,
  duration_ms integer,
  retries integer,
  error_type text,
  created_at timestamptz not null default now()
);

create index if not exists metrics_events_type_subject_idx on metrics_events(event_type, subject);
create index if not exists metrics_events_created_at_idx on metrics_events(created_at);
