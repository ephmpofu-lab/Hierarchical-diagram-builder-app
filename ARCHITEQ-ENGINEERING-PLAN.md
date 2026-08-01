# Engineering Plan: ARCHITEQ

Per `~/.claude/frameworks/universal-prd-framework.md` Section 2 and `rules/principles/
dev-process.md` DP11. This document is an index, not a duplicate — ARCHITEQ's requirements
are already broken into small, testable tasks with dependencies, build order, and
acceptance criteria across three existing places. Writing a second, separate task list
would immediately drift from those three; this file instead states where each part of DP11's
"small tasks, dependencies, build order, acceptance criteria" requirement actually lives.

---

## 1. Requirements -> Modules (the build order)

`ARCHITEQ-PRD.md` Section 4a lists every module, its requirement IDs, and its dependency on
earlier modules — this is the project's build order, module by module:

```
Module 1 (Domain Resolution & Schema)
    -> Module 2 (Principles & Rules) -> Module 3 (Checklists) -> Module 4 (Validator)
        -> Module 5 (Decomposition Engine) -> Module 5a (Grounding Simulation)
            -> Module 6 (Execution Ordering)
                -> Module 7 (Python Renderer)
                -> Module 8 (n8n Node Mapper) -> Module 9 (Visual Diagram Renderer)
            -> Module 10 (UI Shell)
                -> Module 11 (Dual Tree Architecture / Component Tree)
```

Status of each: `PROGRESS.md`.

## 2. Modules -> Small Tasks (dependencies, acceptance criteria)

A module is not itself a build unit — each is further broken into `.agent/plans/
{sequence}.{plan-name}.md` files per `~/.claude/CLAUDE.md`'s Development Loop, one
requirement (or sub-piece) at a time. A plan file states its own complexity rating
(Simple/Medium/Complex), its dependencies (which earlier plan or module it needs), and at
least one validation test per task — this is DP2's "test before commit" made concrete per
task, and is the literal "acceptance criteria" DP11 asks this document to point to.

Modules 1-10 were built before the `.agent/plans/` convention existed in this project (they
predate the pulled `CLAUDE.md`/`RULES-INDEX.md` corpus) — their task-level history lives in
this session's own commit history instead, not as retroactively-created plan files (per DP1,
history is not rewritten after the fact).

Module 11 onward uses `.agent/plans/` going forward:
- `.agent/plans/11.dual-tree-architecture.md` — the Complex-rated index plan.
- `.agent/plans/11a.requirements-engineering-stage.md` through `11i.completion-tracking.md`
  — each sub-plan's own small tasks, dependencies, and acceptance tests.

## 3. Cross-Module Dependencies Worth Naming Explicitly

- Module 11 depends on Modules 1-10 being complete (it reconciles against the Workflow
  Tree, R29) — confirmed complete per `PROGRESS.md`.
- Module 8 (n8n Node Mapper) depends on `rules/n8n_node_schemas.json` existing — a
  hand-curated file, not a build task with its own test; see `ARCHITEQ-TDD.md` Key Tech
  Decision 3 for why.
- Module 5a (Grounding Simulation) depends on Module 5 but was added to the module list
  after Modules 1-10 were already built — a documentation-sync fix, not a build dependency
  that blocked anything retroactively.

## 4. Where to Look for What

| Question | Answer lives in |
|---|---|
| What are we building and why | `ARCHITEQ-PRD.md` |
| Why did we choose this tech | `ARCHITEQ-TDD.md` |
| What screens/flows exist | `ARCHITEQ-APP-FLOW.md` |
| What does it look like | `ARCHITEQ-DESIGN-BRIEF.md` |
| What's the data shape | `ARCHITEQ-BACKEND-SCHEMA.md` |
| What order do we build in, what's done | This file + `PROGRESS.md` |
| What's the next concrete task | `.agent/plans/` — the newest-numbered file not yet marked Committed |
