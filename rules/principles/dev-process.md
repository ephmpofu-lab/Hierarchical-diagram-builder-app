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

## DP11 — Six Planning Artifacts Precede Construction, Always in Order

**Statement:** Before any construction (code, workflow, or infrastructure) begins, six planning artifacts are produced in this fixed order:

1. **PRD** (Product Requirements Document) — what is being built, per the Universal PRD Framework already established.
2. **Tech Design Document (TDD)** — the technical decisions and their rationale: stack, integrations, architecture overview, key tradeoffs. The "bible" for why, not just what.
3. **App Flow** — screens, user journeys, onboarding, and interaction paths. *Conditional*: only produced when the project has a genuine UI/frontend layer; a pure backend/data-pipeline domain has no screens to flow.
4. **Design Brief** — visual system: color palette, typography, component styles. *Conditional*, same test as App Flow.
5. **Backend Schema** — data model: tables, fields, types, relationships between them.
6. **Engineering Plan** — the project broken into small, testable tasks with explicit dependencies and a build order.

Each artifact depends on the one before it and is not started until its predecessor exists. This sequence is universal: it governs ARCHITEQ's own development process *and* it governs what ARCHITEQ produces for a user's project when they describe something they want to build — the same discipline applied at both levels, not two different standards.

**Grounding:** ISO/IEC/IEEE 12207 (Systems and Software Engineering — Software Life Cycle Processes), the international standard separating requirements, architecture, design, and construction into distinct, ordered phases — this six-artifact sequence is that standard's phase separation made concrete and named. The conditional App Flow/Design Brief step reflects the standard's own allowance that not every system has the same process needs; a UI-less data pipeline does not require a UX design phase.

**Applies to:** The Development Loop (this file) for ARCHITEQ's own build; the Decomposition Engine's pre-stages (per `ARCHITEQ-Dual-Tree-Architecture.md`) for what ARCHITEQ generates. This rule sits *above* and *encompasses* those existing pre-stages: the Engineering Plan (artifact 6) is realized by the existing Component Tree / Workflow Tree machinery already specified — this rule does not replace that machinery, it places it correctly as the final stage of a larger sequence that was previously missing its first five stages.

**Predicate:**
```
no construction task (a Plan file per DP3) is opened until all
applicable artifacts (1, 2, 5, 6 always; 3, 4 only if the project has a
UI layer) exist and are committed; each artifact's content is checked
for consistency with the artifact before it, not authored independently
```

---

## DP12 — A Rules-File Change Triggers a Cross-Reference Check Before It's Complete

**Statement:** Editing any single file in `rules/principles/` is not finished when that file's own content is correct. Before the change is considered done, run this checklist:

1. **`RULES-INDEX.md` accuracy** — does the file list, rule-ID range, per-file count, and total still match reality? Update if not.
2. **Cross-reference search** — does any *other* file in the corpus reference the changed rule by ID (e.g. "restates WD8," "extends NT1," "amends NT10")? If the changed rule's meaning shifted, the referencing rule's own text may now be wrong too, even though nobody edited it directly. Check each one; amend if stale, per the same superseding-note convention already established (CR3, NT10, UI11).
3. **Conflict against what's actually implemented** — if the rule governs something already built (not just specified), does the change match live behavior, or does it now describe something that doesn't exist yet? A rule and an implementation disagreeing is exactly the CR3-vs-CR15 defect this project already found once.
4. **Delivery lands as an update, not a duplicate** — when the changed file reaches its actual destination (a project repo maintained by someone else, e.g. via Claude Code), confirm it overwrites the existing file at its correct path rather than arriving under a different name and creating a second, competing copy of the same rule set.

None of these four steps is optional because the file's own prose reads correctly in isolation — a rules corpus is a network of cross-references, and a change that looks complete locally can leave the network inconsistent.

**Grounding:** IEEE 828 (Standard for Configuration Management in Systems and Software Engineering) — specifically its requirement that a change to a controlled specification undergo impact analysis against dependent artifacts before the change is accepted, not just a local correctness check on the changed item itself.

**Applies to:** Any edit to a file in `rules/principles/`, whether the edit originates here or is made directly in a project repo.

**Predicate:**
```
no rules-file edit is marked complete until: RULES-INDEX.md is verified
current, every cross-reference to the changed rule ID elsewhere in the
corpus has been checked and amended if stale, the change has been
checked against known live implementation behavior where applicable,
and the delivered file is confirmed to overwrite its correct destination
path rather than landing as a new, differently-named file
```

---

## DP13 — A Roadmap and Checklist Exist Beyond the Current Work Item

**Statement:** Beyond DP11's six artifacts and `PROGRESS.md`'s module-level tracking,
ARCHITEQ's own project maintains a Roadmap (a sequenced, phased view of what comes after the
current work, not just the current module) and a Checklist (per-item completion status).
Already established in practice via `ARCHITEQ-ROADMAP.md` and `PROGRESS.md`; formalized here
as a standing requirement rather than an incidental convention that happens to exist.

**Grounding:** Standard product/engineering roadmap practice (Lombardo, McCarthy, Ryan,
Connors, "Product Roadmaps Relaunched," O'Reilly, 2017) — a roadmap sequences work at a
level above individual tasks, distinct from and complementary to a task-level plan. The
checklist half reuses the same WBS 100% Rule (PMI) grounding already established for
completion tracking elsewhere in this corpus (CD9, WD11, WD12), rather than a new mechanism.

**Applies to:** Any Complex-rated new capability (mirrors DP5/DP9's Complex-rating trigger).

**Predicate:**
```
before or alongside a Complex-rated capability's PRD, an entry exists in
ARCHITEQ-ROADMAP.md naming it and its rough sequencing relative to other
planned work; PROGRESS.md tracks its checklist-style completion status
once work begins
```

---

## DP14 — A UI-Facing Change Is Tested Against a Real Rendered Screenshot, Not Just Its Own Code

**Statement:** DP2 requires a passed validation test before commit; for a UI-facing change,
reading the source that renders a feature, or grepping for the function that builds it, does
not satisfy DP2's own "verified" bar. A rendered screenshot of the actual served page (an
automated browser, not a description of what the code should do) is the validation test. When
a reference design (a mockup, a written checklist) exists, the screenshot is compared against
it item by item, not eyeballed for a general impression. Adopted directly from this session's
own experience: two rounds of "verified" based on reading `decompose.js` and confirming a
function existed both turned out to be proxies for the real question (what actually renders)
and both missed real, confirmable-by-pixel gaps a screenshot caught on the first pass.

**Grounding:** Restates DP2 (Beck, TDD) at the UI layer, the same relationship DP10 already
has to WD10 in this corpus — one underlying principle applied at a more specific layer, not a
new one. Also: this session's own record (three real defects — hardcoded hub-and-spoke
labels, a stale `sourceSections` fallback, a stray NUL byte silently breaking `grep` — found
only once real screenshots were taken, none of them caught by reading the code that produced
them).

**Applies to:** Any sub-plan whose Build step changes rendered output (HTML/CSS/SVG/canvas),
before that sub-plan's own Status checkboxes may show Tested or Committed.

**Predicate:**
```
a UI-facing sub-plan's own Test step records: (a) an automated-browser
screenshot of the actual served page in the relevant state, (b) if a
reference design exists, a same-state screenshot of that reference and an
item-by-item comparison between the two, (c) for any item that fails, the
file/function where the real behavior is (or isn't) wired in -- never a
"the code looks right" statement standing in for a., b., or c.
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
| DP11 | Six Planning Artifacts Precede Construction, Always in Order | ISO/IEC/IEEE 12207 |
| DP12 | A Rules-File Change Triggers a Cross-Reference Check | IEEE 828 (Configuration Management) |
| DP13 | A Roadmap and Checklist Exist Beyond the Current Work Item | Lombardo et al., Product Roadmaps Relaunched, 2017; PMI (WBS 100% Rule) |
| DP14 | A UI-Facing Change Is Tested Against a Real Rendered Screenshot | Restates DP2 (Beck, TDD) at the UI layer |

This file is referenced from `RULES-INDEX.md`.
