# ARCHITEQ — n8n Canvas: Complete Specification

Reconstructed from every decision made building and correcting `reference/architeq-ux-mockup.html` across this project's full history. This is the definitive reference for the n8n canvas specifically — not a summary, a checklist. Every item traces to either a rule ID (CR/NT) already in the corpus, or a specific correction made after something was shown to be wrong. Nothing here is aspirational; all of it exists, working, in the reference file.

---

## 1. LAYOUT — how nodes are positioned

1.1. **Stage zones allocated first, non-overlapping by construction (CR15).** Each top-level stage (Ingestion, Preprocessing, Embedding, ...) gets its own vertical zone computed *before* any node is positioned — stacked sequentially with a running vertical cursor. A row never spans two stages. If a stage has more nodes than the row cap, both its rows still belong entirely to that stage's zone, never bleeding into a neighbor's.

1.2. **Primary direction is left to right within each stage's own zone (CR3, amended).** CR3's original text ("a row may span multiple stages") is wrong and superseded — see CR15. Within one stage's zone, its nodes read left to right in dependency order.

1.3. **Row cap: ~9-10 nodes per row (CR4).** When a single stage's node count exceeds this, wrap to a second row inside that same stage's zone. Never reverse direction on a wrapped row (no snake layout).

1.4. **Branch nodes drop locally beneath their source (CR8), not into a dedicated row.** A branch (e.g. `Handle Unsupported Format` off `Validate File Type`) sits a short, fixed vertical offset below its source node, in the same column — never pushed into a separate row or past unrelated stages to reach it.

1.5. **Stage background boxes**, one per zone: subtle tinted fill (~5% opacity) + a 1px border in the stage's own layer color, rounded corners, a label top-left reading `STAGE — INGESTION` (etc.) in that same color.

1.6. **Row-count debug text is NOT shown in the production view** (rules 17-18 of the routing-correction spec) — "Row 1: 9 nodes (within 9-10 limit)" style badges are development-only annotations, removed from what a user actually sees. The 9-10 cap is still enforced in the layout math; only its visible text label was removed.

1.7. **Canvas surface: a subtle dot-grid background** — small dots on a fixed pixel spacing across the entire scrollable canvas area, low contrast against the dark background, present in every state (empty, populated, both modes) — the visual cue that this is an infinite/pannable surface, not a fixed page.

1.8. **Auto-arrange button** resets any manually dragged node back to the computed layered position (grounded in the Sugiyama layered-graph-drawing method — hover tooltip on the button states this explicitly). Click it after dragging nodes around and everything snaps back to the canonical layout.

---

## 2. NODE APPEARANCE — what a single tile looks like

2.1. **Shape: rounded-square icon tile**, not a text-only box. Matches real n8n's own node visual grammar (verified against a real n8n screenshot supplied mid-session), not invented.

2.2. **Real icon per node type** — a distinct glyph for each real n8n node: lightning bolt (Webhook Trigger), pencil (Set), branch/diamond glyph (IF), floppy disk (Read/Write File), document (Extract From File), red circle-minus (Stop and Error), folder (Google Drive), globe (HTTP Request), notebook (Notion), sparkle/asterisk (OpenAI), keyboard (Code fallback).

2.3. **Two-line label underneath the tile, not inside it:**
   - Line 1: display name, `Verb Object` pattern (e.g. "Read File Bytes") — never a generic default like `Set1`. No stage/layer suffix (CR12 — corrected from an earlier version that appended `— Layer`, since the stage box already shows that context).
   - Line 2: the *real* n8n node type (e.g. `Read/Write File`), shown as a distinct, separately-styled line — never merged into line 1, never an invented/approximate node name (NT10, CR11).
   - Line 3, *only when the node is unconfigured*: `⚠ needs setup` in warning-amber — a genuinely separate line, never replacing line 2's real node type (the "warnings must not replace node types" correction).

2.4. **Ports**: a small circle on the left edge (input) and right edge (output) of every tile — visible, not merely implied by proximity (CR7).

2.5. **Needs-config state**: dashed amber border on the tile itself, distinct from the normal solid border — visible on the canvas directly, not only inside the detail panel.

2.6. **Small Node-ID label above each tile**: `WF01:N03` style — Workflow ID *and* Node ID together, always, never Node ID alone (a node name/position could recur across workflows).

2.7. **Compact per-node layer-color indicator**: a small colored dot in the tile's top-left corner, matching that node's stage color — the replacement for an earlier full-row background band that became invalid once rows stopped aligning 1:1 with stages.

2.8. **Data anchor badges beneath the label**, for any node that touches persistent data — e.g. `D02 WRITE`, `D02 READ` / `D03 WRITE` stacked — shown by default whenever the canvas is in Workflow layer mode, **not gated behind clicking into Data mode first.**

---

## 3. CONNECTIONS / EDGES

3.1. **Rounded orthogonal routing, not sweeping Bézier arcs (CR5, corrected mid-session).** An earlier version of this rule required smooth curves everywhere; that produced a large diagonal sweep whenever a cross-stage connection's source and target columns were far apart. Corrected: horizontal + vertical segments, every direction change softened by one consistent corner radius (14px), applied identically across the whole canvas. No sharp 90° elbows either — corners are rounded, not hard.

3.2. **Same-row adjacent nodes: a plain straight line**, no curve, no corner — the simplest, strongest connection on the canvas (rule 3 of the routing-correction spec).

3.3. **Cross-stage / row-transition connections route through the whitespace lane between zones** — exit the source's right port, drop into the lane, travel across, approach the target's **left port** (never top or bottom — a node's visual position on the canvas never changes its real input-port semantics; this was an explicit bug fix, an earlier version entered via the top edge).

3.4. **Solid vs. dashed = routing behavior, not "executable vs. not."** Adjacent same-row and local branch connections are solid. Cross-stage/routed connections are dashed — but dashed never means weaker or less real; it's the *same* execution relationship, just visually marked as having been routed through whitespace.

3.5. **Branch connections are amber/warning-colored, not red** (red is reserved for the error node's own icon, not its connecting line) — solid, not dashed (corrected from an earlier dashed treatment).

3.6. **Primary-path connections keep full visual weight even when dashed for routing** — a cross-stage connection that's part of the main sequence is NOT visually demoted just because it crosses a stage boundary. (Corrected from an earlier bug where all cross-row connections were rendered in a faint neutral color regardless of whether they were primary or secondary.)

3.7. **Animated flow — a small pulse travels continuously along every primary-path edge**, direction of travel matching execution order. Branch/secondary edges are not animated.

3.8. **Arrowheads** at the terminating end of every connection, colored to match that edge's semantic color (accent for primary, amber for branch).

3.9. **Connection data labels** (the actual field name passed — `source_scope`, `upload_config`, `raw_file_object`, etc.) appear directly on primary-path edges, small monospace text, muted to ~55% opacity — present but never visually competing with node names (the "connection data labels must be secondary" correction).

3.10. **No connection ever passes through an unrelated node or its label** — routing goes around, through reserved lane whitespace, never straight through.

---

## 4. CONTROLS / TOP BAR

4.1. **Mode toggle: `Python | n8n | Tree`**, three options, styled as one connected pill (rounded container, active option highlighted with accent background) — **DECISION, corrected from the original two-option version and from `ARCHITEQ-APP-FLOW.md:66`'s "tree diagram always visible" spec**: the Layer/Sub-task/Atomic-step hierarchy tree is not stacked permanently above the n8n canvas. It becomes its own selectable third mode, same as Python and n8n. Selecting it shows the tree, full-canvas, alone — not layered with anything else. This supersedes the App Flow doc's earlier instruction; update that doc to match once this is built, per DP12.

4.2. **Layer toggle: `Workflow | Data`**, same pill styling as the mode toggle, positioned next to it — **visible only when in n8n mode**, hidden entirely in Python mode.

4.3. **Colored layer legend**, one dot + label per stage present in the tree (e.g. `● Ingestion  ● Preprocessing  ● Embedding`) — visible in both Python and n8n modes.

4.4. **Auto-arrange button.**

4.5. **Export button** — triggers a confirmation toast naming what was produced (`architeq_rag/` module folder in Python mode, `rag_workflow.json` in n8n mode). Simulated in the mockup; real output is a separate backend concern.

4.6. **Breadcrumb** top-left: domain name + short description of the current decomposition.

---

## 5. INTERACTIONS

5.1. **Middle-mouse-button drag pans the canvas** (AutoCAD/Figma convention) — not a scrollbar as the primary navigation method. Regular scrolling still works as a fallback.

5.2. **Scroll wheel zooms in/out, centered on the cursor position** — not on the canvas origin. The scrollable container's actual size is resized to match the zoomed content (a real bug: an earlier CSS-transform-only version left the scrollable range mismatched with what was visually zoomed, making parts of the canvas unreachable).

5.3. **Left-click-drag on a node repositions it** — connections follow live, redrawn in real time as you drag. Node drag math divides mouse-pixel deltas by the current zoom level (a real bug: dragging while zoomed moved nodes at the wrong speed relative to the cursor before this fix).

5.4. **Click (not drag) on a node opens the detail panel.** Click vs. drag disambiguated by a small movement threshold (~3px) — moving less than that on mouseup counts as a click, more counts as a drag.

5.5. **Hover (desktop) shows a compact tooltip** — display name, real node type, one-line description, ready/needs-setup status, and a JSON payload preview of what that step actually passes forward — without opening the full panel. Click still opens the full editable panel. This split exists because touch devices can't hover at all — click/tap is the interaction that always works everywhere; hover is a desktop-only bonus, never required to reach any functionality.

5.6. **The detail panel auto-retracts after ~7 seconds of no interaction inside it** — any mousemove, keydown, or click within the panel resets the timer. Manually closing it also stops the timer.

5.7. **In Data layer mode, clicking a table opens the same detail panel** (repurposed), showing its attributes, PK/FK, a clickable "Used By" list of nodes, and a click-to-reveal SQL view. Clicking a "Used By" entry switches back to Workflow layer and opens that node's own panel — bidirectional navigation between the two layers.

---

## 6. DATA ARCHITECTURE LAYER (n8n mode only)

6.1. **One canonical data model** — table definitions (attributes, types, PK/FK, relationships) authored once; the ERD boxes, the generated SQL, and the node data-anchor badges all derive from that single definition, never independently authored (the "SQL must come from the same data model" requirement).

6.2. **Workflow layer active (default):** data anchors shown compactly under relevant nodes (`D02 WRITE`, etc. — see 2.8). No ERD visible.

6.3. **Data layer active:** prominence reverses. The workflow becomes a faint (~16% opacity), non-interactive underlay showing real Workflow/Node IDs — not a decorative unrelated diagram. The ERD tables render at full prominence, in their **own independent layout** (a vertical relationship-driven chain — `documents → document_chunks → embeddings`), positioned in a dedicated area, never copying the workflow's row/column positions.

6.4. **ERD connectors**: rounded orthogonal routing (same corner-radius system as the workflow layer, 3.1), labeled with cardinality (`1:N`).

6.5. **Cross-layer relationship lines are not permanently drawn** between the faint workflow underlay and the ERD — they exist as data (the anchor mapping) but are only meant to visually connect on hover/select, fading when deselected, to avoid spaghetti at scale. *(Flagged as a partial implementation — the mockup demonstrates the click-to-detail path; full hover-reveal-then-fade line-drawing between layers was not built.)*

---

## 7. WHAT WAS TRIED AND EXPLICITLY REJECTED — do not reintroduce

7.1. **A visible minimap** — built, then explicitly removed at direct request ("remove the navigation map, not necessary"). Do not add one back without being asked again.

7.2. **A persistent navigation rail/sidebar** (Home/Recent/Settings icons) — built, repeatedly failed to read as intentional, removed entirely. UI11 in the rules corpus is marked superseded, not deleted, specifically to record this so it isn't rebuilt by mistake.

7.3. **Hard right-angle elbow connectors** — an intermediate version of the routing system, superseded by rounded orthogonal (3.1). Do not implement plain sharp-cornered polylines.

7.4. **Uniform smooth Bézier curves everywhere** — the version before 7.3, also superseded. Two rounds of correction happened on connection geometry; rounded orthogonal (3.1) is the final, current answer.

7.5. **Row-transition connections that compare horizontal vs. vertical distance to choose a curve shape** — this specific formula produced the large diagonal sweep bug. The fix is a fixed lane-routing waypoint path, not a smarter curve-shape heuristic.

---

## Cross-reference

Every numbered item above that cites a rule ID (CR1-18, NT1-10) is checkable against `rules/principles/n8n-canvas-rules.md` and `rules/principles/node-translation.md` directly — if this document and those files ever disagree, treat it as a DP12 cross-reference failure and flag it, don't silently pick one.
