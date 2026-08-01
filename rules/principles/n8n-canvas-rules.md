# Rules and Principles: n8n Canvas Rendering

Part of `rules/principles/`. Governs ONLY how an architecture Architeq has already decomposed gets *represented* as an n8n canvas — node shapes, ports, connection routing, row layout, branching, naming. It does not govern decomposition, architecture generation, or domain logic; those remain governed by `decomposition.md`, `workflow-design.md`, and `component-decomposition.md`, unchanged by anything here.

Grounding for this entire file: n8n's own node-and-connection execution model, plus standard graph-drawing/diagramming convention for left-to-right directed flow. Consolidated from an 80-rule structural specification into the corpus's Statement/Grounding/Applies-to/Predicate template; nothing substantive from that specification is dropped, only regrouped.

---

## CR1 — Nodes and Connections Are the Only Executable Objects

**Statement:** A node represents an operation; a connection represents an execution/data relationship between two specific node ports. Stages, layers, and visual groupings are organizational only and are never treated as executable — a connection must never originate or terminate at a stage, a group, empty canvas space, or an arbitrary visual anchor.

**Grounding:** n8n's fundamental execution model: `NODE OUTPUT → CONNECTION → NODE INPUT`. Visual proximity alone never implies execution — an explicit connector is required wherever one step depends on another.

**Applies to:** Node Mapper, JSON Exporter, SVG Renderer.

**Predicate:**
```
every rendered connection has an explicit source node + source port and
an explicit target node + target port; no connection is anchored to a
stage/group/layer element or to unattached canvas space
```

---

## CR2 — Stages Are Visual Groups, Never Execution Gates

**Statement:** Grouping nodes into stages (e.g. by layer) is permitted for readability, but a stage boundary carries no execution meaning. When execution crosses a stage boundary, the real relationship is still node-to-node (`Last Node Stage A → First Required Node Stage B`), never `Stage A → Stage B`. Do not invent an artificial "stage transfer" node to represent a boundary crossing unless it corresponds to a real activity already defined upstream.

**Grounding:** Same source as CR1 — stage/group containers are explicitly defined as visual-only, with cross-stage connections remaining ordinary node-to-node relationships that may freely cross a stage's visual boundary.

**Applies to:** Node Mapper, SVG Renderer (swimlane/background rendering).

**Predicate:**
```
no rendered edge has a stage/group as its endpoint; connections are
permitted to visually cross stage background boundaries without
distortion or an inserted placeholder node
```

---

## CR3 — Primary Execution Direction Is Left to Right, Never Stage-Forced Vertical

**Statement:** The default and primary execution direction is horizontal, left to right. Stages/layers must never force vertical stacking as the layout mechanism (e.g. Stage 1 above Stage 2 above Stage 3). Within a stage's own zone, its nodes follow their actual execution dependency order primarily left to right.

**AMENDED — row/stage relationship corrected by CR15:** This rule's original Predicate stated that "a row may contain nodes from more than one stage, and a stage's nodes may span more than one row." That specific claim is superseded by CR15, which was written after testing this rule's original form produced overlapping and disconnected stage regions in practice. CR15 governs row-to-stage membership; CR3 governs direction-within-a-row only. Do not implement CR3's original cross-stage-row claim — implement CR15 instead. This note is kept in place, rather than silently rewritten, per this corpus's own traceability requirement (G1, G3) — the same treatment NT10 received when CR11/CR12 corrected it.

**Grounding:** Same source — horizontal is the main visual grammar; vertical or curved-away-from-row movement is reserved specifically for branches, alternate routes, and cross-row connections, not for ordinary sequential flow.

**Applies to:** Node Mapper layout computation, subordinate to CR15's stage-zone allocation.

**Predicate:**
```
within any single stage's zone, that stage's nodes are laid out left to
right in dependency order; row assignment across stages follows CR15
(each row belongs to exactly one stage's zone), not this rule's
original (superseded) cross-stage-row claim
```

---

## CR4 — Row Wrapping at Approximately 9-10 Nodes, Never Snake Execution

**Statement:** A primary horizontal row holds roughly 9-10 nodes. When exceeded, wrap to a new row — but every row reads left to right; execution direction is never reversed on alternating rows ("snake" layout is forbidden). A row break is purely a canvas-layout decision: it does not imply a new workflow, new stage, new hand-off, or any change to item flow. The actual dependency relationship between the last node of one row and the first node of the next remains a direct, real connection.

**Grounding:** Same source — the specific numeric cap and the explicit prohibition on reversed-direction rows, since reversed rows are flagged as compact but cognitively difficult to follow.

**Applies to:** Node Mapper layout computation.

**Predicate:**
```
no row exceeds ~10 nodes before wrapping; every row's node order reads
left to right; no row reverses direction relative to the row before it;
the row-transition edge still reflects the real requires/produces
dependency between the two specific nodes involved
```

---

## CR5 — Connections Use Rounded Orthogonal Routing, Not Sweeping Bézier Arcs

**Statement:** Connections consist primarily of horizontal and vertical segments, with every direction change softened by one consistent rounded corner radius applied uniformly across the whole canvas — never a large sweeping diagonal or free-form Bézier arc, and never a sharp 90-degree elbow either. Adjacent same-row nodes use a plain straight line (no curve, no corners — the simplest, strongest connection on the canvas). Local branches and cross-row/cross-stage transitions use a routed orthogonal path (exit port → rounded turn → travel through reserved whitespace → rounded turn → entry port).

**Grounding:** A dedicated routing-correction specification (superseding an earlier draft of this same rule, which required smooth Bézier curves throughout — that requirement produced large uncontrolled diagonal sweeps whenever a cross-stage connection's source and target columns were far apart, exactly the defect this correction exists to fix). The corrected requirement: horizontal + vertical + rounded corners as the standard connection geometry, one consistent corner-radius system, no diagonals, no sweeping arcs, no sharp elbows.

**Applies to:** SVG Renderer (edge path generation for all connection classes: adjacent, branch, row-transition, cross-row, cross-stage, long-distance).

**Predicate:**
```
same-row adjacent edges render as a single straight line segment;
every other edge renders as an orthogonal waypoint path where every
interior direction change uses the same corner radius; zero edges use
a smooth Bézier curve with off-axis control points, and zero edges use
an unrounded sharp corner
```

---

## CR6 — Routing Uses Whitespace Lanes, Never Passes Through Unrelated Nodes

**Statement:** Row-to-row and long-distance connections route through the whitespace reserved between rows (or, when a connection spans several rows, through the outer canvas gutter), never through the nodes of an intervening row. Connections must not pass through unrelated nodes or through node labels. Edge crossings should be minimized, and any connection that becomes visually dominant should be rerouted through a lane or gutter rather than left to dominate the canvas.

**Grounding:** Same source — sufficient vertical whitespace must be reserved above/below each row specifically for connection routing; a routing lane is invisible canvas space, never a node, stage, or workflow object in its own right.

**Applies to:** SVG Renderer (row spacing, path generation for cross-row and multi-row connections).

**Predicate:**
```
no connection's rendered path intersects the bounding box of a node it
is not connecting to; sufficient vertical gap exists between rows to
route a transition curve without touching adjacent row content
```

---

## CR7 — Every Connection Is Traceable From Source Port to Destination Port

**Statement:** A user must be able to visually follow any single connection from its source port to its destination port without ambiguity about which line it is. Connections attach visibly to ports (small, recognizable input/output points on each node) — a line must never appear merely adjacent to a node without a clear port attachment.

**Grounding:** Same source — traceability and port visibility are named as first-class requirements, distinct from mere visual proximity.

**Applies to:** SVG Renderer (port rendering, edge attachment points).

**Predicate:**
```
every node renders a visible input port and output port; every
connection's endpoints coincide exactly with a specific port, not an
approximate edge of the node's bounding box
```

---

## CR8 — Conditional Nodes Show Distinct, Correctly-Ported Outputs

**Statement:** A node with multiple real execution outputs (e.g. an IF/Switch-type node) represents each output as a separate, distinctly-labeled connection from the correct port — never collapsed into what looks like an ordinary single-path sequence. The primary/main output stays on the horizontal path; secondary/alternate outputs may curve away (down is the general preference, but not mandatory if another direction produces a cleaner result). Labels (e.g. "unsupported format", "valid"/"invalid") attach clearly to their specific output edge, not floating ambiguously between two paths.

**Grounding:** Same source — conditional branching section; branches must never be drawn from an arbitrary shared point when the underlying node genuinely has distinct output ports.

**Applies to:** Node Mapper (branch edge tagging, per WD9/NT4), SVG Renderer (branch label placement).

**Predicate:**
```
every branch edge is tagged with which specific output port it
originates from; its label is positioned unambiguously on that edge,
not equidistant between two possible paths
```

---

## CR9 — Multiple Items Are Not Multiple Branches, and Never Auto-Generate Loops

**Statement:** A single connection can carry multiple items (n8n's item-flow model) without requiring multiple edges, multiple branches, or an inserted loop node. Item multiplicity is a data-flow property; branching is an execution-topology property. These are never conflated. A loop/batching mechanism is only rendered when the underlying implementation genuinely requires one — never inserted automatically just because a step could process more than one item.

**Grounding:** Same source — explicit distinction between item flow and branching, and the explicit prohibition on automatically inserting loop nodes for multi-item behavior.

**Applies to:** Node Mapper.

**Predicate:**
```
no atomic step that merely processes multiple items in one call is
rendered as multiple parallel edges or a loop node unless its actual
implementation is iterative
```

---

## CR10 — Item Flow and Execution Continuity Survive Row and Stage Boundaries

**Statement:** Data continuity through a connection is unaffected by whether that connection happens to cross a row break or a stage boundary. Neither a row break nor a stage boundary resets, branches, or otherwise alters the underlying data/execution relationship.

**Grounding:** Same source — row breaks and stage boundaries are both defined as purely visual; the execution and item-flow semantics beneath them are identical to an equivalent connection that doesn't cross either.

**Applies to:** Node Mapper, SVG Renderer.

**Predicate:**
```
a connection's requires[]/produces[] semantics are identical whether or
not the rendered path crosses a row break or a stage/layer background
```

---

## CR11 — Display Name and Real n8n Node Type Are Shown, and Are Never Conflated

**Statement:** Every rendered node shows both its custom, purpose-describing display name (e.g. "Validate File Type") and the actual n8n node type implementing it (e.g. "IF") — displayed together, not merged into one label and not showing only one. The display name is never mistaken for, or substituted with, an invented node type name. Node type names must be the exact names n8n itself uses — never an approximate or plausible-sounding invention.

**Grounding:** Same source — explicit conceptual separation of "Architeq activity / custom display name" from "actual n8n node type," with the requirement to display both where useful, and an explicit prohibition on inventing node type names.

**Applies to:** Node Mapper, SVG Renderer (node label rendering) — this directly extends NT2 (real schema source only) and revises NT10's rendering, see note below.

**Predicate:**
```
every rendered node shows two distinct labels: a display name and a
real node type string; the node type string matches an entry in the
vendored n8n node schema file exactly, never an invented approximation
```

**Note — amends NT10:** NT10 (`node-translation.md`) previously specified display names in the form `Verb Object — Layer`. That suffix is now removed per CR12 below; NT10 is revised to `Verb Object` only, with the real node type shown as a second, distinct label alongside it, per this rule.

---

## CR12 — No Redundant Stage Suffix on Node Labels

**Statement:** If a node already sits visually inside a stage/layer grouping (background, legend, or container), its display name does not repeat that stage name (e.g. a node already inside an "Ingestion" grouping is labeled "Validate File Type", not "Validate File Type — Ingestion"). The stage container already communicates that context; repeating it on every node is noise.

**Grounding:** Same source — explicit rule against redundant stage suffixes, on the basis that the containing stage already provides that information visually.

**Applies to:** Node Mapper, SVG Renderer — this is the specific correction to NT10's earlier `— Layer` suffix.

**Predicate:**
```
no rendered node display name contains its own stage/layer name as a
suffix; stage context is conveyed only by the visual grouping itself
```

---

## CR13 — No Orphan Nodes, Terminal Nodes Are Fine

**Statement:** A node meant to continue execution must have the connection that continuation requires — an unconnected node that should participate in the flow is a rendering defect. A node that intentionally ends a path (a genuine terminal, e.g. a rejected/error branch that simply stops) is not an orphan and requires no further connection.

**Grounding:** Same source — explicit distinction between an unintentional dead end (defect) and an intentional terminal path (valid).

**Applies to:** Validator (extends P5, No Orphan, to the rendered-canvas level specifically).

**Predicate:**
```
every node has at least one incoming connection unless it is a declared
entry point, and at least one outgoing connection unless it is declared
terminal_output (per P5); a node with neither, undeclared, is rejected
```

---

## CR14 — Consecutive Nodes Must Represent Genuinely Distinct Operations

**Statement:** Before rendering two consecutive nodes as separate steps, confirm they represent two actually distinct operations. If they do, keep both — do not artificially merge genuine architectural activities just to simplify the n8n view. If they don't (a step was accidentally duplicated in the underlying tree), that is a decomposition defect to fix upstream, not something to silently collapse or silently leave duplicated in the rendering layer.

**Grounding:** Same source — flags this as a two-sided requirement: neither artificial duplication nor unjustified deletion of real activities is acceptable in the n8n representation.

**Applies to:** Node Mapper (this is a rendering-layer check; the underlying fix, if needed, belongs to the Decomposition Engine, not this file).

**Predicate:**
```
any two consecutive nodes with identical requires[]/produces[]/rules[]
are flagged for review as possible unjustified duplication, rather than
rendered silently as-is
```

---

## CR15 — Stage Zones Are Allocated First, Non-Overlapping by Construction

**Statement:** Layout computes each top-level stage's vertical zone *before* positioning any node — stacked sequentially with a running cursor, each zone's height derived from its own row count, header, padding, and local branch space. Nodes are positioned only after their stage's zone is fixed. A row never spans two stages; if a stage needs more than one row, both rows still belong entirely to that one stage's zone. Stage-zone overlap must be structurally impossible, not merely checked for and avoided after the fact.

**Grounding:** A dedicated stage-layout correction specification, directly addressing a real defect this project shipped: computing node positions first and deriving stage bounding boxes from wherever nodes happened to land produced overlapping and disconnected stage regions once row wrapping stopped aligning 1:1 with stage membership. The corrected model inverts the computation order: `stage membership → allocate non-overlapping zones → rows within each zone → position nodes`, per that specification's explicit "core implementation principle."

**Applies to:** Node Mapper (layout computation) — this supersedes any layout scheme (including an earlier draft of CR3 in this same file) that computed stage grouping as a bounding box around already-positioned nodes.

**Predicate:**
```
for every pair of top-level stage zones, zoneA.bottom <= zoneB.top or
zoneB.bottom <= zoneA.top (no vertical overlap); every node's row index
is local to its own stage's zone, never shared with another stage's rows
```

---

## CR16 — Routed Connections Enter Through the Target's Normal Input Port

**Statement:** When a connection is routed through whitespace (a branch, a row transition, a cross-stage connection), it still approaches and enters its target through that node's normal input port — left side, for standard left-to-right execution — never an arbitrary anchor like the top or bottom of the node chosen only because that happened to be convenient for the routing geometry. The node's visual position on the canvas never changes its underlying input-port semantics.

**Grounding:** Same routing-correction specification — explicit rule that routed connections must "prefer entering through the node's normal LEFT input port" and must not "arbitrarily enter from the top merely because the node is on another row/stage." This corrects an earlier implementation choice in this project that connected cross-stage edges to a target's top edge for routing convenience.

**Applies to:** SVG Renderer (edge termination point selection).

**Predicate:**
```
every connection's terminal point coincides with the target node's
declared input port (left side, for standard nodes); no connection
terminates at a node's top or bottom edge purely for routing convenience
```

---

## CR17 — Row/Layout Debug Information Stays Out of the Production Canvas

**Statement:** Information that exists to explain or verify the renderer's own layout decisions — row numbers, node-per-row counts, "(within 9-10 limit)" annotations, routing-lane labels — is a development/debug aid, not user-facing product content. The underlying rules it reports on (the 9-10 node cap, whitespace routing lanes) remain fully enforced internally; only their visible textual explanation is removed from the normal canvas view.

**Grounding:** Same routing-correction specification, explicit: "the user does NOT need to see the renderer's own row calculation," and a companion spatial-hierarchy specification's rule that routing lanes and row-debug labels are explanatory devices for a reference diagram, not required production UI.

**Applies to:** SVG Renderer.

**Predicate:**
```
no row-count text, node-per-row-limit text, or routing-lane label
renders on the canvas in normal (non-debug) mode; the constraints
themselves remain enforced in layout computation regardless
```

---

## CR18 — Connection Classification Determines Routing Strategy, Not the Reverse

**Statement:** Before generating a path, every connection is classified into one of a small set of relationship types (adjacent primary, local branch, row transition, cross-row, cross-stage, long-distance), and the routing strategy follows from that classification — never the other way around, where a generic source-to-target formula is applied uniformly and the visual result is accepted regardless of which relationship it actually represents.

**Grounding:** Same routing-correction specification's explicit routing algorithm: classify first, then select strategy, then generate geometry, then check collisions — never skip straight from coordinates to a Bézier formula.

**Applies to:** SVG Renderer (edge path generation), Node Mapper (edge classification, extends WD9's control-flow pattern tagging).

**Predicate:**
```
every rendered edge carries an explicit classification tag before path
generation begins; the geometry function invoked is a direct function
of that tag, never a single generic formula applied regardless of class
```

---

## Summary Table

| ID | Rule | Grounding |
|----|------|-----------|
| CR1 | Nodes/Connections Are the Only Executable Objects | n8n execution model |
| CR2 | Stages Are Visual Groups, Never Execution Gates | n8n execution model |
| CR3 | Primary Direction Is Left to Right, Never Stage-Forced Vertical | Left-to-right diagramming convention |
| CR4 | Row Wrap at ~9-10 Nodes, Never Snake Execution | Diagramming readability convention |
| CR5 | Rounded Orthogonal Routing, Never Sweeping Bézier | Routing-correction specification |
| CR6 | Routing Uses Whitespace Lanes, Never Passes Through Nodes | Edge-routing convention |
| CR7 | Every Connection Traceable Port to Port | Diagram clarity convention |
| CR8 | Conditional Nodes Show Distinct, Correctly-Ported Outputs | n8n branching model |
| CR9 | Multiple Items ≠ Multiple Branches; No Auto-Loops | n8n item-flow model |
| CR10 | Item Flow Survives Row/Stage Boundaries | n8n item-flow model |
| CR11 | Display Name and Real Node Type Both Shown | n8n node model; amends NT10 |
| CR12 | No Redundant Stage Suffix on Labels | Redundancy-avoidance convention; corrects NT10 |
| CR13 | No Orphan Nodes; Terminals Are Fine | Extends P5 to canvas level |
| CR14 | Consecutive Nodes Must Be Genuinely Distinct | Duplication-avoidance convention |
| CR15 | Stage Zones Allocated First, Non-Overlapping by Construction | Stage-layout correction specification |
| CR16 | Routed Connections Enter Through Normal Input Port | Routing-correction specification |
| CR17 | Row/Layout Debug Info Stays Out of Production Canvas | Routing-correction specification |
| CR18 | Classification Determines Routing Strategy | Routing-correction specification |

This file is referenced from `RULES-INDEX.md`. It sits alongside `node-translation.md` (which governs step-to-node *mapping*) as the file governing step-to-node *rendering*; CR11/CR12 formally supersede the display-name portion of NT10, which is updated accordingly. CR15 formally supersedes the original layout description under CR3, and CR5 has been corrected once already within this same file (Bézier-only → rounded orthogonal) as the design was tested against real rendering and found wanting — both corrections are kept visible in this file's own text rather than silently overwritten, consistent with this corpus's traceability requirements (G1, G3).
