# PRD: ARCHITEQ

Written using the Universal PRD Framework. This is the PRD that feeds the Plan → Build → Test → Commit loop defined in `ARCHITEQ-UI-and-Dev-Loop-Directive.md`. Read alongside the three existing directive docs, this PRD is the source of the numbered requirements those docs should be built against.

---

## 1. Problem Statement

Building a system from scratch (a RAG pipeline, an automation workflow, or any similarly structured domain) requires breaking the work down into every step, down to individual parameters, before implementation can start correctly. People doing this manually either stop decomposing too early (missing steps, missing parameters, missing cross-cutting concerns like security or observability) or decompose inconsistently between attempts, producing plans that can't be checked, reproduced, or handed to another builder with confidence. Separately, once a plan exists, there is no single tool that renders the same plan into both a runnable Python implementation and an importable n8n workflow, so people rebuild the same logic twice by hand when they want both options.

## 2. Goal

Given a plain-language intent ("I want to develop a ___"), ARCHITEQ produces one complete, validated, atomic task breakdown, and renders it into either a Python implementation or an importable n8n workflow (user's choice) plus a matching visual diagram, without requiring the user to manually enumerate any step.

## 3. Non-Goals

- ARCHITEQ does not execute the generated Python code or deploy the generated n8n workflow. It produces the artifacts; running them is the user's action, outside this system.
- ARCHITEQ does not support output targets other than Python and n8n in this version. No other language, no other automation platform.
- ARCHITEQ does not generate a task tree for a domain that has no checklist file yet without first surfacing that gap to the user (see Open Questions, item 1). It does not silently invent a domain checklist.
- ARCHITEQ is not a general-purpose chat assistant. The persistent input on the canvas (per the UI directive) only refines the current tree; it does not serve as an open-ended conversational agent.
- ARCHITEQ does not host multi-user collaboration, permissions, or team features in this version. Single-user tool.
- ARCHITEQ does not maintain a live connection to a running n8n instance. Node schemas are vendored, not fetched live (per the node-schema decision already made).

## 4. Requirements

### Intent and Decomposition
- **R1.** The system accepts a free-text intent and resolves it to a domain, or flags it as unresolved if no matching domain checklist exists.
- **R2.** The system generates a task tree with exactly four levels: Layer, Sub-task, Atomic step, Variable, per the C4-derived nesting rule.
- **R3.** Every generated tree includes all mandatory layers from the resolved domain's checklist file, none empty.
- **R4.** Every atomic step in a generated tree passes all five Atomicity Test criteria before being accepted into the tree.
- **R5.** Every atomic step lists every one of its parameters, including ones with default values, none omitted silently.
- **R6.** Every atomic step declares both `requires` and `produces` fields.
- **R7.** Every `produces` output in a tree is either consumed by another step or explicitly marked `terminal_output`.
- **R8.** Every tree includes at least one atomic step tagged against each of the five Well-Architected pillars (security, reliability/observability, performance/cost, operational excellence, governance/compliance) somewhere across the whole tree.
- **R9.** A tree that fails any check in R3 to R8 is rejected by the Validator and returned to the Decomposition Engine with the specific violated rule and node named, not a generic failure.
- **R10.** The displayed/rendered order of steps is a topological sort of the `requires`/`produces` graph, computed separately from the breadth-first build order used to construct the tree.

### Output Rendering
- **R11.** The user selects exactly one output mode, Python or n8n, per generated tree.
- **R12.** The Python renderer produces ordered code blocks or function stubs, sequenced by R10's topological order, with atomic-step variables exposed as function arguments or config values.
- **R13.** The n8n renderer maps every atomic step to a real n8n node type sourced from the vendored node schema file, or to a Code/Function node fallback if no dedicated node type exists for that step.
- **R14.** The n8n renderer produces a workflow JSON file that is directly importable into n8n without manual correction.
- **R15.** The visual diagram (SVG) is generated from the same node, edge, and position data used to produce the n8n JSON in R14, not from an independently computed layout.

### Interface
- **R16.** The application has exactly two user-facing screens (Home/Canvas merged, and Canvas populated state) plus one hidden Settings screen, per the UI directive.
- **R17.** Submitting an intent on the Home/Canvas screen populates the tree on the same screen without navigating to a different page.
- **R18.** Clicking any node on the populated canvas opens a detail panel showing that node's variables, dependencies, and rendered output once a mode is selected, without hiding the canvas behind it.
- **R19.** A persistent input remains available on the canvas at all times to submit refinements to the current tree without returning to the empty-state screen.

### Grounding Simulation
- **R22.** The Operator/Builder grounding simulation (per `ARCHITEQ-Simulation-Grounding-and-Visual-Fix.md`) runs once per domain, at domain checklist authoring time, and its output is cached alongside that domain's checklist file. It does not re-run on ordinary user intent requests.
- **R23.** A cached grounding trace can be refined at the level of a single sub-task, on manual trigger only, producing an incremented `grounding_version` rather than a silent overwrite.

### Governance
- **R20.** Every domain checklist file declares a `derived_from` field naming the reference framework and mapping rationale used to justify its layer list.
- **R21.** No layer or nesting level is added to a tree beyond what the C4-derived structure (Layer, Sub-task, Atomic step, Variable) defines, regardless of domain.

## 4a. Modules

Requirements are grouped into modules so Plan/Build/Test/Commit cycles and `PROGRESS.md` can track status at a buildable grain, not just as one long requirement list. Module order follows the dependency order in `ARCHITEQ-Build-Directive.md` Section 6 — each module is buildable once the ones before it are committed.

- **Module 1: Domain Resolution & Task Tree Schema** — R1, R2
- **Module 2: Decomposition Principles & Rules Engine (P1 to P8)** — R4, R5, R6, R7, R21
- **Module 3: Domain Checklists & Reference Architecture Mapping** — R3, R20
- **Module 4: Validator** — R9
- **Module 5: Decomposition Engine (build order, Stages 0 to 4)** — depends on Modules 1 to 4, no new R-numbers of its own, implements R1 to R9 end to end
- **Module 6: Execution Ordering (topological sort)** — R10
- **Module 7: Python Renderer** — R11 (mode selection), R12
- **Module 8: n8n Node Mapper & Renderer** — R13, R14
- **Module 9: Visual Diagram Renderer** — R15
- **Module 10: UI Shell (Home/Canvas, Detail Panel, Persistent Input)** — R16, R17, R18, R19

Each module is the unit `PROGRESS.md` tracks. A module is `[x]` complete only when every requirement listed under it has passed Test and been Committed.

## 5. Constraints

- Backend built in Python (FastAPI), frontend in vanilla JS/SVG, per existing project direction.
- n8n node schemas are sourced from n8n's vendored GitHub node definitions, pinned to a specific tagged release, stored as static JSON. No live-instance schema fetching.
- Decomposition Principles (P1 to P8), reference architecture mappings (TDSP, C4, Well-Architected, SOLID), and domain checklists are all stored as versioned JSON files, not regenerated at runtime.
- UI must follow the collapsed-screen structure in `ARCHITEQ-UI-and-Dev-Loop-Directive.md` Part 1. No additional pages without first checking whether the workflow can be a state or panel instead.
- Development must follow the PRD → Plan → Build → Test → Commit loop in `ARCHITEQ-UI-and-Dev-Loop-Directive.md` Part 2, one build-priority item at a time.
- Documents and generated output text must follow existing standing formatting rules: no en-dashes, no underscores in prose, no AI-sounding filler phrases, concise text.

## 6. Dependencies

- Depends on `ARCHITEQ-Build-Directive.md` for the overall pipeline and component specs.
- Depends on `ARCHITEQ-Decomposition-Engine-Spec.md` for the exact build algorithm, Atomicity Test, and reference architecture mappings.
- Depends on `ARCHITEQ-UI-and-Dev-Loop-Directive.md` for screen structure and dev process.
- Depends on the existing Tool A hierarchical diagram builder (Python FastAPI backend, vanilla JS/SVG frontend, from the SKAIDO Architect project) for the SVG rendering component in R15. `Confirmed` as an existing asset, not to be rebuilt from scratch.
- Depends on n8n's public GitHub node-definition repository remaining accessible and structured similarly to its current form. `Confirmed` as available per prior research in this project; version pin needs to be selected before R13 can be built.

## 7. Success Criteria

- A user can type a plain-language intent for a domain with an existing checklist and receive a fully validated tree with zero manual correction needed to pass R3 to R8.
- The same tree, rendered in both Python and n8n mode on separate runs, produces logically equivalent step sequences (same dependency order), proving the single-tree, two-renderer architecture holds in practice, not just in spec.
- An n8n JSON file exported by the system imports into an actual n8n workspace without error.
- A new domain can be added by writing one new checklist file, without modifying the Decomposition Engine, Validator, or renderer code, proving domain-agnostic design (per R20, R21) actually holds.
- A user completes intent to rendered output (either mode) without navigating away from the two core screens defined in R16.

## 8. Open Questions

1. **Domain checklist authoring process.** Should new domain checklists beyond the RAG example be hand-authored and locked by the user, or should the app propose a first-draft checklist for one-time user approval before it becomes usable? Blocks: finalizing R1's behavior when an unresolved domain is entered. `Partially resolved`: whichever authoring process is chosen, the grounding simulation (R22) runs as part of authoring a new checklist, once, before that domain becomes usable for real requests.
2. **Claude Code autonomy in the Plan step.** Should Claude Code pause and present each Plan step for approval before Building, or run Plan through Commit autonomously per build-priority item and only surface the result at Commit? Blocks: nothing in this PRD's requirements directly, but affects how the dev loop in section 5's constraints is executed day to day.
3. **n8n schema version pin.** Which specific tagged release of n8n's node-definition repo should be vendored for R13? Blocks: R13, R14 cannot be built until this is chosen.
4. **Output rendering as page vs. panel, confirmed.** The UI directive already resolved this to "panel, not page" (R16 to R19 reflect that), but it is listed here as a reminder that this was a judgment call made under the collapse-stops principle, not an explicit prior user decision, in case it needs revisiting once the canvas is actually in front of the user.
