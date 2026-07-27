-- Phase 12 Implementation Roadmap, WP3 (Knowledge Layer MVP). Strictly additive --
-- new columns only, existing knowledge_concepts/knowledge_relationships/governance_principles
-- rows and constraints from WP1 (migration_wp1_governance_knowledge.sql) are untouched.
--
-- Adds the fields Phase 6 §3's acquisition schema names (purpose, characteristics) plus an
-- open extension bag for non-core YAML keys (domains:, lifecycle:, etc. -- Phase 6 §3), and a
-- `supersedes` lineage pointer for the versioning lifecycle (Phase 6 §9).

alter table knowledge_concepts add column if not exists purpose text;
alter table knowledge_concepts add column if not exists characteristics text[] not null default '{}';
alter table knowledge_concepts add column if not exists extended jsonb not null default '{}'::jsonb;
alter table knowledge_concepts add column if not exists supersedes text
  references knowledge_concepts(concept_id) on delete set null;

-- New concepts entering via ingestion always start "Proposed" now (Phase 6 §3 stage 4) --
-- WP1's column default of 'Active' only ever served that phase's own direct-write test data.
alter table knowledge_concepts alter column status set default 'Proposed';
