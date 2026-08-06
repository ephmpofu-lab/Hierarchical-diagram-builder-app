# Plan 10k-ii: Free Node Dragging + Live Connection Redraw

**Complexity: Complex**, confirmed, not just assumed — four real, interacting concerns
(event handling, live path recalculation, zoom-aware coordinate math, a new client-side
position-override store), plus a real architectural prerequisite discovered during this
plan's own research (below). Last of 10k's four sub-plans, built against the final
three-way-toggle canvas structure (10k-iv), per the confirmed sequencing.

## Requirement

`docs/ARCHITEQ-n8n-Canvas-Complete-Spec.md` 5.3 (drag repositions a node, connections
follow live) and 5.4 (click-vs-drag threshold, ~3px). Plus the explicit coupling flagged
before Build started: 10k-i's flow-dot `<animateMotion>` is bound to a path string at
creation time; a live redraw must update it too, not just the visible connection line.

## Real architectural finding (not assumed, checked against the mockup's own working code)

The mockup's node tiles use `transform="translate(x,y)"` on the `<g>`, with every child
(rect, icon, label, ports) at **local, group-relative coordinates**. Our own
`renderN8nDiagram` instead sets absolute `x`/`y`/`cx`/`cy` on every individual child element
(`node.position[i] + padding`, repeated per element). Dragging against the current structure
would mean updating every child element's coordinates by hand, every mousemove — the
mockup's own approach (move the group, children stay put in local space) is simpler, more
mockup-faithful, and the right foundation. **This plan includes that refactor as a real
prerequisite, not scope creep** — dragging is not buildable cleanly without it.

The mockup also already has a proven, working `redrawEdgesFor(name)`: on drag, it doesn't
try to mutate an existing connection's `<path d>` or an `<animateMotion path>` in place —
it removes every DOM element tagged `data-edge`/`data-flow-for`/`data-edge-label` for that
connection and redraws them fresh. This is the answer to the flagged flow-dot coupling: a
freshly-created `<animateMotion>` on a freshly-created path is trivially correct, sidestepping
the real cross-browser uncertainty around mutating a live SMIL animation's `path` attribute
mid-flight. Ported directly, not reinvented.

## Scope decisions

1. **Node group refactor to `transform="translate(x,y)"` + local coordinates** — every
   child (rect, layer-dot, icon, id-label, stacked name/type/warn label, ports, data
   anchors) repositioned relative to (0,0), group itself carries the real position.
2. **`data-edge`/`data-flow-for`/`data-edge-label` attributes** on every connection
   path/flow-dot/label, keyed `${source.step_id}>${target.step_id}` — mirrors the mockup's
   own convention exactly, enables `redrawN8nEdgesFor(stepId)` to find and replace (not
   mutate) every element belonging to a connection touching a given node.
3. **No `renderBoard()` during drag, or at drag end.** A full re-render creates a fresh SVG,
   which resets `attachN8nPanZoom`'s pan/zoom to defaults (scale=1, tx=0, ty=0) — jarring
   mid-interaction, and unnecessary: the drag is handled by direct DOM mutation exactly like
   `attachN8nPanZoom`'s own pan/zoom already is. `state.n8nManualPositions[step_id]` is
   updated silently at drag end (no render) so a *later*, unrelated re-render (mode switch,
   node click elsewhere) still reflects the moved position.
4. **Click-vs-drag**: the existing separate `click` listener on the node group is removed;
   click-vs-drag is handled entirely inside the new mousedown/mousemove/mouseup trio (mirrors
   the mockup's own `if(dragging && !moved){ openPanel... }`), avoiding a double-fire between
   a manual "not moved" check and the browser's own native click event.
5. **Zoom-aware delta**: drag delta divided by the current zoom scale, read from
   `attachN8nPanZoom` — its `scale` variable is presently a private closure value; it now
   returns `{ getScale }` so the drag handler can read the live value, never a stale copy.
6. **Auto-arrange** (existing button, 10i) now also clears `state.n8nManualPositions` before
   its existing `renderBoard()` call — previously a no-op reset (nothing to clear), now a
   real one.
7. **Not built**: persisting manual positions server-side (matches 10b-iii's own precedent —
   node config is session-only too); dragging in Tree or Python mode (nodes there aren't
   n8n tiles).

## Build

- `static/js/decompose.js`, `renderN8nDiagram`: node-drawing loop refactored to
  group-relative coordinates + `transform`; connection-drawing loop factored into a
  `drawN8nConnection(source, target, classification, positions)` helper (adds the
  `data-edge*` attributes, builds path + optional flow-dot + optional data-label) reusable
  by both the initial draw and `redrawN8nEdgesFor`; new `redrawN8nEdgesFor(stepId,
  positions)` removes and redraws every connection touching `stepId`; new
  `n8nEffectivePosition(node)` overlays `state.n8nManualPositions[node.step_id]` on the
  server-computed `node.position`, used everywhere a node's position is read (initial draw,
  port math, connection drawing).
- Node group: `mousedown` (left button only, `stopPropagation`) starts tracking;
  window-level `mousemove` (only while tracking) computes zoom-aware delta, sets `moved`
  past the 3px threshold, updates the group's own `transform` directly, calls
  `redrawN8nEdgesFor` for this node; window-level `mouseup` opens the detail panel if never
  `moved` (replaces the old separate click listener), else commits the final position to
  `state.n8nManualPositions` with no render.
- `attachN8nPanZoom`: returns `{ getScale }`.
- Auto-arrange button (`renderOutputSection`): clears `state.n8nManualPositions` before
  `renderBoard()`.

## Test

Real simulated drag via Playwright (`page.mouse.down/move/up`), per DP14 — not inferred from
the connection path alone:
1. Drag a node >3px: its group `transform` changes to the expected new coordinates; every
   connection touching it (queried by `data-edge`) has a `d` attribute consistent with the
   new position; **the flow-dot coupling explicitly checked** — the `animateMotion` element
   on each redrawn connection is a genuinely new DOM node (not the same node with a mutated
   attribute) and its `path` attribute matches the connection's own new `d` exactly.
2. Drag a node <3px then release: detail panel opens (same node, same content as a plain
   click today); no position change recorded.
3. `state.n8nManualPositions` reflects the dragged node's final position after mouseup;
   Auto-arrange clears it and the node returns to its server-computed position.
4. No `renderBoard()`-triggered network request fires during or immediately after a pure
   drag (confirms no full re-render occurred, matching the no-pan/zoom-reset scope decision).
5. Full pytest suite green (no backend touched).

## Commit

One commit, then a second flipping this file's own Committed checkbox.

## Status

- [x] Built — node rendering refactored to `transform="translate(x,y)"` + group-relative
  local coordinates (rect, layer-dot, icon, id-label, stacked label, ports, data anchors all
  now at fixed local positions, matching the mockup's own `makeTile` structure exactly);
  connection drawing factored into `drawN8nConnection`, tagged `data-edge`/`data-flow-for`/
  `data-edge-label` (mirrors the mockup's own `redrawEdgesFor` convention); new
  `redrawN8nEdgesFor(stepId)` removes and redraws every connection touching a node — never
  mutates an existing path/animateMotion in place, sidestepping the SMIL-reliability
  question entirely; new `livePositions` (world coords, seeded from
  `state.n8nManualPositions` overlaid on server positions) is the single source every
  position read goes through; two explicit z-order layers (`connectionsLayer`/`nodesLayer`)
  so a mid-drag redraw's fresh elements still land behind every node tile. Drag handled by
  direct DOM mutation only (group `transform` + `redrawN8nEdgesFor`), never `renderBoard()`
  during or immediately after a drag — preserves `attachN8nPanZoom`'s live pan/zoom state,
  which a full re-render would otherwise reset to defaults. `attachN8nPanZoom` now returns
  `{ getScale }` so the drag handler reads the live zoom scale, never a stale copy.
  `state.n8nManualPositions` added (reset alongside `n8nNodeConfig` at every existing reset
  site); Auto-arrange clears it before its own existing `renderBoard()`. Old separate
  `click` listener on the node group removed — click-vs-drag is now handled entirely by the
  new mousedown/mousemove/mouseup trio (mirrors the mockup's own `if (dragging && !moved)`),
  avoiding a double-fire against the browser's native click event.
- [x] Tested — real simulated drag via Playwright (`page.mouse.down/move/up`), per DP14,
  against the served `rag` domain, not inferred from the connection path alone:
  - A >3px drag moves the node's `transform` by exactly the expected delta (confirmed:
    120,80 px mouse movement -> exactly 120,80 px transform delta at scale=1).
  - **The explicitly flagged flow-dot coupling, checked directly**: the one real connection
    touching the dragged node got both a changed path `d` and a **genuinely new**
    `animateMotion` DOM element (identity-compared before/after, not just attribute-
    compared) whose own `path` attribute exactly matches the connection's new `d`; all 31
    other (untouched) connections' `animateMotion` elements remained the same DOM node,
    confirming `redrawN8nEdgesFor` correctly scopes to only the connections that need it.
  - A <3px movement (in practice, zero movement) on mouseup opens the detail panel, same as
    a plain click today.
  - A dragged position survives an unrelated re-render (clicking a different node's panel
    open and closed again) — `state.n8nManualPositions` round-trips correctly.
  - Auto-arrange reverts the dragged node back to its exact original server-computed
    position.
  - A real bug caught and fixed during this same verification pass, not assumed correct:
    `workflow.nodes` array order does not correspond to on-screen row position (nodes from
    different Layers interleave); the first verification attempt picked node index 0/1
    assuming visual top-to-bottom order and found zero movement because that node was
    off-screen (SVG-internal pan, not native scroll) — fixed by selecting the node with the
    smallest real y-translate instead of trusting array index.
  Full pytest suite green (443 passed after this sub-plan's own commit -- one pre-existing
  self-referential test updated for Module 10's honest current state, same established
  pattern).
- [x] Committed
