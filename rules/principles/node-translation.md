# Rules and Principles: Node Translation

Part of `rules/principles/`. Split out from `workflow-design.md` (WD9) because the atomic-step-to-n8n-node mapping is central enough to ARCHITEQ's n8n output path (Build Directive Section 4.8, the Node Mapper) to warrant its own file rather than one rule among ten. This file governs specifically how a validated atomic step becomes a real n8n node, not how the tree itself is built.

Template per rule: **Statement | Grounding | Applies to | Predicate**

---

## NT1 — One Atomic Step, One Node

**Statement:** Every atomic step maps to exactly one n8n node. No step spans multiple nodes, and no single node silently absorbs more than one step.

**Grounding:** Direct restatement of P1/the Single Responsibility Principle (SOLID), applied specifically at the node-mapping boundary rather than the tree-generation boundary — this is the criterion that makes the Atomicity Test's fifth check ("maps to exactly one implementation unit") concrete and verifiable once real node schemas are involved.

**Applies to:** Node Mapper (Build Directive Section 4.8).

**Predicate:**
```
for each atomic_step, exactly one node exists in the mapped output;
no node in the mapped output corresponds to more than one atomic_step
```

---

## NT2 — Real Schema Source Only

**Statement:** Node types and their parameter schemas come from a real, checked n8n schema source, never invented or approximated by the model.

**Grounding:** `Corrected` from an earlier "vendored GitHub JSON, pinned to a release" framing: confirmed during Module 8's build that n8n has no live schema-fetch endpoint and no downloadable full-catalog JSON (the real catalog is TypeScript source, not JSON). What actually satisfies this rule: `rules/n8n_node_schemas.json`, a small, hand-curated set of common core nodes, each checked by hand against n8n's published docs, with the Code node as mandatory fallback (NT3) for anything unmatched — restated here as a rule because it is the precondition for R14 (importable without manual correction) actually holding; a hallucinated schema field produces a workflow JSON that looks valid but fails on import.

**Applies to:** Node Mapper, JSON Exporter.

**Predicate:**
```
every mapped node's type and parameter set is checked against the
hand-curated schema file (rules/n8n_node_schemas.json);
a node type or parameter not present in that file is rejected, not guessed
```

---

## NT3 — Fallback to Code Node Is Mandatory, Not Silent

**Statement:** Every atomic step resolves to a node — either a real dedicated node type, or the Code/Function node fallback with the step's logic embedded as JS. A step is never silently dropped because no dedicated node exists for it.

**Grounding:** This is WD2 (No Silent Failure) applied to the specific failure mode of an unmappable atomic step; a mapping gap is itself a kind of failure and must be handled visibly (via the documented fallback), not by omission.

**Applies to:** Node Mapper.

**Predicate:**
```
for each atomic_step: a node exists in the mapped output, tagged either
node_type: <real_type> or node_type: "code_fallback"; no atomic_step
is absent from the mapped output for any reason
```

---

## NT4 — Control-Flow Patterns Map to Named n8n Nodes

**Statement:** The five control-flow patterns defined in WD9 map to specific, fixed n8n node types, never an improvised connection shape:

- Sequence → direct node-to-node connection
- Parallel Split (AND-split) → one node's output connects to multiple downstream nodes
- Synchronization (AND-join) → Merge node configured to wait for all inputs
- Exclusive Choice (XOR-split) → IF or Switch node
- Simple Merge (XOR-join) → Merge node configured as pass-through (first input wins)

**Grounding:** Direct extension of WD9 (Workflow Patterns, van der Aalst et al., 2003) into n8n's specific node vocabulary; this is what makes a tree's abstract control-flow tagging (already required by WD9's predicate) actually renderable, rather than leaving the renderer to guess which n8n node a given branch shape should become.

**Applies to:** Node Mapper, specifically wherever the tree contains a tagged branching edge.

**Predicate:**
```
every edge tagged and_split, and_join, xor_split, or xor_join (per WD9)
resolves to the corresponding fixed node type above; an untagged or
unmapped branching edge blocks JSON export
```

---

## NT5 — Dependencies Become Ports

**Statement:** An atomic step's `requires[]` becomes that node's incoming connection(s); its `produces[]` becomes that node's outgoing connection(s) and output data shape.

**Grounding:** This is WD5 (Explicit Dependencies) made concrete at the node level — the same dependency graph that governs execution order (Decomposition Engine Spec Section 6) is the literal source of the n8n workflow's `connections{}` object, not a separately computed layout.

**Applies to:** Node Mapper, JSON Exporter.

**Predicate:**
```
the connections{} object in the exported JSON is generated directly
from requires[]/produces[] edges; no connection exists in the export
that does not correspond to a requires/produces edge in the tree
```

---

## NT6 — Constraints Become Node Parameters

**Statement:** An atomic step's `rules[]` field (validation/business constraints) populates that node's actual parameter configuration, not a comment or description field the node ignores at runtime.

**Grounding:** Operationalizes P4's `rules[]` requirement and G5 (Transparency) at the rendering boundary — a rule that exists in the tree but doesn't reach the rendered node's actual configuration is functionally invisible, defeating the purpose of requiring it in the first place.

**Applies to:** Node Mapper.

**Predicate:**
```
every entry in an atomic_step's rules[] maps to a specific parameter
field on the mapped node (e.g. "max file size: 50MB" sets a size-limit
parameter, not a free-text note); a rule with no corresponding
parameter field on the target node type is flagged, not silently dropped
```

---

## NT7 — Least Privilege on Credentialed Nodes

**Statement:** Any mapped node that requires credentials (API keys, database connections) is scoped to exactly the access declared in that step's `access_scope` field (per G9), never given broader credential access than the step needs.

**Grounding:** Direct restatement of G9 (Least Privilege) at the node-mapping level, since this is the point where an abstract "security_relevant" tag becomes an actual credential binding with real blast-radius consequences if scoped too broadly.

**Applies to:** Node Mapper, wherever an atomic_step is tagged security_relevant per P8.

**Predicate:**
```
every mapped node using n8n credentials references a credential entry
scoped to the step's declared access_scope; no node is configured with
a broader-scope credential than declared
```

---

## NT8 — Idempotent Steps Use Safe-Retry Node Configurations

**Statement:** A step tagged `idempotent: true` (per WD8) maps to a node configuration that is actually safe to re-run (e.g. a database node using upsert rather than insert-only). A step tagged `idempotent: false` is mapped with retry/deduplication explicitly disabled or flagged, so a workflow re-run doesn't silently duplicate a non-idempotent action.

**Grounding:** Direct restatement of WD8 (Idempotency Where the Trace Allows It) at the node-configuration level — the idempotency tag is only meaningful if it actually changes how the corresponding node is configured, not left as inert metadata.

**Applies to:** Node Mapper.

**Predicate:**
```
for each mapped node whose source atomic_step is idempotent: true,
the node's write operation (if any) uses an upsert/safe-retry
configuration where the target node type supports one; for
idempotent: false steps, automatic retry is not silently enabled
```

---

## NT9 — Positions and Connections Are Computed Once

**Statement:** Node positions and connection layout are computed a single time by the Node Mapper and reused identically by both the JSON Exporter and the SVG diagram renderer. Neither consumer recomputes layout independently.

**Grounding:** WD4 (Determinism) applied specifically to the shared-computation requirement already stated in Build Directive Section 4.8 — if the JSON export and the visual diagram compute layout separately, they can silently diverge even when both are individually "correct," which defeats the purpose of a single-tree, two-renderer architecture (Build Directive Section 2).

**Applies to:** Node Mapper, JSON Exporter, SVG Renderer.

**Predicate:**
```
JSON Exporter and SVG Renderer both read positions and connections
from the same Node Mapper output object; neither computes its own
independent layout
```

---

## NT10 — Node Names Follow Verb + Object; Real Node Type Shown Alongside

**Statement:** Every rendered n8n node carries a human-readable display name, never a generic default (`Set1`, `IF2`). The name follows the pattern `[Verb] [Object]`, derived directly from the atomic step's name. It does not repeat the stage/layer name as a suffix — a node already sitting inside a visible stage grouping doesn't need that context restated on every label. Alongside the display name, the node's real n8n node type (e.g. `IF`, `Set`, `HTTP Request`) is shown as a distinct second label, never merged into or substituted for the display name, and never an invented approximation of a real n8n node name.

**Grounding:** Convergent n8n community best practice for the verb-first display name (node names should start with a verb, describe the action and data involved). The removal of the layer suffix and the requirement to show the real node type alongside the display name are corrections from `rules/principles/n8n-canvas-rules.md` CR11 and CR12, grounded in n8n's own explicit conceptual separation of custom display name from actual node type, and its rule against redundant stage suffixes now that stage context is conveyed visually by grouping rather than by label text.

**Applies to:** Node Mapper (Build Directive Section 4.8), SVG Renderer, JSON Exporter (display names are written into the exported workflow file, not left as defaults there either).

**Predicate:**
```
every exported or rendered node has a display_name matching the pattern
"{Verb} {Object}" (no layer suffix), derived from the atomic step's name
(already Verb+Object per the Atomicity Test, P1); the same node also
renders its real node_type as a distinct second label, matched exactly
against the vendored n8n node schema file, never invented; no node is
exported with an unedited default name
```

---

## Summary Table

| ID | Rule | Grounding |
|----|------|-----------|
| NT1 | One Atomic Step, One Node | SOLID / SRP (P1 restated) |
| NT2 | Real Schema Source Only | Hand-curated `rules/n8n_node_schemas.json`, checked against n8n docs |
| NT3 | Fallback to Code Node Is Mandatory | WD2, No Silent Failure |
| NT4 | Control-Flow Patterns Map to Named Nodes | Workflow Patterns (van der Aalst et al., 2003), extends WD9 |
| NT5 | Dependencies Become Ports | WD5, Explicit Dependencies |
| NT6 | Constraints Become Node Parameters | P4 rules[]; G5 Transparency |
| NT7 | Least Privilege on Credentialed Nodes | G9, restated |
| NT8 | Idempotent Steps Use Safe-Retry Configurations | WD8, restated |
| NT9 | Positions and Connections Computed Once | WD4, Determinism |
| NT10 | Node Names Follow Verb + Object; Real Node Type Shown Alongside | n8n community naming best practice; amended by CR11/CR12 |

This file is referenced from `RULES-INDEX.md`. This completes the planned rules corpus: workflow-design, governance, ui-design, dev-process, decomposition, prompting, node-translation.
