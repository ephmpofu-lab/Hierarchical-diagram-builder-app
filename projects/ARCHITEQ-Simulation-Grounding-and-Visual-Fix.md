# ARCHITEQ — Simulation Grounding & Visual Tree Fix

Addendum to `ARCHITEQ-Decomposition-Engine-Spec.md`. This document amends Section 4 (Build Order) and Section 5 (Atomicity Test) of that spec, and corrects the SVG rendering requirement. Where this conflicts with the current running app, this document wins.

---

## 1. Diagnosis

Two separate defects observed in current output:

**A. Decomposition is abstract, not grounded.** Steps like `collect_raw_documents` sound atomic but are not. They fail the Atomicity Test's own criterion 5 (maps to exactly one implementation unit) because in a real build, "collecting raw documents" is actually several distinct operations: getting a file list, selecting an upload source, reading file bytes, detecting format, extracting text, handling unsupported formats. The engine generated a plausible-sounding label instead of deriving steps from what actually happens when a human or a developer does this task. Nothing caught this because the Atomicity Test was applied to invented descriptions, never checked against a real trace of the work.

**B. Visual output is stacked cards, not a tree.** Layers currently render as flat panel headers with buttons underneath — no branching, no connecting lines, no visible parent/child structure. This does not reflect the four-level hierarchy (Layer to Sub-task to Atomic step to Variable) that the Decomposition Engine Spec Section 2.2 (C4 model) already defines. The existing hierarchical diagram builder (Tool A, from the SKAIDO project) supports node/edge rendering with connecting lines and should be the renderer used here — the current flat card layout is not that renderer, or is bypassing it.

---

## 2. Fix A: Grounding Simulation Layer (new pipeline stage)

Insert a new stage between Stage 2 (Sub-task Generation) and Stage 3 (Atomic Step Generation) in the Decomposition Engine Spec's build order.

```
STAGE 2.5 — Grounding Simulation (new)

  for EVERY sub-task generated in Stage 2 (breadth-first, all sub-tasks):

    run OPERATOR SIMULATION:
      simulate a real person performing this sub-task by hand today, with no
      automation. Output an ordered list of the actual micro-actions a human
      would take (e.g. for "collect raw documents": choose upload source,
      select files on device, confirm upload, see upload progress, see
      confirmation or error).

    run BUILDER SIMULATION:
      simulate a developer implementing this sub-task in code. Output an
      ordered list of the actual implementation-level operations needed to
      automate it (e.g. for the same sub-task: receive file object, validate
      file type, validate file size, read file bytes, detect encoding,
      extract text content, handle unsupported format, handle read error).

    merge both traces into one ordered candidate action list per sub-task.
    Builder trace is primary (it is what actually becomes code/nodes).
    Operator trace is used to catch anything a real user still needs that
    the Builder trace omitted (e.g. a progress indicator, a confirmation step).

  do not proceed to Stage 3 until every sub-task has a merged, grounded trace.
```

This stage exists specifically so atomic steps are *derived from* a real trace of actual operations, not invented as abstract descriptions and checked after the fact.

### Stage 3 revised (Atomic Step Generation)

```
for EVERY sub-task's grounded trace (breadth-first across all sub-tasks):
  for each candidate action in the trace:
    apply the Atomicity Test (Section 5 of the Decomposition Engine Spec)
    - passes all 5 criteria as-is: promote directly to atomic step
    - fails because too broad (e.g. "collect_raw_documents"): split further,
      using the trace itself as the source of the split, never invented
      sub-actions
    - fails because too granular (does not correspond to any real function
      or node on its own): merge with the adjacent trace action it belongs to
  repeat until every resulting step passes all 5 criteria against the ACTUAL
  trace, not an abstract description generated without grounding.
```

Concrete effect on the example shown: `collect_raw_documents` becomes something like `select_upload_source`, `receive_uploaded_files`, `validate_file_type`, `validate_file_size`, `read_file_bytes`, `extract_text_content`, `handle_unsupported_format` — each one mapping to exactly one function call or one n8n node, each independently testable.

---

## 2a. Caching, Versioning, and Refinement

Stage 2.5 (Grounding Simulation) runs **once per domain, at domain checklist authoring time** — not on every user's "I want to build a ___" request. Results are cached and reused across all future runs of that domain.

**Storage:** grounded traces are stored alongside the domain checklist file, e.g. `rules/domain_checklists/rag.grounding.json`, keyed by sub-task ID. Each entry carries a `grounding_version` field (starting at 1).

**What this means at request time:** when a user's intent resolves to a domain that already has a cached grounding file, Stage 2.5 is skipped entirely — Stage 3 reads directly from the cached trace. Grounding simulation only runs live if a domain has no cached grounding file yet (i.e. its checklist was just authored and never grounded).

**Refinement mechanism (for when a cached trace turns out wrong or incomplete):**

- Refinement is manually triggered, never automatic. Re-running Stage 2.5 silently on a schedule risks producing a different tree for the same domain without anyone noticing.
- Trigger it at the level of a single sub-task, not the whole domain, wherever possible: `regroup <domain> <sub_task_id>` re-runs Operator + Builder simulation for just that sub-task, increments its `grounding_version`, and requires explicit confirmation before overwriting the cached entry.
- If a domain checklist itself changes (a layer is added/renamed), any sub-task whose Input/Output Contract changed as a result must be re-grounded, since its old trace was derived from a contract that no longer applies.
- Keep prior `grounding_version` entries rather than deleting them, so a regression can be traced back to which regrounding introduced it.

## 3. Fix B: Node Schema Gets a `rules` Field

Every atomic step already declares `requires` and `produces` (P4). Add a third mandatory field:

- **`rules`**: the validation or business constraints governing this step. Example: `select_upload_source` might have `rules: ["accepted formats: pdf, docx, txt", "max file size: 50MB"]`.

This is not optional metadata — it is what makes the eventual n8n node or Python function actually correct, not just structurally present. Update P4 in `ARCHITEQ-Decomposition-Engine-Spec.md` to read: **P4 — Dependency & Rules Rule**: every atomic step declares `requires[]`, `produces[]`, and `rules[]`. All three fields are mandatory, not just the first two.

---

## 4. Fix C: Layer Repetition Is Allowed

Stage 1 (Layer Instantiation) currently implies one instance per mandatory layer. Amend this: a layer MAY repeat if the grounded trace justifies it (e.g. a domain that ingests from two structurally different sources needs two Preprocessing branches, not one that awkwardly covers both). The domain checklist (P7) is satisfied as long as at least one instance of each mandatory layer exists — repetition is permitted where the real workflow branches, not required by default, and never used to avoid genuine atomic decomposition.

---

## 5. Fix D: Visual Rendering Requirement

The SVG output must be an actual branching tree, not stacked panels:

- Use the existing Tool A hierarchical diagram builder (SKAIDO project) as the renderer. Do not build a separate flat-card layout for this.
- Render all four levels with visible connecting lines (edges) between parent and child: Layer nodes at the top, branching to Sub-task nodes, branching to Atomic step nodes.
- Each of the four C4 levels (Section 2.2 of the Decomposition Engine Spec) gets a visually distinct treatment (e.g. size and/or color coding) so the hierarchy is legible at a glance, not just implied by grouping under a header.
- Variables attach to their atomic step node (e.g. shown on click/hover or in the detail panel per the UI directive), not rendered as separate top-level boxes.
- This is the same node/edge data structure used for the n8n JSON export (per the Build Directive's Node Mapper, Section 4.8) — the tree diagram and the n8n workflow must visibly correspond to the same underlying graph.

---

## 6. Why This Matters for n8n Specifically

Every atomic step becomes one n8n node. If the atomic step is not actually atomic (Fix A), the resulting node is either doing too much (a Code node silently containing several operations) or the mapping to a real n8n node type becomes impossible to get right, because no single real node does five things at once. Grounding decomposition in a simulated trace before Atomicity Test is what makes the eventual node-per-step mapping (Build Directive Section 4.8) actually hold in practice, not just in the abstract tree.
