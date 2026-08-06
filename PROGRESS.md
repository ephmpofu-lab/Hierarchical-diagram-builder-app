# Progress

Track progress through ARCHITEQ. Update this file as modules are completed. Claude Code reads this to understand where the project currently stands. Modules and their requirement IDs are defined in `ARCHITEQ-PRD.md` Section 4a.

## Convention
- `[ ]` = Not started
- `[-]` = In progress
- `[x]` = Completed

A module moves to `[x]` only when every requirement listed under it in the PRD has passed Test and been Committed, per the Development Loop in `~/.claude/CLAUDE.md`.

## Modules

### Module 1: Domain Resolution & Task Tree Schema
`[x]` — R1, R2

### Module 2: Decomposition Principles & Rules Engine (P1 to P8)
`[x]` — R4, R5, R6, R7, R21

### Module 3: Domain Checklists & Reference Architecture Mapping
`[x]` — R3, R20

### Module 4: Validator
`[x]` — R9

### Module 5: Decomposition Engine (build order, Stages 0 to 4)
`[x]` — implements R1 to R9 end to end, depends on Modules 1 to 4

### Module 5a: Grounding Simulation (Stage 2.5)
`[x]` — R22, R23. Not present in `ARCHITEQ-PRD.md` Section 4a's original module list; added here since R22/R23 exist as requirements but were never assigned a module. PRD Section 4a should be updated to match (tracked as a documentation gap, not a blocker).

### Module 6: Execution Ordering (topological sort)
`[x]` — R10

### Module 7: Python Renderer
`[x]` — R11, R12

### Module 8: n8n Node Mapper & Renderer
`[x]` — R13, R14

### Module 9: Visual Diagram Renderer
`[x]` — R15

### Module 10: UI Shell (Home/Canvas, Detail Panel, Persistent Input)
`[x]` — R16, R17, R18, R19

### Module 11: Dual Tree Architecture (Component Tree)
`[x]` — R24 to R37. See `ARCHITEQ-Dual-Tree-Architecture.md` and `ARCHITEQ-Recursive-Depth-and-Completion-Tracking.md`. Grounded and confirmed in scope by `RULES-INDEX.md` and `rules/principles/component-decomposition.md` (CD1-CD11). All 11 sub-plans (11a-11k) built/tested/committed. 11k added the Roadmap + Checklist render (R37/CD11): one shared, mode-agnostic markdown-checklist renderer plus two adapters (Workflow Tree, Component Tree), each in their own tree's existing build order, showing every node's real completion status. 10c (Python folder/file/function browser, part of Module 10's UI rebuild) already satisfies UI12's requirement for the Engineering Plan artifact specifically. Sub-plan 11l (2026-08-02) added the `propose_component_tree` orchestrator tying Stages -3 through 0 together into one real, persistable `ComponentTree` object, plus `component-tree/draft`/`/approve`/`GET` endpoints mirroring the Workflow Tree's own shape -- the last item this line used to list as deferred. No UI beyond the minimal API, per this plan's own explicit scope (matches the Workflow Tree's own precedent of API-first, UI-later).

### Module 12: Planning Artifact Diagram Engine
`[x]` — R38 to R40. Renders the *current domain's own* six planning artifacts (not ARCHITEQ's own self-documentation) as a `docs/` folder next to that domain's `architeq_{domain}/` code folder, hub-and-spoke diagram by default per UI12, text view one interaction away. Both sub-plans (12a-12b) built/tested/committed. 12a added the `docs/` folder, the generic `renderHubAndSpoke` diagram primitive, and the Engineering-Plan-equivalent's real hub-and-spoke view. 12b resolved OQ6: `backend/planning_artifacts.py` adds six deterministic per-domain generators (PRD, TDD, App Flow, Design Brief, Backend Schema, Engineering Plan), each derived only from a domain's frozen Workflow Tree and, where relevant, its Component Tree or Data Architecture -- never an LLM call, never ARCHITEQ's own repository documents. App Flow/Design Brief still need a frozen Component Tree and Backend Schema still needs a frozen Data Architecture to exist for a given domain; absent either, R40's honest "not generated yet" state names that specific dependency -- a real per-domain state, not a gap in ARCHITEQ itself.

### Module 13: Data Architecture Layer
`[x]` — R41 to R50. Per `docs/ARCHITEQ-Data-Architecture-Layer-Spec.md`. A second, synchronized architectural layer alongside the Workflow Layer (never an independent ERD page, never sharing the Workflow Layer's own layout) -- derived from a domain's already-frozen Workflow Tree: every Atomic step classified by its data-persistence operation (CREATE/READ/WRITE/UPDATE/DELETE/QUERY/TRANSIENT), persistent entities deduplicated and given stable Data IDs, one canonical model driving the ERD/SQL DDL/workflow mappings together, bidirectional cross-layer traceability (domain + Atomic step id + Data ID + operation, never a bare id alone), and prominence-toggling between the two layers. Depends on Modules 1-10. All 10 sub-plans (13a-13j) built/tested/committed: backend (13a-13e, model/persistence/Stage 5-6/SQL DDL/orchestrator/API) then frontend (13f-13j, ERD renderer with its own FK-driven layout, workflow-active anchors + faint Data underlay, data-active mode + faint Workflow underlay, Workflow->Data highlighting on the Node Detail Panel, Data->Workflow highlighting via the new Entity Detail Panel + synchronized SQL view).

## Open Blockers
Carried from `ARCHITEQ-PRD.md` Section 8.

- OQ1 (domain checklist authoring process) — resolved: app drafts, user approves. No longer blocks Module 3.
- OQ2 (Claude Code Plan-step autonomy) — resolved: per `~/.claude/CLAUDE.md` Autonomy Default, Plan through Test runs autonomously per requirement (surfaced at Commit), except Complex-rated items, which pause after Plan for sub-plan confirmation before Build (DP9).
- OQ3 (n8n schema version pin) — superseded, not resolved as originally framed. Confirmed via research mid-build that n8n has no live schema endpoint and no downloadable full-catalog JSON (the catalog is TypeScript source). What actually shipped: `rules/n8n_node_schemas.json`, a hand-curated set of core nodes (HTTP Request, Set, If, Merge, Webhook, Postgres, Stop And Error, Extract From File, Read/Write Files from Disk, Google Drive, Notion, plus one deferred cluster-node entry), each checked against n8n's published docs, with the Code node as mandatory fallback. `ARCHITEQ-PRD.md`'s Constraints/Dependencies sections have been corrected to match (marked `Corrected` inline) — this documentation gap is now closed, this line kept only as the historical record of the supersession itself.
- OQ6 (no real per-domain generator for 5 of DP11's 6 planning artifacts) — resolved by sub-plan 12b, no longer blocks Module 12. All six DP11 artifacts now have a real, deterministic per-domain generator (`backend/planning_artifacts.py`), derived only from a domain's frozen Workflow Tree and, where relevant, its Component Tree or Data Architecture. App Flow/Design Brief still need a frozen Component Tree to exist for a given domain, and Backend Schema still needs a frozen Data Architecture — absent either, R40's honest "not generated yet" state names that specific dependency; this is a real per-domain condition, not an unresolved scope question about ARCHITEQ itself.
- OQ7 (Data Architecture Layer's "multiple workflows" framing) — resolved: Workflow ID = domain name, Node ID = real Atomic step id. See `ARCHITEQ-PRD.md`'s Data Architecture Layer section and `docs/ARCHITEQ-Data-Architecture-Layer-Spec.md`'s own grounding note.
- OQ8 (data-persistence-operation classification granularity) — open, does not block starting Module 13's earlier sub-plans (the model/schema work); only blocks the specific sub-plan that builds Stage 5's own AI call shape.
- Module 11 (Dual Tree Architecture) has no blockers; Requirements Engineering (Stage -3) input is the real PRD, already in hand.
