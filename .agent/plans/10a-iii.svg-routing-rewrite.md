# Plan 10a-iii: SVG Routing Rewrite (CR2, CR5, CR6, CR7, CR16)

**Complexity: Complex** (the largest of 10a's four pieces, flagged honestly rather than
under-rated) — a real path-routing algorithm, port rendering, and stage-zone backgrounds,
touching both a small backend wiring addition and a substantial frontend rewrite. Proceeds
through Build/Test/Commit per the Autonomy Default, since it's already one scoped item
inside the 4-way 10a breakdown the user already confirmed — not re-pausing for a second
confirmation on top of that one, but split into two build passes internally (backend wiring
first, then the frontend rewrite) so the frontend work has real classified data to render
against from the start.

## Requirement

Part of `10a.canvas-foundation.md`. Per `rules/principles/n8n-canvas-rules.md`:
- CR7: every node shows a visible input and output port; every connection's endpoints
  coincide exactly with a specific port.
- CR5: same-row adjacent edges render as a single straight line; every other edge renders
  as an orthogonal waypoint path with one consistent rounded-corner radius, never a Bézier
  arc, never a sharp elbow.
- CR6: routing uses whitespace lanes, never passes through an unrelated node's bounding box.
- CR16: a routed connection always enters the target through its normal left input port,
  never an arbitrary top/bottom anchor.
- CR2: stage/layer groupings are rendered as visual-only backgrounds; a connection is never
  anchored to a stage boundary itself.

## Key finding that simplifies backend wiring

Confirmed by direct read: `decompose.js::downloadWorkflowJson` already does
`const exportable = { name: workflow.name, nodes: workflow.nodes, connections:
workflow.connections }` before building the download blob — it already explicitly
whitelists exactly 3 fields and discards everything else on the fetched object. This means
adding new fields directly onto `N8nWorkflow` (rather than a second endpoint + a second
frontend fetch/state slot, as originally sketched in 10a-i's own scope decision 1) is safe:
the real, downloaded `workflow.json` stays exactly the 3-field shape R14 requires, with zero
extra plumbing needed. Revises 10a-i's stated intention for *how* stage-zone data reaches
the frontend — not a re-litigation of *what* the data is (still a rendering-only concern,
still computed once in `node_mapper.py`, never duplicated).

## Scope decisions

1. **`N8nWorkflow` gains `stage_zones: List[N8nStageZone]` and
   `connection_classifications: List[N8nConnectionClassification]`** (new small model:
   `source_step_id`, `target_step_id`, `classification`), populated by `export_workflow`
   from 10a-i/10a-ii's existing `compute_stage_zones`/`classify_connections` — no new
   endpoint, no new frontend fetch.
2. **A generic rounded-polyline path helper**, not six hand-written path-string builders —
   `roundedPolylinePath(points, radius)` takes any ordered waypoint list and inserts one
   quadratic-curve rounded corner per interior point (a standard, well-known technique:
   shrink each adjacent segment by the corner radius, `Q` through the true corner point).
   Every classification only needs to supply *waypoints*; the rounding/geometry itself is
   one shared function, matching this codebase's standing "one shared computation, not N
   near-duplicates" discipline.
3. **Waypoint generation per classification**:
   - `adjacent` — 2 waypoints (source right port, target left port); a straight line, no
     rounding needed (CR5's own "simplest, strongest connection" case).
   - `local_branch` (same row, skips a column) — routes through a whitespace lane below the
     row (down from source, across, back up into target's left port) rather than a straight
     line that would pass through the skipped node's bounding box (CR6).
   - `row_transition`/`cross_row`/`cross_stage`/`long_distance` — a standard 4-point elbow
     (out of source's right port, vertical travel at a shared midpoint X, into target's
     left port) — CR16 satisfied by construction (every path's final waypoint is always the
     target's left port, regardless of class).
4. **Ports are small visible circles**, not a new interactive control — CR7 only requires
   visibility and exact endpoint coincidence, not click/drag behavior (that would be a
   different, not-yet-scoped node-editing capability this read-only frozen-tree canvas
   doesn't have).
5. **Stage-zone backgrounds are drawn first, behind everything**, using 10a-i's own
   `N8nStageZone.x/y/width/height` directly (already computed padding-free; the SVG applies
   the same outer `padding` constant uniformly) — a labeled `<rect>` + `<text>` per zone,
   CR2's "visual group, never an execution anchor" satisfied by construction (no connection
   ever originates/terminates at a zone element, only at node ports).
6. **Total SVG width/height now derive from the real 2-D extent of `stage_zones`**, not
   just the old single-row `maxX` — replacing that computation, since positions now vary in
   `y` per 10a-i.
7. **11g's existing hover-payload wiring is carried forward, not dropped** — the mockup/
   plan's own standing flag (`10.ui-shell-rebuild.md`'s note) is honored: the
   `mouseenter`/`mousemove`/`mouseleave` listeners move from the old plain `<rect>` to the
   new node-group element, unchanged in behavior.
8. **Verification uses the same standalone Playwright harness 11g already established**
   (serve a scratchpad dir via `python -m http.server`, copy real `style.css`/`decompose.js`
   in as `real-*`, drive `state`/`renderBoard()` directly with a hand-built fixture tree,
   screenshot) — Playwright + Chromium are confirmed installed and launchable in this
   environment (checked directly before writing this plan), so this is a real, live check,
   not a "no browser automation available" caveat.

## Build

1. **`backend/models.py`** — new `N8nConnectionClassification` model; `N8nWorkflow` gains
   `stage_zones`/`connection_classifications` fields (both default empty list).
2. **`backend/render/n8n_exporter.py::export_workflow`** — calls `compute_stage_zones` and
   `classify_connections` (10a-i/10a-ii, already built) and populates the two new fields.
3. **`static/js/decompose.js::renderN8nDiagram`** — rewritten:
   - `roundedPolylinePath(points, radius)` helper.
   - Per-classification waypoint builders (`buildAdjacentWaypoints`,
     `buildLocalBranchWaypoints`, `buildElbowWaypoints`).
   - Stage-zone background rects + labels, drawn first.
   - Node rects unchanged in position logic (now driven by real 2-D `position`), gain
     visible input/output port circles.
   - Total SVG width/height computed from `workflow.stage_zones`' real extent.
   - Existing hover-payload listeners moved onto the new node group element, unchanged
     behavior.
4. **`static/css/style.css`** — new `.decompose-n8n-stage-zone`,
   `.decompose-n8n-stage-zone-label`, `.decompose-n8n-port` rules, reusing existing theme
   tokens only (no new hardcoded colors, matching 11g's own established convention).

## Test

1. **Backend (`tests/test_engineering_decomposition.py`)** — `export_workflow` on a
   multi-layer tree populates non-empty `stage_zones` and `connection_classifications`
   matching `compute_stage_zones`/`classify_connections`'s own direct output; the existing
   `test_export_workflow_wraps_mapped_nodes_and_connections` and
   `test_render_n8n_endpoint_returns_importable_shape` stay green unmodified (additive
   fields only).
2. **Frontend (standalone Playwright harness, scratchpad-only, not committed to the repo)**
   — a hand-built fixture workflow with 2+ stage zones and at least one of each
   classification, rendered via the real `renderN8nDiagram`; screenshot-checked for: two
   visibly distinct, non-overlapping zone backgrounds; visible ports on every node; at least
   one straight-line edge (adjacent) and at least one visibly rounded/orthogonal edge
   (everything else); zero browser console errors.

## Commit

One commit: "Add SVG routing rewrite -- ports, stage-zone backgrounds, classified rounded-
orthogonal routing (CR2/CR5/CR6/CR7/CR16, sub-plan 10a-iii)."

## Status

- [x] Built — `N8nConnectionClassification` model + `N8nWorkflow.stage_zones`/
  `connection_classifications` fields; `export_workflow` populates both from 10a-i/10a-ii's
  existing functions; `renderN8nDiagram` rewritten in `decompose.js` with
  `roundedPolylinePath`, per-classification waypoint builders, stage-zone backgrounds,
  visible ports, and a real 2-D total-extent SVG size computation; new
  `.decompose-n8n-stage-zone`/`-label`/`.decompose-n8n-port` CSS.
- [x] Tested — 1 new backend test (`export_workflow` populates real stage_zones/
  classifications matching 10a-i/10a-ii's direct output); frontend verified live via the
  standalone Playwright harness (confirmed Playwright + Chromium ARE installed and
  launchable in this environment, contrary to this plan's own earlier caveat) — a 3-zone,
  5-node, 4-classification fixture rendered with 3 zone rects + 3 labels, 10 ports, 4
  correctly-classified paths, zero JS errors; screenshot visually confirms non-overlapping
  zones, straight adjacent line, and correctly rounded local_branch/cross_stage/
  long_distance routes all entering their targets' left ports.
- [x] Committed
