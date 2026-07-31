# ARCHITEQ — Dual Tree Architecture: Component Tree vs. Workflow Tree

Addendum to `ARCHITEQ-Decomposition-Engine-Spec.md` and `ARCHITEQ-Simulation-Grounding-and-Visual-Fix.md`. This corrects a conflation in the original spec: Python and n8n do not need the same tree shape rendered two ways. They need two different projections of the same underlying grounded domain data.

---

## 1. Two Trees, One Source

**Component Tree (structural)** — what the system is made of, and how each part is configured. Leaves are attributes/parameters, not actions. This is what Image 1 shows: `Goal → Requirements Engineering → Capability Identification → Functional Decomposition → Components (Knowledge Source, Document Ingestion, Embedding, Vector Database, Retrieval, LLM, API, UI) → each component's attributes`.

**Workflow Tree (behavioral)** — what happens, in what order, with what data flowing between steps. Leaves are atomic actions with `requires`/`produces`/`rules`. This is the tree already specified in `ARCHITEQ-Decomposition-Engine-Spec.md`: `Layer → Sub-task → Atomic step → Variable`, grounded via Stage 2.5's Operator/Builder simulation.

**They are not independent.** Both derive from the same domain resolution and the same grounded trace. A component's attribute in the Component Tree (e.g. `Embedding → Model`) and a variable on an atomic step in the Workflow Tree (e.g. `embed_chunks`'s `model_name` parameter) must be the same underlying value, defined once and referenced by both — this extends WD1 (Single Source of Truth) explicitly across both projections, not just within one tree.

```
                    Domain Resolution + Grounded Trace
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                  ▼
        COMPONENT TREE                       WORKFLOW TREE
   (structural, attribute leaves)      (behavioral, action leaves)
                 │                                  │
                 ▼                                  ▼
         PYTHON RENDERER                       n8n RENDERER
   (exploding branch diagram,             (sequential node graph,
    scaffolds classes/config)              hover reveals payload)
```

---

## 2. New Pre-Stages: Building the Component Tree

Insert these stages before Stage 0 (Domain Resolution) in the Decomposition Engine's build order, specifically for the Component Tree. The Workflow Tree's existing Stages 0-4 (with Stage 2.5 grounding) are unaffected and continue to run as already specified.

```
STAGE -3 — Requirements Engineering
  input: the project's PRD (per the Universal PRD Framework)
  action: extract functional and non-functional requirements relevant to
    this domain from the PRD's Requirements section
  output: a requirements list, each item traceable to a PRD requirement ID

STAGE -2 — Capability Identification
  input: requirements list from Stage -3
  action: group requirements into discrete capabilities the system must
    have (e.g. "must be able to answer questions grounded in a document
    corpus" becomes the capability "Retrieval-Augmented Generation")
  output: an ordered capability list

STAGE -1 — Functional Decomposition
  input: capability list from Stage -2
  action: break each capability into its constituent components (e.g.
    RAG capability decomposes into Knowledge Source, Document Ingestion,
    Embedding, Vector Database, Retrieval, LLM, API, UI)
  output: a component list, each component traceable to the capability
    and requirement that produced it

STAGE 0 (Component Tree specific) — Component Attribute Enumeration
  for EVERY component from Stage -1:
    enumerate its configuration attributes down to the smallest
    meaningful unit (e.g. Embedding's attributes: Model, Dimensions,
    Batch Size, Metadata)
    each attribute must be a leaf: a single named property with a
    single type, never a compound description
  output: the frozen Component Tree, four levels:
    Capability → Component → Attribute Group → Attribute
```

This produces exactly the shape in Image 1: `Goal → Requirements Engineering → Capability Identification → Functional Decomposition → [Components] → [Attributes]`. Note the first three branch labels in Image 1 are the *pipeline stages themselves*, shown as provenance — this is intentional and should be kept in the Python-rendered diagram, since it makes every component traceable back to why it exists (satisfying G1, Traceability, at the structural level).

---

## 3. Reconciliation Rule (extends WD1)

Before either tree is considered frozen, every attribute in the Component Tree must resolve to exactly one variable in the Workflow Tree, and vice versa. Neither tree may define a configuration value the other doesn't know about.

**Predicate:**
```
for each attribute in the Component Tree:
    exactly one atomic_step variable in the Workflow Tree shares its
    canonical name and value
    else REJECT, reason: "attribute has no corresponding workflow variable,
    or vice versa — trees have diverged"
```

Practically: `Embedding → Model` (Component Tree) and `embed_chunks.model_name` (Workflow Tree) are the same fact, stored once, referenced twice.

---

## 4. Python Renderer: Exploding Branch Diagram

- Rendered as a literal branching tree (ASCII-style connectors: `├──`, `└──`, `│`), matching Image 1's visual convention exactly, not the flat stacked-card layout already flagged as wrong in the Simulation Grounding addendum.
- Each Component becomes a Python module or class; each Attribute becomes a field on that class (Pydantic model, per the existing stack constraint of using Pydantic for structured output where relevant).
- The diagram is the literal scaffold: walking the tree top to bottom in order produces the file/class structure directly, not just a visualization of it.
- Collapsible per component, per UI4 (Progressive Disclosure) — full attribute detail expands on interaction, matching the "Continue decomposing..." affordance already shown in Image 1's own UI.

---

## 5. n8n Renderer: Node Graph with Hover-Reveal Payload

- Rendered as the sequential node-and-edge graph already specified (Simulation Grounding addendum Section 5, using the Tool A diagram builder) — this part is unchanged.
- **New requirement:** hovering (or tapping, on mobile) any node reveals its actual data contract: `requires[]` as inputs, `produces[]` as outputs, and any intermediate objects/variables that pass through it as "baby nodes" — the payload shape moving from this node to the next.
- This hover payload is sourced directly from the atomic step's `requires`/`produces`/`rules` fields (already mandatory per P4) and the reconciled attribute values from Section 3 — never a separately invented description.
- The parent view (Image 2's second diagram: `RAG Platform → Ingestion/Retrieval/User Interface → Workflow A/B/C → n8n Nodes → Atomic Tasks`) is the zoomed-out version of the same graph; zooming in reveals individual nodes with their hover payload, zooming out reveals the layer/sub-task grouping. Same underlying data, different zoom level — not a separately maintained diagram.

---

## 6. Where Python Development Actually Starts

For a Python-track build, the starting sequence is:

```
PRD → Requirements Engineering (Stage -3) → Capability Identification (Stage -2)
    → Functional Decomposition (Stage -1) → Component Attribute Enumeration (Stage 0)
    → Component Tree frozen → reconciled against Workflow Tree (Section 3)
    → Python code scaffolding begins directly from the frozen Component Tree
```

This answers the "where do you start" question directly: not at the workflow/sequence level, but at the PRD, moving through requirements and capabilities before any component or attribute is named — the same discipline already required by the Universal PRD Framework, now explicitly wired into the Decomposition Engine's Python-track entry point.
