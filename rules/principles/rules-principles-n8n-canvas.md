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

**Statement:** The default and primary execution direction is horizontal, left to right. Stages/layers must never force vertical stacking as the layout mechanism (e.g. Stage 1 above Stage 2 above Stage 3). Nodes follow their actual execution dependency order primarily left to right, regardless of which stage each one belongs to.

**Grounding:** Same source — horizontal is the main visual grammar; vertical or curved-away-from-row movement is reserved specifically for branches, alternate routes, and cross-row connections, not for ordinary sequential flow.

**Applies to:** Node Mapper layout computation (this directly supersedes any layout scheme that assigns one row per layer/stage).

**Predicate:**
```
the primary sequence of nodes is laid out left to right in dependency
order; row assignment is never a direct function of layer/stage
membership — a row may contain nodes from more than one stage, and a
stage's nodes may span more than one row
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

## CR5 — Connections Are Smooth Bézier Curves, Not Hard Right-Angle Elbows

**Statement:** Connections use smooth, curved (Bézier) routing throughout, as the single consistent connection language. Adjacent nodes get near-straight curves; curvature increases for branches, cross-row connections, and distant-node connections — but the connection style itself (curved) never switches to rigid 90-degree elbow routing as a way of handling those cases. Row-transition connections specifically must remain curved, routed through the whitespace between rows, not rendered as hard-cornered paths.

**Grounding:** Same source — explicitly names smooth Bézier as the required primary style and forbids mixing hard elbows, straight lines, and arbitrary curves within one canvas; curvature is the variable that changes with routing distance, not the underlying connection style. This corrects an earlier implementation choice in this project that used a hard right-angle elbow for row transitions — that choice is superseded by this rule.

**Applies to:** SVG Renderer (edge path generation for both same-row and cross-row connections).

**Predicate:**
```
100% of rendered connections use curved/Bézier paths; zero connections
use a hard right-angle (elbow) path, regardless of whether they connect
adjacent nodes, branches, or nodes across a row break
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

## Summary Table

| ID | Rule | Grounding |
|----|------|-----------|
| CR1 | Nodes/Connections Are the Only Executable Objects | n8n execution model |
| CR2 | Stages Are Visual Groups, Never Execution Gates | n8n execution model |
| CR3 | Primary Direction Is Left to Right, Never Stage-Forced Vertical | Left-to-right diagramming convention |
| CR4 | Row Wrap at ~9-10 Nodes, Never Snake Execution | Diagramming readability convention |
| CR5 | Smooth Bézier Only, Never Hard Elbows | Consistent connection-language convention |
| CR6 | Routing Uses Whitespace Lanes, Never Passes Through Nodes | Edge-routing convention |
| CR7 | Every Connection Traceable Port to Port | Diagram clarity convention |
| CR8 | Conditional Nodes Show Distinct, Correctly-Ported Outputs | n8n branching model |
| CR9 | Multiple Items ≠ Multiple Branches; No Auto-Loops | n8n item-flow model |
| CR10 | Item Flow Survives Row/Stage Boundaries | n8n item-flow model |
| CR11 | Display Name and Real Node Type Both Shown | n8n node model; amends NT10 |
| CR12 | No Redundant Stage Suffix on Labels | Redundancy-avoidance convention; corrects NT10 |
| CR13 | No Orphan Nodes; Terminals Are Fine | Extends P5 to canvas level |
| CR14 | Consecutive Nodes Must Be Genuinely Distinct | Duplication-avoidance convention |

This file is referenced from `RULES-INDEX.md`. It sits alongside `node-translation.md` (which governs step-to-node *mapping*) as the file governing step-to-node *rendering*; CR11/CR12 formally supersede the display-name portion of NT10, which is updated accordingly.
