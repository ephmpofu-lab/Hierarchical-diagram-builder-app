# ARCHITEQ Decomposition Engine — Full Technical Spec

This document is an addendum to `ARCHITEQ-Build-Directive.md`. It does not replace it. Where the two overlap, this document is the authoritative, detailed version — implement from this file for anything covering decomposition principles, reference architecture grounding, and the build/execution algorithm.

This is a spec, not a set of principles to interpret. Every rule below is written as a predicate the Validator can run against a tree, or as a fixed procedure the Decomposition Engine follows step by step. Nothing here should be re-interpreted or re-derived at build time — implement it as written.

---

## 1. Why This Document Exists

General knowledge of software architecture frameworks (SOLID, TDSP, C4, Well-Architected) is not sufficient on its own, because it produces *plausible* application, not *consistent* application. This system requires that the same domain input always produces the same validated tree. That requires fixed, encoded predicates — not principles applied fresh each run. Everything below is the encoded version.

---

## 2. Reference Architecture Module

Location: `rules/reference_architectures/`

Every domain checklist must trace to a named, citable framework. No checklist is authored freely. Each checklist file carries a `derived_from` field naming the framework and mapping rationale.

### 2.1 `rules/reference_architectures/tdsp.json`
Used for ML/AI pipeline domains (RAG, CV, fine-tuning, forecasting, etc.).
Canonical stage order (Microsoft Team Data Science Process, adapted to layer form):

```
1. Business Understanding      → maps to: Intent/Requirements layer
2. Data Acquisition & Ingestion → maps to: Ingestion layer
3. Data Preprocessing           → maps to: Preprocessing layer
4. Feature Engineering          → maps to: Embedding/Feature layer (domain-specific naming)
5. Modeling                     → maps to: Model/Retrieval/Generation layer (domain-specific naming)
6. Deployment                   → maps to: Storage/Serving layer
7. Evaluation & Acceptance      → maps to: Evaluation layer
```

A domain checklist for an ML/AI domain must map every one of its layers back to one of these seven stages. If a proposed layer doesn't map to any stage, it is rejected — either it's a cross-cutting concern (see Section 3) or it doesn't belong in the vertical checklist.

### 2.2 `rules/reference_architectures/c4_model.json`
Used for structural nesting rules across ALL domains (not domain-specific).

```
Level 1 — Context:   the domain itself (e.g. "RAG system") — single node, no internals shown
Level 2 — Container:  the Layers (Ingestion, Embedding, Storage...) — deployable/runnable units
Level 3 — Component:  the Sub-tasks within a layer — logical groupings of atomic steps
Level 4 — Code:       the Atomic steps — one-to-one with a function or n8n node
```

This fixes the nesting depth for every domain: exactly 4 levels, always in this order (Layer → Sub-task → Atomic step → Variable is Level 4 plus its parameters, not a 5th C4 level). The Decomposition Engine must not introduce intermediate levels beyond this structure.

### 2.3 `rules/reference_architectures/well_architected.json`
Used for the cross-cutting concerns overlay (Section 3). Five pillars, each with a machine-checkable tag.

```json
{
  "pillars": [
    { "id": "security", "tag": "security_relevant" },
    { "id": "reliability_observability", "tag": "observability_relevant" },
    { "id": "performance_cost", "tag": "performance_relevant" },
    { "id": "operational_excellence", "tag": "ops_relevant" },
    { "id": "governance_compliance", "tag": "governance_relevant" }
  ]
}
```

### 2.4 `rules/reference_architectures/solid.json`
Used only to formally ground the Atomicity Test (Section 5). SRP (Single Responsibility Principle) is the direct source of the "exactly one implementation unit" criterion. Not applied elsewhere — SOLID is a code-level principle set, not a task-tree structuring framework, and must not be stretched to justify layer or sub-task design.

---

## 3. P8 — Cross-Cutting Concerns Rule (new principle, extends P1–P7)

A tree is not valid until every layer has been checked against the five Well-Architected pillars (2.3), even if the domain's vertical checklist doesn't mention them.

**Predicate:**
```
for each pillar in well_architected.pillars:
    if count(atomic_steps where pillar.tag == true) == 0:
        REJECT tree, reason: f"No atomic step addresses {pillar.id} anywhere in the tree"
```

This does not mean every layer needs every pillar — it means every pillar must appear *somewhere* in the whole tree, at least once. Examples of what satisfies each tag:

- `security_relevant`: e.g. an atomic step for access control on a vector DB, API key handling, input sanitization.
- `observability_relevant`: e.g. logging retrieval scores, tracing a generation call, metrics emission.
- `performance_relevant`: e.g. setting `top_k`, batching embedding calls, caching.
- `ops_relevant`: e.g. deployment step, health check, retry/backoff config.
- `governance_relevant`: e.g. audit logging, data retention step, compliance check on stored data.

The Decomposition Engine should attempt to tag steps with these during Stage 3/4 generation (Section 4). The Validator enforces the predicate above regardless of whether tagging was automatic or required a correction loop.

---

## 4. Build Order — Deterministic Procedure

This is the exact sequence the Decomposition Engine executes. Breadth-first, top-down, four stages. No stage begins until the prior stage is complete across the *entire* tree — not per-branch.

```
STAGE 0 — Domain Resolution
  input: domain name (from Intent Parser)
  action: load rules/domain_checklists/{domain}.json
  output: ordered mandatory Layer list (this list is fixed, not generated)

STAGE 1 — Layer Instantiation
  action: create every Layer node from the checklist, in order. All of them.
  do not proceed to Stage 2 until every mandatory layer exists as a node.

STAGE 2 — Sub-task Generation
  for EVERY layer (breadth-first across all layers, not one layer to completion):
    load the layer's Input Contract and Output Contract
      (defined per-layer in the domain checklist: what it consumes, what it must produce)
    generate sub-tasks as the minimal set of transformations needed to move
      from Input Contract to Output Contract
  do not proceed to Stage 3 until every layer has its sub-tasks generated.

STAGE 3 — Atomic Step Generation
  for EVERY sub-task (breadth-first across all sub-tasks):
    recursively apply the Atomicity Test (Section 5)
    if candidate step fails the test: split it and re-test each half
    repeat until every resulting step passes
  do not proceed to Stage 4 until every sub-task's atomic steps are fully generated.

STAGE 4 — Variable Exhaustion
  for EVERY atomic step:
    look up the full parameter list from the implementation schema
      (Python function signature, or n8n node schema — see ARCHITEQ-Build-Directive.md 4.8)
    list every parameter, including ones with defaults. Never omit a default silently.
  do not mark the tree "generated" until every atomic step has its full variable list.

→ tree passed to Validator (checks P1–P8 + domain checklist + cross-cutting overlay)
```

Breadth-first at every stage is what makes P2 (No Skip) mechanically checkable: the Validator can confirm no branch went deeper than the others before every branch reached the same stage.

---

## 5. The Atomicity Test (Stage 3 predicate, grounded in SOLID/SRP)

A candidate step is atomic only if **all five** hold:

1. **Single verb, single object** — description has exactly one action governing one direct object. If the description needs "and," it fails.
2. **Single named input** — consumes exactly one input artifact. A composite object counts as one only if genuinely passed as a single object (e.g. "the document," not "the document and its metadata" as two separate things unless metadata is bundled inside the document object).
3. **Single named output** — produces exactly one output artifact.
4. **No hidden implementation choice** — if executing the step still requires choosing between sub-approaches with genuinely different inputs/outputs, it is not atomic yet. Split into the choice point plus each branch.
5. **Maps to exactly one implementation unit** — the step corresponds to exactly one function call (Python) or one node (n8n). Not "roughly one." This is checked directly against the implementation schema already loaded in Stage 4/Node Mapper — it is a lookup, not a judgment call. This criterion is the direct application of SOLID's Single Responsibility Principle to a task-tree node.

If any one of the five fails, split the candidate step and re-run the test on each resulting piece.

---

## 6. Execution/Output Order — Topological Sort (distinct from Build Order)

Build order (Section 4) exists to make the tree complete and checkable. It is NOT the order shown to the user or used for code/node sequencing. That is a separate, second computation, run once the tree is frozen:

```
1. Take the frozen tree's full set of atomic steps with their requires[]/produces[] (P4).
2. Run a topological sort on this dependency graph.
3. Layer order in the checklist is itself just the first topological pass —
   e.g. Ingestion precedes Embedding because Embedding's Input Contract requires
   Ingestion's Output Contract.
4. Within a layer, sub-task and atomic-step order is determined purely by
   requires[]/produces[] edges. Whatever step produces what another step needs
   goes first — no exceptions.
5. If two steps have no dependency relationship to each other (parallel-safe),
   their relative order is arbitrary but must be resolved deterministically
   (stable sort by step ID) so identical re-runs never shuffle output.
```

This topological order is what both the Python Renderer and the Node Mapper (n8n path) consume for sequencing. The build order in Section 4 is discarded after validation — it only exists to construct and check the tree, never to display or execute it.

---

## 7. Validator — Full Check List (updated)

The Validator now runs three categories of checks against every frozen tree, in this order:

```
1. Structural principles: P1–P8
     P1  Atomicity                (Section 5, all 5 criteria)
     P2  No Skip                  (breadth-first build order was followed — Section 4)
     P3  Variable Exhaustion      (Stage 4 completed for every atomic step)
     P4  Dependency               (requires[]/produces[] present on every atomic step)
     P5  No Orphan                (every produces[] is consumed or terminal_output)
     P6  Tool Agnosticism         (no implementation-specific naming in the tree itself)
     P7  Domain Checklist Coverage (every mandatory layer present, non-empty)
     P8  Cross-Cutting Coverage   (Section 3 predicate — all 5 pillars tagged somewhere)

2. Reference architecture conformance
     - every layer maps to a named TDSP stage (2.1) OR is explicitly marked
       cross-cutting (2.3) — no orphan layers with no framework justification
     - nesting depth matches C4's 4 levels exactly (2.2) — no extra intermediate levels

3. Domain-specific checklist (rules/domain_checklists/{domain}.json)
```

Any failure at any category returns a specific violation to the Decomposition Engine, naming exactly which predicate failed and on which node. The tree is never partially accepted — pass all three categories or return to Stage 2/3/4 for correction.

---

## 8. Summary of File Structure (final)

```
rules/
  decomposition_principles.json      # P1–P8 as machine-checkable predicates
  reference_architectures/
    tdsp.json                        # Section 2.1
    c4_model.json                    # Section 2.2
    well_architected.json            # Section 2.3
    solid.json                       # Section 2.4 (Atomicity Test grounding only)
  domain_checklists/
    rag.json                         # example domain, derived_from: tdsp + RAG stack
    {other_domain}.json              # same pattern, added incrementally
```

---

## 9. What Claude Code Should NOT Do

- Do not re-derive TDSP, C4, Well-Architected pillars, or SOLID from general knowledge at build time. Use the fixed mappings in Section 2 exactly as written.
- Do not treat build order (Section 4) and execution order (Section 6) as the same thing, or compute them with the same code path.
- Do not accept a tree into rendering (Python or n8n) if it hasn't passed all three Validator categories in Section 7.
- Do not add layers, stages, or nesting levels beyond what Section 2.1/2.2 define, even if it seems like it would make a specific domain's tree "more complete." If a domain genuinely needs something extra, it belongs in that domain's checklist file with its own `derived_from` justification — not as a silent addition to the core framework.
