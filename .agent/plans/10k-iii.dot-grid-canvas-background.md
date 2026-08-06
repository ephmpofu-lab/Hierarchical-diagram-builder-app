# Plan 10k-iii: Dot-Grid Canvas Background

**Complexity: Simple.** CSS-only, one new wrapper element. Second of 10k's four sub-plans
(built out of the plan's own numeric order, iii before ii/iv, per the confirmed sequencing:
i -> iii -> iv -> ii).

## Requirement

`docs/ARCHITEQ-n8n-Canvas-Complete-Spec.md` 1.7 — a subtle dot-grid background, present in
every canvas state (loading/error/populated, both Python and n8n modes), signaling a
pannable surface. Confirmed absent entirely before this plan (no `dot-grid`/`radial-gradient`
anywhere in `style.css`).

## Scope decisions

1. Exact geometry read from `reference/architeq-ux-mockup.html`'s own `.tree-scroll` rule:
   `radial-gradient(circle, <color> 1px, transparent 1px)`, `background-size: 22px 22px`.
2. Color NOT copied literally: the mockup's own `#202226` is tuned against its own darker
   `--bg` (`#0B0C0F`); this app's real `--bg` is lighter (`#161616`). Used the existing
   `--surface-2` token instead (a similarly subtle step up from `--bg`) — geometry copied
   exactly, color kept on an existing token, per the standing "no new color system" rule.
3. Scoped to the canvas body specifically, not the whole page — the Home screen's intent
   input isn't a pannable surface and the dot-grid shouldn't imply it is. `renderCanvasView`
   didn't have a single wrapper for its own body content (everything appended directly to
   the shared `decomposeBoard`); added one (`.decompose-canvas-body`), which every existing
   canvas element (refine bar, tree diagram, mode toggle, output section, detail panels)
   now renders into instead of `decomposeBoard` directly. Detail panels are fixed-position
   overlays, unaffected by the new wrapper (no `overflow`/`transform` added to it).

## Build

- `static/js/decompose.js`, `renderCanvasView`: new `canvasBody` div
  (`.decompose-canvas-body`), appended once to `decomposeBoard` right after the topbar;
  every subsequent append target changed from `decomposeBoard` to `canvasBody` (refine bar,
  error state, loading state, tree diagram, mode toggle, output section, both detail
  panels).
- `static/css/style.css`: `.decompose-canvas-body` background-image/background-size.

## Test

Real screenshot of the served app's canvas view (both the tree-diagram/loading state and
the populated n8n view), per DP14: dot-grid visible as a subtle background texture. DOM
query confirms `.decompose-canvas-body` exists and contains the tree diagram, mode toggle,
and output section (i.e. the restructure didn't drop any existing element). Full pytest
suite (no backend touched, expect unchanged pass count).

## Commit

One commit, then a second flipping this file's own Committed checkbox.

## Status

- [x] Built — `.decompose-canvas-body` wrapper introduced in `renderCanvasView`, every
  canvas element now renders into it instead of `decomposeBoard` directly.
  `radial-gradient(circle, var(--border) 1px, transparent 1px)`, `background-size: 22px
  22px` (exact mockup geometry). Color switched from an initial `--surface-2` attempt
  (confirmed via a real zoomed screenshot to be genuinely invisible against this app's own
  closer bg/surface-2 pairing, not just subtle) to `--border` (confirmed visible, still
  subtle, in a second real screenshot) — a real mid-build correction, not guessed right the
  first time.
- [x] Tested — DOM query confirms `.decompose-canvas-body` contains the mode toggle and
  tree diagram (restructure dropped nothing); computed `backgroundImage`/`backgroundSize`
  match exactly; two real screenshots (before/after the color fix) prove the dot pattern is
  actually visible, not just present in the DOM. Full pytest suite green (443 passed after
  this sub-plan's own commit -- one pre-existing self-referential test updated for Module
  10's honest current state, same established pattern, not a regression).
- [x] Committed
