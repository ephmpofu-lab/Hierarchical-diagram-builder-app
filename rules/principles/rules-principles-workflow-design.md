# Rules and Principles: Workflow Design

Part of `rules/principles/`. Governs how ARCHITEQ constructs, sequences, and connects any workflow, whether rendered as Python code or an n8n graph. Every rule below is grounded in a named, citable source. Each is written as a testable predicate, following the same discipline as P1-P8 in `ARCHITEQ-Decomposition-Engine-Spec.md`.

Template per rule: **Statement | Grounding | Applies to | Predicate**

---

## WD1 — Single Source of Truth

**Statement:** Any given piece of data or state has exactly one authoritative origin in the tree. No two atomic steps independently produce the same output artifact.

**Grounding:** Single Source of Truth is a foundational data management principle (widely attributed to the relational database normalization literature, Codd 1970 onward) requiring that every fact be stored/produced in exactly one place, with everything else referencing it rather than duplicating it.

**Applies to:** Decomposition Engine (tree generation), Validator.

**Predicate:**
```
for each output_name in all produces[] across the tree:
    count(atomic_steps where produces includes output_name) == 1
    else REJECT, reason: "output produced by more than one step, no single source of truth"
```

---

## WD2 — No Silent Failure

**Statement:** Every atomic step that can fail must have an explicit, visible failure path (an error output, a `handle_*` step, or an escalation). A step is never allowed to fail and continue as if it succeeded.

**Grounding:** Fail-fast/fail-visible design is standard reliability engineering practice (see Google's Site Reliability Engineering literature on error budgets and alerting; also the general software engineering principle that swallowed exceptions are a leading cause of undiagnosable production failures).

**Applies to:** Decomposition Engine (Stage 2.5 grounding simulation, Stage 3 atomic step generation), Node Mapper, Python Renderer.

**Predicate:**
```
for each atomic_step where failure_possible == true:
    a corresponding error-handling step or explicit error output in produces[]
    must exist
    else REJECT, reason: "step can fail with no visible failure path"
```

Note: `failure_possible` is determined during Stage 2.5 grounding (the Builder simulation surfaces error/exception cases directly, e.g. `handle_unsupported_format`, `handle_read_error` — this is why those appeared in the worked ingestion example already).

---

## WD3 — Separation of Concerns

**Statement:** A layer, sub-task, or atomic step addresses exactly one concern. Cross-cutting concerns (security, observability, etc.) are tagged onto steps, never folded into a step's core function.

**Grounding:** Separation of Concerns, Dijkstra (1974), foundational software engineering principle: a system is easier to reason about and modify when each part has one clearly bounded responsibility.

**Applies to:** All four tree levels (Layer, Sub-task, Atomic step, Variable); this is the structural principle underneath the Atomicity Test's single-verb, single-object criterion, and underneath P8 (cross-cutting concerns are tags, not embedded logic).

**Predicate:**
```
for each atomic_step:
    core function description contains exactly one concern
    cross-cutting tags (security_relevant, observability_relevant, etc.)
    are metadata fields, not part of the function description itself
```

---

## WD4 — Determinism

**Statement:** Given the same tree and the same inputs, the same rendered output (Python code or n8n JSON) is produced every time. No step in the pipeline introduces unmanaged randomness into structure or sequencing.

**Grounding:** Determinism is a prerequisite for reproducibility and auditability in any engineered system; this is also why the Decomposition Engine Spec separates build order from execution order (Sections 4 and 6) and specifies a stable sort for parallel-safe steps rather than leaving order arbitrary.

**Applies to:** Decomposition Engine, topological sort (execution ordering), Node Mapper, JSON Exporter.

**Predicate:**
```
running the full pipeline twice on the same domain + same cached grounding
produces byte-identical trees and byte-identical rendered output (excluding
timestamps/IDs explicitly marked as non-deterministic metadata)
```

---

## WD5 — Explicit Dependencies

**Statement:** No atomic step may depend on another step's output without declaring it. Implicit ordering (steps that happen to work because of accidental sequence) is forbidden.

**Grounding:** This is the workflow-design restatement of P4 (Dependency Rule) already in the Decomposition Engine Spec, elevated here because it is also a general workflow theory principle: explicit data dependency is what the Workflow Patterns initiative (van der Aalst, ter Hofstede et al., "Workflow Patterns," 2003 onward, the standard academic catalog of workflow control-flow behavior) uses to define correct sequencing, independent of any specific tool.

**Applies to:** Decomposition Engine (P4), topological sort, n8n connection inference.

**Predicate:** identical to P4; restated here so workflow-design rules are self-contained without requiring a cross-document lookup for this specific one.

---

## WD6 — Loose Coupling, High Cohesion

**Statement:** Atomic steps within the same sub-task share a tight functional relationship (high cohesion). Atomic steps across different sub-tasks or layers interact only through declared `requires`/`produces`, never through shared hidden state (loose coupling).

**Grounding:** Coupling and cohesion as design quality metrics, Larry Constantine and Edward Yourdon, "Structured Design" (1979) — a core software architecture principle for why systems remain modifiable over time.

**Applies to:** Sub-task Generation (Stage 2), Node Mapper (a step should map to one node with clear input/output ports, not a node that silently reads global state).

**Predicate:**
```
no atomic_step references another atomic_step's internal state directly;
all cross-step data flow is via requires[]/produces[] only
```

---

## WD7 — Statelessness by Default

**Statement:** An atomic step holds no memory of prior invocations unless explicitly declared as stateful (e.g. an index/counter step). Default assumption during generation is stateless.

**Grounding:** Stateless-by-default is standard distributed systems and workflow engine design practice (reduces failure modes, enables retries/idempotency); reflected in n8n's own node model where most nodes are stateless functions of their inputs.

**Applies to:** Node Mapper, Python Renderer (function stub generation).

**Predicate:**
```
for each atomic_step not explicitly tagged stateful:
    output depends only on declared inputs (requires[]), not on any
    execution history
```

---

## WD8 — Idempotency Where the Trace Allows It

**Statement:** Where a grounded atomic step can reasonably be made idempotent (safe to run more than once with the same result, e.g. `write_chunks_to_vector_index` using an upsert rather than an append), it must be. Where the underlying real-world operation is not naturally idempotent (e.g. `send_notification`), this is fine, but the step must be tagged `non_idempotent` so retries downstream are handled deliberately, not accidentally.

**Grounding:** Idempotency as a workflow reliability principle is central to distributed workflow orchestration literature (e.g. the retry-safety requirements described in workflow engines' own design documentation, and in general distributed systems practice around at-least-once delivery).

**Applies to:** Stage 2.5 grounding simulation (Builder simulation should surface whether an operation is naturally idempotent), Node Mapper.

**Predicate:**
```
every atomic_step carries an explicit idempotent: true|false tag;
absence of the tag is a validation failure, not a default assumption
```

---

## WD9 — Control-Flow Patterns Are Named, Not Improvised

**Statement:** Whenever a tree needs branching, parallel execution, or merging logic (not pure linear sequence), it must use one of the standard control-flow patterns below, named explicitly in the tree's edge metadata — never an ad hoc, undocumented branching shape.

**Grounding:** The Workflow Patterns initiative (van der Aalst, ter Hofstede, Kiepuszewski, Barros, "Workflow Patterns," Distributed and Parallel Databases, 2003) catalogued the recurring control-flow patterns underlying essentially all workflow systems, later cross-referenced against BPMN (OMG standard) notation. Using named patterns instead of improvised branching is what makes the tree's control flow checkable and portable across renderers (Python vs. n8n).

**Named patterns in scope for ARCHITEQ v1:**
- **Sequence** — one step strictly follows another.
- **Parallel Split (AND-split)** — one step's output feeds multiple independent downstream steps simultaneously.
- **Synchronization (AND-join)** — a step waits for all of several parallel branches to complete before proceeding.
- **Exclusive Choice (XOR-split)** — exactly one of several branches is taken, based on a condition.
- **Simple Merge (XOR-join)** — multiple alternative branches converge back to one path, only one of which actually ran.

**Applies to:** Execution ordering (topological sort, Section 6 of the Decomposition Engine Spec), Node Mapper (these map directly to n8n's own branching nodes: IF/Switch for XOR-split, Merge for AND-join/XOR-join).

**Predicate:**
```
every edge in the tree with more than one outgoing or incoming connection
is tagged with one of: sequence, and_split, and_join, xor_split, xor_join
no untagged branching edge is permitted through the Validator
```

---

## WD10 — Explicit Over Implicit

**Statement:** If a rule, default, or assumption governs how a step behaves, it is written down on that step (in its `rules[]` field, per the Simulation Grounding addendum), never left as an unstated convention the renderer is expected to "just know."

**Grounding:** This generalizes P3 (Variable Exhaustion — defaults are listed, never assumed) and WD5 (dependencies declared, never implicit) into one umbrella rule covering any other form of hidden convention that might otherwise creep in during rendering.

**Applies to:** All stages; this is the rule that governs how the other rules in this document get enforced in practice.

**Predicate:**
```
no renderer (Python or n8n) may rely on an assumption not traceable to a
field on the atomic_step it is rendering
```

---

## WD11 — Depth Is Determined by Atomicity, Never a Fixed Level Count

**Statement:** The four tree-level categories (Layer, Sub-task, Atomic step, Variable) name node types, not a depth ceiling. A branch may recurse many levels within one category before a leaf genuinely passes the Atomicity Test (P1). Depth stops when the atomicity test passes, never when a level-count target is reached.

**Grounding:** Work Breakdown Structure practice (Project Management Institute, "Practice Standard for Work Breakdown Structures") — a WBS decomposes to arbitrary depth until reaching a "work package," the smallest independently verifiable unit; depth is never fixed in advance.

**Applies to:** Stage 3 (Atomic Step Generation), any recursive split triggered by the Atomicity Test.

**Predicate:** as specified in `ARCHITEQ-Recursive-Depth-and-Completion-Tracking.md` Section 1.

---

## WD12 — Completion Status Rolls Up, Never Set Independently

**Statement:** Every node in the tree carries a `[ ]`/`[-]`/`[x]` completion status. A non-leaf node's status is always computed from its children's statuses and can never be manually set to `[x]` while any child is incomplete.

**Grounding:** The WBS "100% Rule" (Practice Standard for Work Breakdown Structures, PMI) — a parent element's completion must be fully accounted for by the sum of its children, nothing implicit, nothing double-counted.

**Applies to:** Every node in the Workflow Tree; the same rule applies to the Component Tree via CD9.

**Predicate:** as specified in `ARCHITEQ-Recursive-Depth-and-Completion-Tracking.md` Section 3.

---

## Summary Table

| ID | Rule | Grounding |
|----|------|-----------|
| WD1 | Single Source of Truth | Relational data modeling (Codd) |
| WD2 | No Silent Failure | SRE / reliability engineering practice |
| WD3 | Separation of Concerns | Dijkstra, 1974 |
| WD4 | Determinism | Reproducibility/audit engineering practice |
| WD5 | Explicit Dependencies | Workflow Patterns (van der Aalst et al.); restates P4 |
| WD6 | Loose Coupling, High Cohesion | Constantine & Yourdon, Structured Design, 1979 |
| WD7 | Statelessness by Default | Distributed systems / workflow engine design practice |
| WD8 | Idempotency Where Possible | Distributed systems retry-safety practice |
| WD9 | Named Control-Flow Patterns | Workflow Patterns initiative + BPMN (OMG) |
| WD10 | Explicit Over Implicit | Generalizes P3 and WD5 |
| WD11 | Depth Determined by Atomicity, Never Fixed Level Count | WBS Practice Standard (PMI) |
| WD12 | Completion Status Rolls Up, Never Set Independently | WBS 100% Rule (PMI) |

This file is referenced from `RULES-INDEX.md`. The next files in the corpus (governance, UI design, dev process, decomposition, prompting, node translation) follow the same statement/grounding/applies-to/predicate template established here.
