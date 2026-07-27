-- Phase 12 Implementation Roadmap, WP11b (Timeline workspace). Strictly additive -- new
-- columns only, existing nodes rows untouched.
--
-- Resolves Phase 9 section 6's own flagged gap ("temporal attributes (target date,
-- duration) do not yet exist on DecompositionNode... left for Phase 11 [implementation
-- planning]") -- Phase 11 itself deferred the decision further to "Phase 12 implementation
-- planning." WP11b is that point: adding target_date/duration_days so the Timeline
-- workspace has real data to render instead of inventing a parallel schedule model.
--
-- Learned from the real WP8/WP9 bug (two new Node fields were added to models.py but never
-- wired into this repository's explicit column lists, silently failing to persist): the
-- matching load()/save() column-list changes are applied in the same commit as this
-- migration, not as an afterthought.

alter table nodes add column if not exists target_date date;
alter table nodes add column if not exists duration_days integer;
