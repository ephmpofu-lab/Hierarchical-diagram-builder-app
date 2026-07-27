-- Phase 12 Implementation Roadmap, WP8 (Decomposition strategy extensions) + WP9
-- (Change Management). Strictly additive -- new columns only, existing nodes rows
-- untouched.
--
-- WP8 added Node.abstraction_level and Node.decomposition_terminal (Phase 5 sections 5
-- and 9) but the Postgres repository's explicit column lists were never updated to
-- match, so both fields silently failed to persist -- caught live by a WP9 test that
-- round-trips Node.held_for_change through the real database. Fixing all three columns
-- in one migration since they share the same root cause.
--
-- WP9 adds Node.held_for_change (Phase 5 section 3's "Held" state, Phase 10 section 8).

alter table nodes add column if not exists abstraction_level text;
alter table nodes add column if not exists decomposition_terminal boolean;
alter table nodes add column if not exists held_for_change boolean not null default false;
