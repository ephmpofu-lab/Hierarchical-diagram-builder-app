# Plan 10a-ii: Connection Classification (CR18)

**Complexity: Medium.** Pure backend data computation (`backend/render/node_mapper.py`),
building directly on 10a-i's `compute_stage_zones` output. No frontend change yet — that's
10a-iii's job, which will consume this classification to select a routing strategy.
Proceeds through Build/Test/Commit per the Autonomy Default.

## Requirement

Per `rules/principles/n8n-canvas-rules.md` CR18: "every rendered edge carries an explicit
classification tag before path generation begins; the geometry function invoked is a direct
function of that tag, never a single generic formula applied regardless of class." CR18
names six categories: adjacent primary, local branch, row transition, cross-row,
cross-stage, long-distance.

## Scope decisions

1. **Classification operates on tree-native Atomic step ids, not n8n display names.**
   `map_tree`'s `id_to_name` resolution (uniqueness suffixing) is a separate, later concern
   — classification only needs `TaskTreeNode.requires` and 10a-i's own
   `compute_stage_zones` positions/zones, both keyed by step id already. 10a-iii translates
   ids to names when it actually builds the SVG.
2. **The six categories, defined mechanically from position/zone data** (CR18's own text
   doesn't give an exact numeric boundary between "row transition" and "cross-row," or
   between "cross-stage" and "long-distance" — this sub-plan picks a concrete, defensible
   rule rather than leaving it a fuzzy judgment call, flagged here per this corpus's own
   "explicit over implicit" standard):
   - **adjacent** — same zone, same row, target is exactly one column to the right of source.
   - **local_branch** — same zone, same row, but not the immediately-next column (a
     same-row connection that isn't the simple sequential case).
   - **row_transition** — same zone, target's row is exactly one row after source's row
     (the ordinary "row wraps, continue in the next row" case).
   - **cross_row** — same zone, target's row is more than one row after source's row.
   - **cross_stage** — different zones, and those zones are adjacent in stacking order
     (`tree.root_ids` order) — i.e. crossing exactly one stage boundary.
   - **long_distance** — different zones, more than one stage boundary apart.
3. **Lives in `node_mapper.py`**, not a new module — CR18's own "Applies to" line names
   Node Mapper as the owner of edge classification (SVG Renderer only consumes the tag).

## Build (`backend/render/node_mapper.py`)

1. **`_classify_one(source_id, target_id, positions, node_to_zone, zone_index) -> str`** —
   the mechanical predicate above, given already-computed positions/zone-membership/
   zone-order lookups.
2. **`classify_connections(tree: DomainTaskTree) -> Dict[Tuple[str, str], str]`** — calls
   `compute_stage_zones(tree)`, builds the `node_to_zone`/`zone_index` lookups from its
   result plus `_atomic_steps_by_layer`, then classifies every real `(dependency_id,
   dependent_id)` pair drawn from each Atomic step's own `requires` list.

## Test (`tests/test_engineering_decomposition.py`)

1. `classify_connections` on a 3-Layer fixture (each layer single-row, small step counts):
   confirms `adjacent` (consecutive same-row dependency), `local_branch` (same-row
   dependency skipping a column), `cross_stage` (dependency crossing exactly one Layer
   boundary), and `long_distance` (dependency crossing two Layer boundaries).
2. `_classify_one` tested directly against hand-built position/zone dicts for
   `row_transition` (row+1) and `cross_row` (row+3) — building a real 11+/21+-step tree
   fixture just to reach those row indices naturally would be disproportionate to what the
   test needs to prove.

## Commit

One commit: "Add connection classification to the Node Mapper (CR18, sub-plan 10a-ii)."

## Status

- [x] Built — `_classify_one`, `classify_connections` in `backend/render/node_mapper.py`.
- [x] Tested — 2 new tests (4 categories via a real 3-Layer tree fixture; row_transition/cross_row via direct `_classify_one` calls against hand-built position data), both passing.
- [ ] Committed
