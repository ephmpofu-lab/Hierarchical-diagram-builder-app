# ARCHITEQ — Reset & Rebuild Directive

This supersedes any prior UI implementation in the current codebase. Read this before touching `decompose.html`, `decompose.js`, or any other existing frontend file.

---

## 1. Why This Reset Is Happening

The current codebase has accumulated build history across 19+ rounds, including UI concepts and journeys (e.g. "Discovery Session," "AI Reasoning" flows) that were never part of the governing specification and are not mentioned in any of the following documents:

- `ARCHITEQ-Build-Directive.md`
- `ARCHITEQ-Decomposition-Engine-Spec.md`
- `ARCHITEQ-UI-and-Dev-Loop-Directive.md`
- `ARCHITEQ-PRD.md`
- `PROGRESS.md`

This has created drift between what the app actually does and what it was speced to do, and is now causing confusion during further build work. This directive resolves that drift by declaring the five documents above the single source of truth and instructing a clean rebuild of the UI layer against them.

## 2. What Gets Discarded

- Any page, screen, or journey not defined in `ARCHITEQ-UI-and-Dev-Loop-Directive.md` Part 1 (this includes "Discovery Session," "AI Reasoning," or any other named flow not in that document).
- Any UI structure that treats Output, History, Validation Results, or New Project as separate pages rather than states/panels on the two-screen structure already defined.
- Do not delete outright. Move discarded files/components into a `legacy/` directory at the project root, untouched, so nothing is lost and anything genuinely reusable can be salvaged deliberately later, on request, not by default.

## 3. What Gets Rebuilt, From a Clean State

Rebuild the frontend strictly to the two-screen structure already specified:

- **Screen 1 — Home/Canvas (merged)**: intent input, empty state, and populated-state history list, all on one screen. No separate "new project" page.
- **Screen 2 — Canvas, populated state**: same screen, showing the generated tree, mode toggle (Python | n8n), node detail panel, and rendered output as panel states, not separate pages.
- **Persistent command/refine input**: available on the canvas at all times, per the existing spec.
- **Settings**: hidden, admin-only, separate screen, per the existing spec.

No additional pages, journeys, or shortcuts beyond this structure unless they are first added as new numbered requirements to `ARCHITEQ-PRD.md` and approved there. If a build suggestion (visual polish, richer content, better framing) fits inside the existing two-screen structure without adding a new page, it can proceed. If it requires a new page or a new named journey, stop and flag it as a PRD gap first, per section 4 below.

## 4. Handling Ambiguity Going Forward

If, during rebuild, a piece of the old implementation reveals a workflow the PRD doesn't account for (e.g. the two named journeys above), do not silently rebuild it and do not silently discard its underlying intent. Instead:

1. Describe what the discarded flow actually did, in plain terms.
2. Flag it as a new Open Question or candidate Requirement against `ARCHITEQ-PRD.md`.
3. Wait for confirmation before it re-enters the two-screen structure in any form.

## 5. Skills

Skills already installed for this project (from `emilkowalski/skills` and `pbakaus/impeccable`) should be used as normal. No special invocation is required. Do not manually force them into every step; let them trigger automatically when a task's description matches, per standard Agent Skills behavior. If a rebuild task is clearly frontend/design related and a relevant skill does not appear to trigger, note that explicitly rather than proceeding without it silently.

## 6. Process

This rebuild follows the same Plan → Build → Test → Commit loop already defined in `ARCHITEQ-UI-and-Dev-Loop-Directive.md` Part 2 and `~/.claude/CLAUDE.md`, scoped to Module 10 (UI Shell) in `ARCHITEQ-PRD.md` Section 4a. Do not treat this as a special one-off process outside that loop.

## 7. Explicit Instruction

Discard confusion, not history. Everything moved to `legacy/` remains on disk and in git history. The five governing documents listed in Section 1 are the only current source of truth for what the UI should be. Build to them, not to what already exists in the repo.
