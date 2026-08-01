# Plan 10a-iv: Pan + Zoom (Canvas Foundation, final piece)

**Complexity: Medium.** Frontend-only (`decompose.js`/`style.css`), self-contained
interaction layer independent of 10a-i/ii/iii's layout/routing logic. No backend change.
Proceeds through Build/Test/Commit per the Autonomy Default.

## Requirement

Part of `10a.canvas-foundation.md`: "Middle-mouse-drag pan, cursor-centered scroll-wheel
zoom, on the n8n canvas SVG."

## Scope decisions

1. **A single `<g class="decompose-n8n-viewport">` wraps all drawn content** (stage zones,
   connections, nodes) inside the existing `renderN8nDiagram`'s `<svg>` — pan/zoom then
   only ever mutates one `transform` attribute on that group, never touches the individual
   zone/connection/node elements it already builds.
2. **The outer `<svg>`'s width/height become a fixed, capped viewport**
   (`min(totalWidth, 1100)` / `min(totalHeight, 640)`) instead of the full content extent —
   a real behavior change from 10a-i/ii/iii's sizing (which always showed the whole tree via
   the wrap's native horizontal scrollbar). This is the actual point of adding pan/zoom: a
   wide/tall tree is explored by dragging and scrolling the wheel, not by a scrollbar.
   `.decompose-n8n-diagram-wrap`'s CSS changes from `overflow-x: auto` to `overflow: hidden`
   to match — the SVG itself is now the pannable surface.
3. **Zoom keeps the point under the cursor stationary** (the standard "zoom to point"
   transform: convert cursor position to current world-space coordinates, apply the new
   scale, then solve for the translate that keeps that same world point under the cursor)
   — not a "zoom to center" that would otherwise drift the diagram away from where the user
   is actually looking.
4. **Middle-mouse only for pan** (`event.button === 1`), matching the requirement's own
   wording — left-click stays free for a future node-selection interaction (out of scope
   here), and `preventDefault()` on `mousedown` suppresses the browser's native middle-click
   autoscroll icon.
5. **Scale clamped to `[0.2, 3]`**, fixed constants matching this codebase's standing
   fixed-constant posture (`MAX_ATOMICITY_SPLIT_DEPTH`, `_MAX_NODES_PER_ROW`, etc.) — not
   configurable, revisited only if it proves limiting.

## Build (`static/js/decompose.js`, `static/css/style.css`)

1. **`attachN8nPanZoom(svg, viewport)`** — wires `mousedown`/`mousemove`/`mouseup`/
   `mouseleave` (middle-mouse drag) and `wheel` (cursor-centered zoom) listeners onto `svg`,
   mutating `viewport`'s `transform` attribute.
2. **`renderN8nDiagram`** — every element it currently appends to `svg` directly now appends
   to a new `viewport` group instead; `svg`'s width/height/viewBox become the capped
   viewport size; `attachN8nPanZoom(svg, viewport)` called before returning.
3. **`style.css`** — `.decompose-n8n-diagram-wrap` changes to `overflow: hidden`; new
   `.decompose-n8n-diagram` cursor styling (`grab` at rest, nothing needed for `grabbing`
   since it's a transient state toggled inline during drag, not a persistent CSS class worth
   adding for one small interaction).

## Test

Standalone Playwright harness (same pattern as 10a-iii, reusing the same fixture): after
`renderN8nDiagram` returns, dispatch a synthetic `wheel` event (zoom in) and confirm the
viewport's `transform` scale increased and the translate shifted to keep the cursor point's
world coordinate fixed (recomputed and compared); dispatch a synthetic middle-mouse
`mousedown`/`mousemove`/`mouseup` sequence and confirm the translate changed by exactly the
drag delta. Zero JS console errors in either case.

## Commit

One commit: "Add pan (middle-mouse drag) + zoom (cursor-centered scroll-wheel) to the n8n canvas (sub-plan 10a-iv)."

Once this lands, **Module 10a (Canvas Foundation) is fully complete** (10a-i through 10a-iv).

## Status

- [x] Built — `attachN8nPanZoom` in `decompose.js`; `renderN8nDiagram` now wraps all drawn
  content in a `.decompose-n8n-viewport` group and calls it; SVG width/height capped to a
  viewport size instead of full content extent; `.decompose-n8n-diagram-wrap` changed to
  `overflow: hidden`, `.decompose-n8n-diagram` gets `cursor: grab`.
- [x] Tested — standalone Playwright harness (reusing 10a-iii's fixture): synthetic
  cursor-centered wheel zoom confirmed scale increased and translate solved exactly per the
  zoom-to-point formula (`-20, -20` at scale 1.1 for a cursor at (200,200), matching by
  hand); synthetic middle-mouse drag (500,400) -> (560,440) confirmed the translate shifted
  by exactly the drag delta (60, 40) on top of the zoom's translate; zero JS console errors;
  screenshot confirms the diagram visibly shifted/scaled.
- [x] Committed
