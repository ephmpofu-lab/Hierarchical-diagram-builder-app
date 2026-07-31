# ARCHITEQ System — Build Directive (New Direction, Supersedes Prior Instructions)

## 0. Direction Change Notice

This document replaces any prior direction given for this application. Ignore earlier scope, earlier task breakdowns, and earlier assumptions about what the tool does. Build strictly to what is written below. If anything here conflicts with earlier context in the repo, this document wins.

**RAG is an example domain only, not the fixed scope.** Everywhere this document uses "RAG" (intent parsing example, domain checklist in 4.4, build priority in section 6), treat it as the first domain used to prove the pipeline out, not the only domain the system supports. The Decomposition Engine, Validator, Principles module, Node Mapper, and both renderers must all be domain-agnostic by design — RAG's checklist is just the first entry in `rules/domain_checklists/`. Do not hardcode RAG-specific logic anywhere outside that one checklist file and the example task tree.

---

## 1. What the App Does (Plain Description)

A user states an intent, e.g. "I want to develop a RAG."

The system:

1. Parses the intent into a domain (e.g. `RAG`).
2. Breaks that domain down into a full task tree: Layer → Sub-task → Atomic step → Variable/parameter. Nothing is skipped. Every atomic step and every variable is listed, including ones with sensible defaults.
3. Lets the user pick one of exactly two output modes: `python` or `n8n`. Both modes render from the same task tree — never two separate trees.
4. Renders the chosen output:
   - **Python mode**: ordered code blocks / function stubs, sequenced correctly, atomic-step variables become function args/config.
   - **n8n mode**: a real, importable n8n workflow JSON (`nodes[]`, `connections{}`, positions) built from actual n8n node schemas — not illustrative/fake nodes.
5. Renders a visual diagram (SVG, using the existing diagram builder) from the same node/edge structure used for the n8n JSON, so diagram and importable file never diverge.

No unnecessary chatter in output. Steps are shown sequentially. Depth of decomposition goes to the smallest atomic thing — last variable, last parameter.

---

## 2. Core Architectural Rule

**One task tree, two renderers.** The task tree is the single source of truth. Python renderer and n8n renderer both consume it. The n8n JSON exporter and the SVG diagram renderer both consume the same mapped node/edge list. Never let any of these fork into independent representations.

---

## 3. Pipeline (End to End)

```
User intent (free text)
        ↓
Intent Parser → { domain, confidence, extracted_constraints }
        ↓
Decomposition Engine → proposes task tree
        ↓
Validator → checks tree against Decomposition Principles (P1–P7) + domain checklist
        ↓ (fail → back to engine with specific violation; pass → tree frozen)
Frozen Task Tree
        ↓
Output Mode Selector: python | n8n  (user picks one)
        ↓                                   ↓
Python Renderer                    Node Mapper (atomic step → real n8n node type + params)
   ↓                                         ↓                          ↓
Ordered code blocks              JSON Exporter (importable      SVG Renderer (visual
                                   n8n workflow file)              diagram, same nodes/edges)
```

---

## 4. Component Specs

### 4.1 Intent Parser
- Input: free text.
- Output: `{domain: string, confidence: float, extracted_constraints: object}`.
- Implementation: rule-based/keyword classifier first; LLM fallback only when rule-based confidence is low.

### 4.2 Decomposition Engine
- Input: `domain`.
- Output: proposed task tree, structured as:
  - `Layer` → `Sub-task` → `Atomic step` → `Variable/parameter`
- Must be a stored, versioned taxonomy (JSON tree per domain), not regenerated freely each run. Reproducibility and auditability depend on this.
- Breadth-first before depth-first: all sub-tasks of a layer must exist before any of them decomposes further.

### 4.3 Decomposition Principles (P1–P7) — Governing Rules Module
Stored as machine-checkable predicates in `rules/decomposition_principles.json`, not prose. The Validator runs these against every proposed tree.

- **P1 — Atomicity Rule**: A step is atomic only if it has exactly one action, one input, one output. If it needs "and" to describe it, split it further.
- **P2 — No Skip Rule**: Breadth-first only. Every sub-task of a layer must exist before any sub-task decomposes into atomic steps.
- **P3 — Variable Exhaustion Rule**: Every configurable parameter an atomic step touches must be listed explicitly, even if it has a default value (e.g. `chunk_overlap=50` is listed, never assumed silently).
- **P4 — Dependency Rule**: Every atomic step declares `requires: [step_ids]` and `produces: [output_name]`. Both fields are mandatory. This is what drives correct sequencing and node-connection inference.
- **P5 — No Orphan Rule**: Every `produces` output must be consumed downstream or explicitly flagged `terminal_output`. An unconsumed output means a missing step — reject the tree.
- **P6 — Tool Agnosticism Rule**: Steps are named by function, never by implementation (e.g. "generate embedding vector," not "call OpenAI API"). Implementation binding happens only at render time (Python/n8n), never inside the tree.
- **P7 — Coverage Checklist Rule**: Each domain has a mandatory list of layers that must all be present and non-empty. Tree is rejected if any mandatory layer is empty.

### 4.4 Domain Checklists (P7 data)
- Location: `rules/domain_checklists/{domain}.json`
- RAG checklist (example domain, mandatory layers, all must be present): `Ingestion, Preprocessing, Embedding, Storage, Retrieval, Augmentation, Generation, Evaluation`
- RAG is only the first proof-of-concept domain. The file format and validation logic must generalize to any domain the user later defines (e.g. a different ML pipeline, a data engineering pipeline, an automation workflow unrelated to RAG). Do not design the checklist schema around RAG-specific layer names.
- New domains beyond RAG follow the same file pattern, added incrementally.
- **Open decision, ask the user before building further domains**: should new-domain checklists be hand-authored and locked by the user, or should the app propose a first-draft checklist per new domain for one-time user approval before it becomes usable? Do not assume either — confirm.

### 4.5 Validator
- Separate module from the Decomposition Engine (do not merge these).
- Input: proposed tree.
- Checks: P1–P7 + relevant domain checklist.
- Output: pass (tree frozen, moves to rendering) or fail (specific violation returned to Decomposition Engine for correction).
- Nothing reaches a renderer without passing validation.

### 4.6 Output Mode Selector
- Exactly two modes: `python`, `n8n`. User picks one per run.
- Both modes are fed by the same frozen task tree — this is a hard constraint, not a suggestion.

### 4.7 Python Renderer
- Input: frozen task tree.
- Output: ordered code blocks / function stubs, sequenced by the tree's dependency graph (`requires`/`produces` chains from P4).
- Atomic-step variables become function arguments/config values, not hardcoded.

### 4.8 Node Mapper (n8n path, shared by JSON exporter and SVG renderer)
- Input: frozen task tree.
- Output: mapped node list — each atomic step becomes a real n8n node type with pre-filled parameters sourced from the tree's variables.
- **Node schema source is real, not hallucinated.** Source options to choose from (confirm with user before building):
  - Vendored JSON pulled from n8n's own node definition repo, or
  - Live schema pulled from a running n8n instance's API, if the user has one.
- **Fallback rule for steps with no clean 1:1 n8n node** (e.g. "chunk document"): map to a `Code`/`Function` node, with the step's logic embedded as JS in that node's parameters. This fallback is mandatory, not optional — every atomic step must resolve to *some* node, known or fallback.
- Node positions and connection logic are computed once here and reused identically by both downstream consumers (4.9 and 4.10). Do not compute positions/connections twice.

### 4.9 JSON Exporter (n8n path)
- Input: mapped node list + connections + positions from 4.8.
- Output: valid, importable n8n workflow JSON (`nodes[]`, `connections{}`, `positions`).
- Must be directly importable into n8n without manual fixing.

### 4.10 SVG Renderer (visual diagram)
- Input: same mapped node list + connections + positions from 4.8 (not a separately generated layout).
- Output: SVG diagram using the existing diagram builder (Tool A / hierarchical diagram builder already in the codebase).
- Layout optimized for human readability, but must represent the exact same graph as the JSON export — no divergence.

---

## 5. Output Behavior Rules (apply to all rendered output, both modes)

- Steps are always shown **sequentially**.
- No unnecessary text, no preamble, no filler — output is the breakdown/render itself.
- Decomposition depth always goes to the smallest atomic thing: last variable, last parameter. Nothing is left at a "should be obvious" level.
- Whichever mode is chosen (Python or n8n), the sequencing and completeness must be traceable back to the same underlying task tree.

---

## 6. Build Priority Order (for Claude Code)

1. Task tree schema + storage format (JSON, versioned, per domain).
2. Decomposition Principles module (`rules/decomposition_principles.json`) as machine-checkable predicates.
3. RAG domain checklist (`rules/domain_checklists/rag.json`) — built first as the proof-of-concept domain, using domain-agnostic schema (see 4.4).
4. Validator module (standalone, checks P1–P7 + checklist).
5. Decomposition Engine (produces trees, sends to Validator, handles rejection/correction loop).
6. Intent Parser (rule-based first, LLM fallback).
7. Python Renderer.
8. Node Mapper (with fallback rule for unmapped steps) — **blocked until node schema source is confirmed with user (see 4.8).**
9. JSON Exporter + SVG Renderer, both consuming Node Mapper output directly.
10. Output Mode Selector UI (python | n8n).

---

## 7. Explicit Open Questions Before Full Build (do not assume, ask the user)

- Node schema source: vendored GitHub JSON vs. live n8n instance API (section 4.8).
- Domain checklist authoring process for future domains beyond RAG: user-authored/locked vs. app-drafted/user-approved (section 4.4).
