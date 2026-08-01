# Plan 10b-ii: Detail Panel Click Wiring

**Complexity: Simple.** Frontend-only, reuses the already-built `renderNodeDetailPanel`
(`decompose.js:461`) verbatim — it already renders an n8n node's `type`/`parameters` as
read-only JSON when `state.mode === "n8n"` and `state.selectedNodeId` is set; nothing on the
n8n canvas currently sets that state. This is wiring, not new panel construction. Proceeds
through Build/Test/Commit per the Autonomy Default.

## Requirement

Part of `10b.n8n-node-tile.md`: "detail panel wiring." Clicking any n8n canvas node should
open the same slide-in detail panel the Tree Diagram's nodes already open.

## Scope decisions

1. **Reuses the existing `onAtomicClick`-style pattern** the Tree Diagram already uses
   (`renderTreeDiagram(tree, (nodeId) => { state = {...state, selectedNodeId: nodeId};
   renderBoard(); })`, `decompose.js:417`) — a click listener on each n8n node's `<g>` group
   that does the exact same state update, keyed by `node.step_id` (the real `TaskTreeNode`
   id `renderNodeDetailPanel` already looks up via `state.tree.nodes[state.selectedNodeId]`).
   No new panel, no new state shape.
2. **Click listener added to the same `<g>` group that already carries the hover
   listeners** (10a-iii) — one element, both interactions, no separate hit-target needed.

## Build (`static/js/decompose.js`)

`renderN8nDiagram`'s per-node loop: `group.addEventListener("click", () => { state = {
...state, selectedNodeId: node.step_id }; renderBoard(); });`.

## Test

Standalone Playwright harness (same fixture as 10a/10b-i, extended with a minimal
`state`/`renderBoard`/`renderNodeDetailPanel` stub sufficient to observe the click's state
update): dispatch a click on one node's `<g>` group, confirm `state.selectedNodeId` becomes
that node's `step_id`. Zero JS console errors.

## Commit

One commit: "Wire n8n canvas node clicks to the existing slide-in detail panel (sub-plan 10b-ii)."

## Status

- [x] Built — click listener added to each n8n node's `<g>` group, sets
  `state.selectedNodeId = node.step_id` and calls `renderBoard()`; `.decompose-n8n-node-
  group` class added for `cursor: pointer` styling.
- [x] Tested — standalone Playwright harness: clicking a node's group transitions
  `state.selectedNodeId` from `null` to that node's real `step_id`, zero JS errors.
- [x] Committed
