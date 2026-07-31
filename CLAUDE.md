# CLAUDE.md (Global)

Location: `~/.claude/CLAUDE.md`. Applies to every project. Project-specific stack, domain rules, and architecture belong in that project's own `./CLAUDE.md`, not here.

## Who I am
Dr. Ephraim Mpofu, AI Solutions Architect and freelance consultant. Work spans building applications (like this one) and producing structured written deliverables (PRDs, specs, career/business documents). The rules below apply to both.

## Formatting Rules (all documents and written output, any project)
- No en-dashes, no underscores in prose.
- No AI-sounding filler phrases ("at the intersection of," "in today's landscape," etc.).
- No fabricated metrics or invented statistics.
- Concise, minimalist text. No repeated headers across sections/pages.
- Plain, direct sentences. Numbered lists over prose wherever something is enumerable.

## PRD Framework
Every project starts from a PRD before planning begins. Structure: Problem Statement, Goal, Non-Goals, Requirements (numbered, atomic, testable), Constraints, Dependencies, Success Criteria, Open Questions. Full framework lives at `~/.claude/frameworks/universal-prd-framework.md` — read it before writing any PRD.

Rules that always apply:
- No solutioning outside the Requirements section.
- Every requirement gets an ID (R1, R2...) and must be phrased so a pass/fail test can be written against it directly.
- Non-Goals is mandatory, not optional.
- One PRD, one Goal. Split into multiple PRDs if the goal is compound.
- Open Questions that affect a Requirement block that PRD from being finalized.

## Development Loop
Every feature, on every project, follows this loop. Do not skip a stage, do not batch multiple requirements into one untested step.

```
PRD (numbered requirements)
   → PLAN: scope one requirement (or one sub-piece of a large one).
       Save the plan to .agent/plans/{sequence}.{plan-name}.md
       (e.g. 1.auth-setup.md, 2.document-ingestion.md)
   → BUILD: implement just that scoped item.
   → TEST: verify directly against that requirement's own testable phrasing.
       Every plan task includes at least one validation test.
   → COMMIT: only after TEST passes.
   → back to PLAN: next requirement.
```

Plan file rules:
- Naming: `{sequence}.{plan-name}.md`, sequential.
- Plans must be detailed enough to execute without ambiguity.
- Every task in a plan includes at least one validation test.
- Mark a complexity indicator at the top of each plan:
  - Simple: single-pass executable, low risk.
  - Medium: may need iteration, some complexity.
  - Complex: break into sub-plans before executing.
- Before planning, assess single-pass feasibility honestly. If a requirement can't realistically be completed in one pass, split it into sub-plans rather than forcing it.

## Progress Tracking
Every project maintains a `PROGRESS.md` at its root. Check it at the start of a session, update it as requirements move through the loop (Planned / Building / Testing / Committed).

## Autonomy Default
Unless a project's own `./CLAUDE.md` says otherwise: run Plan through Test autonomously per requirement, then surface the result at Commit for review, rather than pausing for approval at every stage. If a requirement is Complex, pause after Plan to confirm the sub-plan breakdown before Building.

## General Working Preferences
- Prefer staged rollouts and mockups/plans before full implementation on anything user-facing.
- Collapse UI/navigation to the minimum number of real stops. Before adding a new page or screen, check whether it can be a state or panel on an existing one instead.
- When a technical decision has a "quick but fragile" option and a "slightly more setup but stable/versioned" option, default to recommending the stable one and say why, rather than defaulting to whichever is faster to wire up.
