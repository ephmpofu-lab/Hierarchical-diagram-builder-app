# Rules and Principles: Decomposition Engine

Part of `rules/principles/`. This is the readable, grounded companion to the machine-checkable predicates already defined in `rules/decomposition_principles.json` and `ARCHITEQ-Decomposition-Engine-Spec.md`. Nothing here changes those predicates; this file exists so every rule's origin is stated once, in prose, in one place, rather than scattered across JSON comments.

Template per rule: **Statement | Grounding | Applies to | Predicate**

---

## P1 — Atomicity

**Statement:** A step is atomic only if it has exactly one action, one input, one output, and maps to exactly one implementation unit (one function call or one node).

**Grounding:** The Single Responsibility Principle, one of the five SOLID principles (Robert C. Martin, building on Bertrand Meyer's earlier open/closed work; formalized as "SOLID" by Michael Feathers). Applied here to a task-tree node rather than a class or function, but the underlying claim is identical: a unit that does one thing is easier to verify, reuse, and reason about than one that does several.

**Applies to:** Stage 3 (Atomic Step Generation), now revised by the Grounding Simulation addendum to derive candidates from a real trace rather than an invented description.

**Predicate:** as specified in Decomposition Engine Spec Section 5 (five criteria).

---

## P2 — No Skip

**Statement:** Breadth-first only. Every sub-task of a layer must exist before any sub-task decomposes into atomic steps.

**Grounding:** This mirrors the C4 model's own discipline (Simon Brown, "The C4 Model for Visualising Software Architecture") of moving through Context, Container, Component, and Code as distinct, complete passes rather than diving into implementation detail on one component while others remain unexamined — a common cause of architectural blind spots in ad hoc system design.

**Applies to:** Stage 1 through Stage 3 of the build order.

**Predicate:** as specified in Decomposition Engine Spec Section 4.

---

## P3 — Variable Exhaustion

**Statement:** Every configurable parameter an atomic step touches is listed, including ones with defaults. Nothing is silently assumed.

**Grounding:** This is the decomposition-engine-specific instance of WD10 (Explicit Over Implicit) — an unlisted default is exactly the kind of hidden convention that principle forbids, applied here to the specific case of function/node parameters.

**Applies to:** Stage 4 (Variable Exhaustion).

**Predicate:** as specified in Decomposition Engine Spec Section 4, Stage 4.

---

## P4 — Dependency and Rules

**Statement:** Every atomic step declares `requires[]`, `produces[]`, and (per the Simulation Grounding addendum) `rules[]`.

**Grounding:** `requires`/`produces` operationalizes WD5 (Explicit Dependencies), itself grounded in the Workflow Patterns initiative's (van der Aalst et al., 2003) treatment of explicit data dependency as the basis of correct sequencing. `rules[]` operationalizes G5 (Transparency) and G6 (Data Provenance) at the individual-step level.

**Applies to:** Every atomic step, without exception.

**Predicate:** as specified in Decomposition Engine Spec Section 7 (Validator check 1).

---

## P5 — No Orphan

**Statement:** Every `produces[]` output is consumed downstream or explicitly marked `terminal_output`.

**Grounding:** This is WD1 (Single Source of Truth) viewed from the consumption side rather than the production side — WD1 ensures no output has two producers; P5 ensures every output that is produced actually goes somewhere, closing the other half of the same data-integrity concern.

**Applies to:** Full-tree Validator pass, after Stage 4.

**Predicate:** as specified in Decomposition Engine Spec Section 4, Stage 4 note and Section 7.

---

## P6 — Tool Agnosticism

**Statement:** Steps are named and defined by function, never by implementation. Implementation binding (which Python library, which n8n node) happens only at render time.

**Grounding:** This is Separation of Concerns (WD3, Dijkstra 1974) applied to the boundary between the abstract task tree and its two renderers — conflating "what" with "how" at the tree level would make the single-tree-two-renderers architecture (Build Directive Section 2) impossible to maintain, since a tree tied to one implementation could not honestly feed the other renderer.

**Applies to:** Stage 2 and Stage 3 tree generation; explicitly checked before Node Mapper or Python Renderer touch the tree.

**Predicate:** as specified in Decomposition Engine Spec Section 4.6, Build Directive 4.6.

---

## P7 — Domain Checklist Coverage

**Statement:** Every mandatory layer from the domain's checklist is present and non-empty.

**Grounding:** For ML/AI domains, the checklist itself derives from TDSP (Microsoft's Team Data Science Process); the requirement that all mandatory stages be present, none skipped, mirrors TDSP's own insistence that skipping a lifecycle stage (e.g. going straight from data acquisition to deployment without evaluation) is a recognized failure mode in ML system delivery, not a shortcut.

**Applies to:** Stage 1 (Layer Instantiation), domain checklist files.

**Predicate:** as specified in Decomposition Engine Spec Section 2.1 and Section 7.

---

## P8 — Cross-Cutting Concerns Coverage

**Statement:** Every one of the five Well-Architected pillars (security, reliability/observability, performance/cost, operational excellence, governance/compliance) is addressed by at least one atomic step somewhere in the tree.

**Grounding:** The AWS/Azure/GCP Well-Architected Frameworks (independently converging on materially the same five pillars across all three major cloud providers' published architecture guidance) treat these as concerns that apply to every system regardless of its domain-specific function — a RAG pipeline and a scheduling system both need security and observability, even though neither is a domain-specific "layer" the way Ingestion or Retrieval is.

**Applies to:** Full-tree Validator pass, checked independently of the domain checklist.

**Predicate:** as specified in Decomposition Engine Spec Section 3.

---

## Reference Architecture Index (restated from the Decomposition Engine Spec, Section 2, for completeness)

| Framework | Used for | Source |
|---|---|---|
| TDSP | ML/AI domain checklist layer derivation | Microsoft, Team Data Science Process |
| C4 Model | Fixed 4-level nesting (Layer/Sub-task/Atomic step/Variable) | Simon Brown, "The C4 Model" |
| Well-Architected Framework | Cross-cutting concerns overlay (P8) | AWS/Azure/GCP, convergent published guidance |
| SOLID (SRP specifically) | Atomicity Test grounding (P1) | Robert C. Martin |
| Workflow Patterns | Explicit dependency and control-flow logic (P4, WD5, WD9) | van der Aalst, ter Hofstede et al., 2003 |

## Summary Table

| ID | Rule | Grounding |
|----|------|-----------|
| P1 | Atomicity | SOLID / Single Responsibility Principle |
| P2 | No Skip | C4 Model (Brown) |
| P3 | Variable Exhaustion | WD10 (Explicit Over Implicit), specific instance |
| P4 | Dependency and Rules | Workflow Patterns (van der Aalst et al.); G5, G6 |
| P5 | No Orphan | WD1 (Single Source of Truth), consumption side |
| P6 | Tool Agnosticism | Separation of Concerns (Dijkstra) |
| P7 | Domain Checklist Coverage | TDSP (Microsoft) |
| P8 | Cross-Cutting Concerns Coverage | Well-Architected Framework (AWS/Azure/GCP) |

This file is referenced from `RULES-INDEX.md`. Two categories remain in the planned corpus: prompting, and a decision on whether node translation (currently folded into WD9) warrants its own file.
