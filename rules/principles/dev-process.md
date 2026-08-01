# Rules and Principles: Development Process

Part of `rules/principles/`. Governs how ARCHITEQ itself gets built, module by module, per `ARCHITEQ-UI-and-Dev-Loop-Directive.md` Part 2 and `~/.claude/CLAUDE.md`. This file grounds that loop in established process theory rather than leaving it as an assertion.

Template per rule: **Statement | Grounding | Applies to | Predicate**

---

## DP1 — One Scoped Item Per Loop Iteration

**Statement:** Each Plan → Build → Test → Commit cycle covers exactly one requirement (or one sub-piece of a large requirement), never a batch of several requirements committed together.

**Grounding:** Lean software development's small-batch principle (Mary and Tom Poppendieck, "Lean Software Development," 2003) — smaller batches reduce risk, shorten feedback loops, and make failure attributable to a single change rather than a bundle.

**Applies to:** Every module in `ARCHITEQ-PRD.md` Section 4a; already stated as an explicit instruction in `ARCHITEQ-UI-and-Dev-Loop-Directive.md` Part 2, restated here with its grounding.

**Predicate:**
```
each commit's diff maps to exactly one requirement ID (R1, R2, ...) or
one named sub-piece of one requirement; a commit touching multiple
unrelated requirement IDs is rejected
```

---

## DP2 — Test Before Commit, Never After

**Statement:** No code is committed until it has been verified against the specific testable phrasing of the requirement it implements.

**Grounding:** Test-Driven Development and Extreme Programming (Kent Beck, "Extreme Programming Explained," 1999; "Test-Driven Development: By Example," 2002) — writing and running the test before or immediately after the implementation, never deferring verification past the point of commit.

**Applies to:** Every Build step in the loop.

**Predicate:**
```
a commit's associated plan file (.agent/plans/{n}.{name}.md) must record
at least one passed validation test before the Commit step is permitted
```

---

## DP3 — The Plan Is Written, Not Implicit

**Statement:** No Build step begins without a corresponding written plan file. A plan that exists only as a mental model or an unwritten intention does not satisfy this loop.

**Grounding:** Deming's Plan-Do-Check-Act (PDCA) cycle (W. Edwards Deming, "Out of the Crisis," 1986) requires the Plan phase to produce a concrete, checkable artifact before Do begins; this is also what makes G1 (Traceability) possible at the process level, not just the data level.

**Applies to:** `.agent/plans/` folder convention already specified in `~/.claude/CLAUDE.md`.

**Predicate:**
```
for every Build step executed, a corresponding file exists at
.agent/plans/{sequence}.{plan-name}.md, created before the Build step,
not backfilled after
```

---

## DP4 — The Loop Closes, It Does Not Terminate

**Statement:** A Commit is not an endpoint. It immediately feeds the next Plan step for the next requirement. The loop is continuous across the life of the project, not a one-time onboarding sequence.

**Grounding:** Deming's PDCA cycle, specifically the "Act" phase feeding back into a new "Plan" phase; also Kaizen (continuous improvement practice, central to Toyota Production System literature, e.g. Imai, "Kaizen," 1986) — improvement is ongoing, not a project phase that concludes.

**Applies to:** The Development Loop as a whole, for the entire lifetime of ARCHITEQ, not just its initial build.

**Predicate:**
```
PROGRESS.md always has at least one module in a non-terminal state
([ ] or [-]) unless every requirement in the PRD is complete; the
process is checked for "what's next," never treated as finished
without an explicit project-closure decision
```

---

## DP5 — Complexity Is Assessed Honestly Before Building

**Statement:** Before a Build step begins, the scoped item is honestly rated Simple, Medium, or Complex. Complex items are broken into sub-plans before any code is written, not attempted in one pass and corrected afterward.

**Grounding:** Boehm's Spiral Model (Barry Boehm, "A Spiral Model of Software Development and Enhancement," 1988) — risk assessment before committing to a full implementation pass is what distinguishes iterative, risk-managed development from a waterfall guess.

**Applies to:** Plan file complexity indicators already specified in `~/.claude/CLAUDE.md`.

**Predicate:**
```
every plan file declares a complexity indicator (Simple | Medium | Complex);
a Complex item's plan file must reference at least one sub-plan file
before its Build step begins
```

---

## DP6 — One Concern Per Commit

**Statement:** A commit changes one thing: implements one requirement, fixes one defect, or refactors one component. It does not mix unrelated changes.

**Grounding:** This is Separation of Concerns (WD3, Dijkstra 1974) applied specifically to version control granularity, consistent with standard atomic-commit practice in software engineering.

**Applies to:** All commits across the project.

**Predicate:**
```
a commit's changed files all trace to the same requirement ID or the
same named defect fix; unrelated changes are split into separate commits
```

---

## DP7 — Failures Surface Loudly During Test, Never Silently During Build

**Statement:** If a Build step produces something that doesn't work, this must be caught and surfaced at the Test step, not discovered later in production or masked by a subsequent change.

**Grounding:** Restates WD2 (No Silent Failure) at the process level rather than the workflow-output level: the same reliability-engineering discipline that governs generated workflows also governs the act of building ARCHITEQ itself.

**Applies to:** Test step of every loop iteration.

**Predicate:**
```
a Test step that does not produce an explicit pass or fail result (i.e.
is skipped or assumed) blocks the Commit step
```

---

## DP8 — Documentation Sync Is Part of Definition of Done

**Statement:** A requirement is not "done" when the code works. It is done when `ARCHITEQ-PRD.md`, `PROGRESS.md`, and any other affected governing document (the directive docs, the project `CLAUDE.md`) reflect the change. Documentation update is not a separate, optional follow-up task.

**Grounding:** Scrum's "Definition of Done" concept (Ken Schwaber and Jeff Sutherland, "The Scrum Guide") — a shared, explicit checklist that must be satisfied before work is considered complete, preventing partially-finished work from being reported as finished.

**Applies to:** Every Commit step; this directly operationalizes the standing instruction that every ARCHITEQ decision must populate back into the relevant md documents.

**Predicate:**
```
a Commit step is not considered closed until:
  - PROGRESS.md's relevant module/requirement checkbox is updated
  - ARCHITEQ-PRD.md is updated if the change added, removed, or altered
    a requirement or open question
  - any directive doc whose content the change contradicts is updated
    in the same commit, not a later one
```

---

## DP9 — Human Confirmation Gate for Complex or Irreversible Items

**Statement:** A Complex-rated plan item, or any item touching an irreversible action (per G4), pauses for human confirmation of the sub-plan breakdown before Build begins.

**Grounding:** Combines DP5's risk-assessment discipline (Boehm) with G4's human-oversight grounding (EU AI Act Article 14) — the process-level enforcement of a governance rule already established for generated workflows, applied here to ARCHITEQ's own build process.

**Applies to:** Autonomy Default section of `~/.claude/CLAUDE.md`.

**Predicate:**
```
for a plan item rated Complex, or tagged irreversible:
    Build does not begin until an explicit human confirmation of the
    sub-plan is recorded
for a plan item rated Simple or Medium and not irreversible:
    Plan through Test may proceed autonomously, per the Autonomy Default
```

---

## DP10 — Autonomy Level Is Stated, Never Assumed

**Statement:** How autonomously the loop runs (pause per stage vs. run through to Commit) is an explicit, written setting, not an implicit assumption either party carries into the work.

**Grounding:** This generalizes WD10 (Explicit Over Implicit) to the process layer: an unstated assumption about autonomy is exactly the kind of hidden convention that rule already forbids in generated workflows, and the same standard should apply to how the workflow of building ARCHITEQ itself runs.

**Applies to:** `~/.claude/CLAUDE.md` Autonomy Default section.

**Predicate:**
```
the current autonomy setting is recorded in ~/.claude/CLAUDE.md; if this
document is silent on autonomy for a given situation, that silence is
itself treated as an open question to resolve before proceeding, not
as implicit permission for full autonomy
```

---

## DP11 — Full Pre-Build Documentation Set Precedes Planning

**Statement:** Before Plan through Build through Test through Commit begins on a new project
or a major new capability (Complex-rated per DP5), six documents exist: PRD, TDD (Tech
Design Document), App Flow, Design Brief, Backend Schema, and Engineering Plan. A PRD alone
is necessary but not sufficient — it answers what and why; the other five answer how, in
what shape, on what data, and in what order.

**Grounding:** Generalizes separately-established software engineering documentation
practice into one ordered set, per `~/.claude/frameworks/universal-prd-framework.md` Section
2: IEEE 830 (SRS) for the PRD, IEEE 1016 (Software Design Description) and Nygard's
Architecture Decision Record practice for the TDD, Garrett's "Elements of User Experience"
(2000) for App Flow, Frost's "Atomic Design" (2016) for the Design Brief, Chen's
Entity-Relationship Model (1976) for Backend Schema, and WBS practice (PMI) for the
Engineering Plan.

**Applies to:** Every new project and every major new capability added to an existing
project (e.g. Module 11's Dual Tree Architecture); does not require redoing documentation
for work already committed under an earlier, smaller documentation set — that is a
documentation gap to close (DP8), not grounds to redo finished work.

**Predicate:**
```
before a Complex-rated item's Build step begins:
    PRD exists (Requirements, numbered, testable)
    TDD exists (tech stack, integrations, architecture overview, key decisions)
    App Flow exists (screens, journeys, actions, success/error paths)
    Design Brief exists (palette, type scale, component list)
    Backend Schema exists (entities/fields/types/relationships, or the equivalent
        structured data contract for non-relational storage)
    Engineering Plan exists (requirements broken into small tasks with dependencies,
        build order, acceptance criteria -- this PRD's own Section 4a/Modules plus
        .agent/plans/ satisfies this, it does not need a separate duplicate document)
a project missing one of these for already-in-progress work updates the missing
document in the same pass that discovers the gap, per DP8, rather than deferring it
```

---

## Summary Table

| ID | Rule | Grounding |
|----|------|-----------|
| DP1 | One Scoped Item Per Loop Iteration | Poppendieck, Lean Software Development, 2003 |
| DP2 | Test Before Commit | Beck, Extreme Programming / TDD, 1999-2002 |
| DP3 | The Plan Is Written, Not Implicit | Deming, PDCA, 1986 |
| DP4 | The Loop Closes, It Does Not Terminate | Deming PDCA; Imai, Kaizen, 1986 |
| DP5 | Complexity Assessed Honestly Before Building | Boehm, Spiral Model, 1988 |
| DP6 | One Concern Per Commit | Dijkstra, 1974 (via WD3) |
| DP7 | Failures Surface Loudly During Test | Restates WD2 at the process level |
| DP8 | Documentation Sync Is Part of Definition of Done | Schwaber & Sutherland, Scrum Guide |
| DP9 | Human Confirmation Gate for Complex/Irreversible Items | Boehm (DP5) + EU AI Act Art. 14 (G4) |
| DP10 | Autonomy Level Is Stated, Never Assumed | Generalizes WD10 to the process layer |
| DP11 | Full Pre-Build Documentation Set Precedes Planning | IEEE 830, IEEE 1016, Nygard (ADRs), Garrett (UX), Frost (Atomic Design), Chen (ER Model), PMI (WBS) |

This file is referenced from `RULES-INDEX.md`.
