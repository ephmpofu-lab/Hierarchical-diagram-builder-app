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
`[-]` — R24 to R37. See `ARCHITEQ-Dual-Tree-Architecture.md` and `ARCHITEQ-Recursive-Depth-and-Completion-Tracking.md`. Grounded and confirmed in scope by `RULES-INDEX.md` and `rules/principles/component-decomposition.md` (CD1-CD11). CD10 (R32/R33) requires that any architecture ARCHITEQ generates -- Python or n8n -- carries its own TDD/App-Flow/Design-Brief-equivalent documentation before freezing, elaborating DP11's own unified six-artifact sequence; CD11 (R37) additionally requires a Roadmap+Checklist render for that same generated architecture, restating DP13 at the output layer, not just at ARCHITEQ's own build process. 10c (Python folder/file/function browser, part of Module 10's UI rebuild) already satisfies UI12's requirement for the Engineering Plan artifact specifically. In progress: sub-plans 11a-11h built/tested/committed. 11h added the Component Tree's missing attribute-leaf whole-tree safety net (check_attribute_leaf) after tracing and confirming the Workflow Tree side was already correct, just under-documented. 3 of 11 sub-plans remain (11i-11k).

### Module 12: Planning Artifact Diagram Engine
`[ ]` — R38 to R40. Renders the *current domain's own* six planning artifacts (not ARCHITEQ's own self-documentation) as a `docs/` folder next to that domain's `architeq_{domain}/` code folder, hub-and-spoke diagram by default per UI12, text view one interaction away. Partially blocked: OQ6 means only the Engineering-Plan-equivalent (already real via Modules 5-8, surfaced through 10c) renders for real today; the other five -- including the PRD-equivalent, which depends on Module 11's Stage -3 -- render R40's honest "not generated yet" state until their generators exist. Not started.

## Open Blockers
Carried from `ARCHITEQ-PRD.md` Section 8.

- OQ1 (domain checklist authoring process) — resolved: app drafts, user approves. No longer blocks Module 3.
- OQ2 (Claude Code Plan-step autonomy) — resolved: per `~/.claude/CLAUDE.md` Autonomy Default, Plan through Test runs autonomously per requirement (surfaced at Commit), except Complex-rated items, which pause after Plan for sub-plan confirmation before Build (DP9).
- OQ3 (n8n schema version pin) — superseded, not resolved as originally framed. Confirmed via research mid-build that n8n has no live schema endpoint and no downloadable full-catalog JSON (the catalog is TypeScript source). What actually shipped: `rules/n8n_node_schemas.json`, a small hand-curated set of common core nodes (HTTP Request, Set, If, Merge, Webhook, Postgres), each checked against n8n's published docs, with the Code node as mandatory fallback. `ARCHITEQ-PRD.md`'s Constraints/Dependencies sections still describe the original "pinned tagged release, fully vendored" framing and need correction to match — tracked as a documentation gap, being fixed alongside this update.
- Module 11 (Dual Tree Architecture) has no blockers; Requirements Engineering (Stage -3) input is the real PRD, already in hand.
