-- Phase 12 Implementation Roadmap, WP19 (Journey 3: Decomposition -> Implementation
-- Blueprint). Strictly additive -- one new column, existing node rows untouched.
--
-- Adds Node.milestone: a free-text grouping label (mirrors classification's convention)
-- set when a human commits an Implementation Blueprint proposal, grouping Task nodes that
-- belong to the same delivery milestone. Deliberately not a separate Milestone table --
-- nothing in v1 needs milestone-level metadata independent of the tasks under it.
--
-- Same lesson WP11b's own migration documented (learned from the real WP8/WP9 bug: new
-- Node fields silently fail to persist unless the repository's explicit load()/save()
-- column lists are updated in the same commit as this migration, not as an afterthought).

alter table nodes add column if not exists milestone text;
