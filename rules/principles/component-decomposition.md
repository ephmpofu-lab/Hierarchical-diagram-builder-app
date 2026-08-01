# Rules and Principles: Component & Requirements Decomposition

Part of `rules/principles/`. Grounds the pre-stages introduced in `ARCHITEQ-Dual-Tree-Architecture.md` (Requirements Engineering, Capability Identification, Functional Decomposition, Component Attribute Enumeration) and the Component Tree they produce.

Template per rule: **Statement | Grounding | Applies to | Predicate**

---

## CD1 — Requirements Precede Capabilities

**Statement:** No capability is identified except as a grouping of one or more explicit requirements already extracted from the PRD. A capability invented without a traceable requirement behind it is not permitted.

**Grounding:** ISO/IEC/IEEE 29148 (Systems and Software Engineering — Requirements Engineering), the international standard governing requirements engineering practice, which requires capabilities and features to be derived from documented stakeholder requirements, not asserted independently.

**Applies to:** Stage -3 to Stage -2 transition (Requirements Engineering → Capability Identification).

**Predicate:**
```
every capability in the Capability list carries a traced_requirements[]
field listing the specific PRD requirement IDs (R1, R2, ...) it groups;
a capability with an empty traced_requirements[] is rejected
```

---

## CD2 — Capabilities Precede Components

**Statement:** No component is named except as something needed to deliver an identified capability. A component with no capability behind it is scope creep, not a legitimate part of the system.

**Grounding:** Business Capability Modeling, as used in enterprise architecture practice (notably TOGAF, The Open Group Architecture Framework) — capabilities are defined independent of implementation, and components/systems are then mapped to the capabilities they realize, ensuring nothing gets built that doesn't trace to a business or functional need.

**Applies to:** Stage -2 to Stage -1 transition (Capability Identification → Functional Decomposition).

**Predicate:**
```
every component in the Component list carries a realizes_capability
field naming the specific capability it exists to deliver; an
orphaned component with no realizes_capability is rejected
```

---

## CD3 — Functional Decomposition Is Top-Down and Exhaustive

**Statement:** A capability is decomposed into ALL the components required to realize it before any single component is decomposed further into its attributes. Breadth-first across components, same discipline as P2 (No Skip) at the Workflow Tree level.

**Grounding:** Structured Analysis (Tom DeMarco, "Structured Analysis and System Specification," 1979; Ed Yourdon) — the classical top-down functional decomposition technique, explicitly breadth-first to avoid over-detailing one branch while others remain unexamined.

**Applies to:** Stage -1 (Functional Decomposition).

**Predicate:**
```
for a given capability, no component's attributes are enumerated
(Stage 0) until every component realizing that capability has been
named; identical breadth-first discipline as P2, applied one level up
```

---

## CD4 — Attributes Are Leaves, Not Compound Descriptions

**Statement:** A component attribute is a single named property with a single type (e.g. `Batch Size: integer`). It is never a compound description requiring further unpacking to be usable.

**Grounding:** This is the Component Tree's equivalent of the Atomicity Test (P1) — a component attribute that isn't actually atomic can't become a single Pydantic field or config value, the same way a workflow step that isn't atomic can't become a single function or node.

**Applies to:** Stage 0 (Component Attribute Enumeration).

**Predicate:**
```
every leaf in the Component Tree has exactly one name and one declared
type; a leaf requiring "and" to describe its meaning is rejected and
must be split into two leaves
```

---

## CD5 — Components Are Bounded, Not Overlapping

**Statement:** Two components do not both claim ownership of the same attribute or responsibility. Each component has a clear boundary.

**Grounding:** Domain-Driven Design's concept of bounded contexts (Eric Evans, "Domain-Driven Design: Tackling Complexity in the Heart of Software," 2003) — a system decomposed into components each with an unambiguous boundary is what prevents the same concept from being modeled (and potentially modeled inconsistently) in two places at once.

**Applies to:** Stage -1 (Functional Decomposition), Component Tree validation.

**Predicate:**
```
no attribute name (or its canonical underlying value, per the
Reconciliation Rule in ARCHITEQ-Dual-Tree-Architecture.md Section 3)
appears under more than one component in the Component Tree
```

---

## CD6 — The Component Tree and Workflow Tree Reconcile, Never Diverge

**Statement:** Every attribute in the Component Tree resolves to exactly one variable in the Workflow Tree, and every workflow variable resolves to exactly one Component Tree attribute. Neither tree is considered frozen until this holds.

**Grounding:** Direct restatement of WD1 (Single Source of Truth) across two projections rather than within one tree; this is the rule that keeps the dual-tree architecture from becoming two independently drifting sources of truth about the same system.

**Applies to:** Final validation step before either tree is frozen, per `ARCHITEQ-Dual-Tree-Architecture.md` Section 3.

**Predicate:** as specified in `ARCHITEQ-Dual-Tree-Architecture.md` Section 3.

---

## CD7 — Provenance Is Kept Visible in the Rendered Tree

**Statement:** The Python-rendered Component Tree retains its Requirements Engineering, Capability Identification, and Functional Decomposition branches as visible provenance, not just as internal bookkeeping discarded after Stage 0 completes.

**Grounding:** G1 (Traceability) applied specifically to the rendered artifact a human actually sees — a component whose reason for existing is only recoverable by re-querying internal state, rather than visible in the diagram itself, fails the spirit of traceability even if the data technically exists somewhere.

**Applies to:** Python Renderer (Section 4 of `ARCHITEQ-Dual-Tree-Architecture.md`).

**Predicate:**
```
the rendered Component Tree diagram includes the Requirements
Engineering / Capability Identification / Functional Decomposition
branches, not only the Component/Attribute leaves beneath them
```

---

## CD8 — Component Attributes Map to One Code Construct

**Statement:** Every Component in the Component Tree maps to exactly one Python module or class; every Attribute maps to exactly one field on that construct. No component spans multiple classes, and no single class silently absorbs multiple components.

**Grounding:** Restates NT1's discipline (one atomic step, one node) at the Python/Component Tree level — the same one-to-one mapping requirement that makes n8n export reliable also makes Python code scaffolding reliable, for the identical underlying reason (SOLID's Single Responsibility Principle, Martin).

**Applies to:** Python Renderer.

**Predicate:**
```
for each Component, exactly one class/module exists in the rendered
scaffold; for each Attribute, exactly one field exists on that
construct
```

---

## CD9 — Attributes Recurse Until Genuinely Atomic; Completion Rolls Up the Same Way

**Statement:** An Attribute Group may recurse into further sub-groups, arbitrarily deep, before reaching a true Attribute leaf (per CD4). Depth is never capped at a fixed count. Every node in the Component Tree carries a `[ ]`/`[-]`/`[x]` completion status; a non-leaf node's status is always the rollup of its children, never independently set.

**Grounding:** Same grounding as WD11/WD12 (Work Breakdown Structure practice and the WBS 100% Rule, Project Management Institute) applied to the Component Tree side of the dual-tree architecture, so both trees share one completion-tracking discipline rather than two.

**Applies to:** Stage 0 (Component Attribute Enumeration), Node Detail Panel completion controls.

**Predicate:** as specified in `ARCHITEQ-Recursive-Depth-and-Completion-Tracking.md` Sections 1 and 3.

---

## CD10 — Generated Architecture Carries Its Own Documentation Set Before Freezing

**Statement:** ARCHITEQ's own six-document discipline (DP11, `dev-process.md`) does not only
govern how ARCHITEQ itself gets built — it also governs what ARCHITEQ produces when a user
asks it to architect something else. A Component Tree is not considered frozen until it
carries the equivalent of all six documents for the system it describes. Unlike DP11, these
are not six documents written before Build begins — Stages -3 through 0 largely *are* the
build. This rule is a completion gate, evaluated at freeze time, the same enforcement shape
CD1-CD3 already use for stage ordering, not a precondition evaluated before Stage -3 starts.

Mapped concretely:
- **Requirements-Engineering-equivalent** — already satisfied by Stage -3 (CD1).
- **Backend-Schema-equivalent** — already satisfied by Stage 0 Attribute Enumeration (CD4).
- **Engineering-Plan-equivalent** — already satisfied by the Workflow Tree's `requires`/
  `produces` topological order (R10); cross-referenced here, not duplicated.
- **Tech-Decisions-equivalent** — NOT yet satisfied by any existing stage. Every Component
  (Python track) whose realization involved a genuine implementation choice (e.g. which
  vector database, which LLM API, which storage pattern) must carry a one-line rationale
  for that choice. On the Workflow Tree side, this applies only to an Atomic step whose
  node-mapping was a genuine judgment call, not a deterministic single-match (most
  n8n mappings are already deterministic per NT2/Atomicity criterion 5 and need no
  separate rationale).
- **App-Flow-equivalent and Design-Brief-equivalent** — NOT yet satisfied by any existing
  stage, and conditional: required only when the Component Tree contains at least one
  UI-tagged component. When no UI component exists, both are explicitly recorded as "not
  applicable," never silently absent — the same "explicit over implicit" standard WD10
  already sets for workflow behavior, applied here to documentation completeness. Does not
  apply to the Workflow Tree/n8n track at all — n8n output is headless by construction.

**Grounding:** Direct restatement of DP11 at the generated-architecture layer, per the same
cross-layer-restatement convention this corpus already uses (RULES-INDEX.md's own stated
policy: one underlying principle, applied consistently at every layer it touches, rather
than independently invented twice). The six-document grounding sources are DP11's own:
IEEE 830/1016, Nygard (Architecture Decision Records) for the Tech-Decisions-equivalent
specifically, Garrett (UX) and Frost (Atomic Design) for the conditional App-Flow/
Design-Brief-equivalent, Chen (ER Model) for the Backend-Schema-equivalent, PMI (WBS) for
the Engineering-Plan-equivalent.

**Applies to:** The Component Tree freeze step (after Stage 0, before Section 3's
Reconciliation Rule runs); the Workflow Tree's approve step, for the Tech-Decisions-
equivalent and Engineering-Plan-equivalent subset only.

**Predicate:**
```
before a Component Tree is frozen:
    Requirements-Engineering-equivalent present (CD1) -- already enforced
    Backend-Schema-equivalent present (CD4) -- already enforced
    every Component whose realization required a genuine implementation
        choice carries a non-empty rationale field
    IF the tree contains at least one UI-tagged component:
        an App-Flow-equivalent and a Design-Brief-equivalent are present
    ELSE:
        both are explicitly recorded as "not applicable"
    a tree with a UI-tagged component but no App-Flow/Design-Brief
        content, and no "not applicable" is possible, is rejected

before a Workflow Tree is approved:
    every Atomic step whose node-mapping was a genuine (non-deterministic)
        choice carries a non-empty rationale field
    Engineering-Plan-equivalent present (R10) -- already enforced
```

---

## Summary Table

| ID | Rule | Grounding |
|----|------|-----------|
| CD1 | Requirements Precede Capabilities | ISO/IEC/IEEE 29148 |
| CD2 | Capabilities Precede Components | TOGAF Business Capability Modeling |
| CD3 | Functional Decomposition Is Top-Down and Exhaustive | DeMarco/Yourdon, Structured Analysis, 1979 |
| CD4 | Attributes Are Leaves, Not Compound Descriptions | Restates P1 (Atomicity Test) at the component level |
| CD5 | Components Are Bounded, Not Overlapping | Evans, Domain-Driven Design, 2003 |
| CD6 | Trees Reconcile, Never Diverge | Restates WD1 across two projections |
| CD7 | Provenance Is Kept Visible | Restates G1 at the rendered-artifact level |
| CD8 | Components Map to One Code Construct | Restates NT1/SOLID at the Python level |
| CD9 | Attributes Recurse Until Atomic; Completion Rolls Up | WBS Practice Standard + 100% Rule (PMI) |
| CD10 | Generated Architecture Carries Its Own Documentation Set Before Freezing | Restates DP11 at the generated-architecture layer |

This file is referenced from `RULES-INDEX.md`.
