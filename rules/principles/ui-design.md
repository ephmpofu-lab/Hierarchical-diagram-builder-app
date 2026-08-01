# Rules and Principles: User Interface Design

Part of `rules/principles/`. Governs the Home/Canvas screen, the detail panel, and every rendered visual (tree diagram, n8n diagram) per `ARCHITEQ-UI-and-Dev-Loop-Directive.md` and the visual fixes in `ARCHITEQ-Simulation-Grounding-and-Visual-Fix.md`.

Template per rule: **Statement | Grounding | Applies to | Predicate**

---

## UI1 — Collapse Stops, Don't Just Declutter Screens

**Statement:** Before adding a new page, screen, or navigation stop, check whether the workflow can instead be a state or panel on an existing screen.

**Grounding:** Derived directly from Railway's actual dashboard behavior (analyzed in `ARCHITEQ-UI-and-Dev-Loop-Directive.md` Part 1): home, new-project, build, deploy, and monitor all collapse onto one canvas with state changes rather than separate pages. Each additional page is a decision point and a context-switch cost.

**Applies to:** Any new UI work, by default; this is the rule the Reset & Rebuild Directive's Section 3 already enforces for the current rebuild.

**Predicate:**
```
for each proposed new screen:
    can this be expressed as a state, panel, or persistent-input action on
    Screen 1 or Screen 2? if yes, REJECT the new screen proposal
```

---

## UI2 — Visibility of System Status

**Statement:** The user is never left wondering what state the system is in. Validation status, selected output mode, and grounding cache status (fresh vs. stale) are always visibly shown, not hidden until requested.

**Grounding:** Nielsen's Usability Heuristics, heuristic 1 (Jakob Nielsen, "10 Usability Heuristics for User Interface Design," 1994, Nielsen Norman Group) — keep users informed through appropriate feedback within reasonable time.

**Applies to:** Canvas screen (mode toggle state, tree validation pass/fail), Node Detail Panel.

**Predicate:**
```
every asynchronous or stateful operation (validation, rendering, grounding
lookup) has a visible status indicator on screen while and after it runs
```

---

## UI3 — Recognition Over Recall

**Statement:** The user should be able to see available actions and past decompositions rather than needing to remember exact commands or IDs to retrieve them.

**Grounding:** Nielsen's Usability Heuristics, heuristic 6 — minimize the user's memory load by making elements, actions, and options visible.

**Applies to:** Home/Canvas empty and populated states (history list), Node Detail Panel (shows available fields rather than requiring the user to know what to ask for).

**Predicate:**
```
every action available to the user at a given screen state is visually
present (button, list item, toggle) rather than requiring recall of a
hidden command
```

---

## UI4 — Progressive Disclosure

**Statement:** Show only what's needed for the current decision. Full detail (variables, rules, dependencies, rendered code) is available on demand via the detail panel, not shown by default on the canvas.

**Grounding:** Progressive disclosure is a long-established interaction design principle (Nielsen Norman Group; also formalized in Jef Raskin's "The Humane Interface," 2000) for managing information density without overwhelming the primary view.

**Applies to:** Canvas tree view (shows Layer/Sub-task/Atomic step names only) vs. Node Detail Panel (shows requires/produces/rules/variables on click).

**Predicate:**
```
the canvas view surfaces node names and structure only; requires[],
produces[], rules[], and variable lists render only inside the Node
Detail Panel, never inline on the base canvas
```

---

## UI5 — Consistency and Standards

**Statement:** The same concept looks the same everywhere. A Layer node has one consistent visual treatment across every domain and every screen; the same is true for Sub-task and Atomic step nodes.

**Grounding:** Nielsen's Usability Heuristics, heuristic 4 — follow platform and internal conventions so users don't have to wonder whether different words, situations, or actions mean the same thing.

**Applies to:** SVG tree renderer (Fix D in the Simulation Grounding addendum): each of the four C4 levels gets one fixed visual treatment (size/color), applied identically regardless of domain.

**Predicate:**
```
node styling (size, color, shape) is a function of tree_level only
(Layer | Sub-task | Atomic step | Variable), never varied per domain
or per individual tree
```

---

## UI6 — Error Prevention and Graceful Recovery

**Statement:** A Validator rejection is shown with the specific rule violated and the specific node it applies to, with a clear path to correction, not a generic failure message.

**Grounding:** Nielsen's Usability Heuristics, heuristics 5 (error prevention) and 9 (help users recognize, diagnose, and recover from errors); directly consistent with the Decomposition Engine Spec's own Validator design (Section 7), which already returns a specific violation and node, not a generic failure.

**Applies to:** Canvas screen's inline validation warnings (per the earlier UI directive, these surface on the node itself, not a separate "Validation Results" page).

**Predicate:**
```
every Validator rejection surfaced in the UI includes: the specific rule
ID violated (from P1-P8, WD1-WD10, or G1-G10), the specific node it
applies to, and a plain-language description of what would resolve it
```

---

## UI7 — Fitts's Law: Size and Placement Match Frequency of Use

**Statement:** The most frequently used controls (mode toggle, persistent refine input) are large enough and close enough to reduce time-to-target; rarely used controls (Settings) are smaller and further from the primary work area.

**Grounding:** Fitts's Law (Paul Fitts, 1954; widely applied in HCI via Card, Moran & Newell's "The Psychology of Human-Computer Interaction," 1983) — the time to acquire a target is a function of its size and distance.

**Applies to:** Persistent command/refine input (always visible, generous hit area), Settings screen (deliberately tucked away, per UI1).

**Predicate:**
```
primary controls (mode toggle, refine input, node click targets) meet a
minimum hit-area size; Settings entry point is not placed in the primary
canvas work area
```

---

## UI8 — Hick's Law: Bound the Choices Presented at Once

**Statement:** The user is never asked to choose from an open-ended or large set of options where a small, bounded set will do. Output mode is exactly two choices (Python, n8n), not an extensible list shown as if more exist.

**Grounding:** Hick's Law (William Edmund Hick, 1952; Ray Hyman, 1953) — decision time increases with the number and complexity of choices.

**Applies to:** Output Mode Selector (Build Directive Section 4.6, R11), any future selection UI.

**Predicate:**
```
the output mode control presents exactly 2 options, never rendered as
an open list; any future choice point in the UI is reviewed against
whether it can be bounded to a small fixed set before being built
```

---

## UI9 — Gestalt Grouping: Hierarchy Shown Through Structure, Not Just Labels

**Statement:** The tree's four-level hierarchy must be visually legible through proximity, connecting lines, and enclosure — not only through text headers. A user should be able to tell a Layer from a Sub-task from an Atomic step by looking at the shape of the diagram alone, before reading any label.

**Grounding:** Gestalt principles of visual perception (Wertheimer, Koffka, Köhler, early 20th century; standard reference in visual design literature) — proximity, connectedness, and enclosure communicate grouping and hierarchy independent of text. This is the direct fix for the flat-card defect identified in `ARCHITEQ-Simulation-Grounding-and-Visual-Fix.md` Section 1.

**Applies to:** SVG tree renderer (Fix D).

**Predicate:**
```
the rendered tree diagram, with all text labels removed, still visually
communicates 4 distinct hierarchy levels through connecting lines,
size, and grouping alone
```

---

## UI10 — Accessibility Is Not Optional

**Statement:** Status and validation states are never communicated by color alone. Text contrast, keyboard navigation, and screen-reader-readable labels are required, not a later pass.

**Grounding:** WCAG 2.1/2.2 (W3C Web Content Accessibility Guidelines) — the standard baseline for accessible interface design, specifically the "use of color" success criterion (1.4.1) and keyboard-operability requirement (2.1.1).

**Applies to:** Validation status indicators (pass/fail must also use an icon or text label, not color alone), mode toggle, all interactive elements on the canvas.

**Predicate:**
```
every status indicator that uses color also carries a non-color signal
(icon, text, or pattern); every interactive control is reachable via
keyboard navigation, not mouse/touch only
```

---

## UI11 — Navigation Rail Collapses by Default, Expands on Demand

**SUPERSEDED — see note below.** **Statement:** Persistent cross-screen navigation (Home, Recent, Settings) lives in a narrow, icon-only rail by default, expanding to labeled items only on interaction. It never competes with the canvas for primary screen space, and it carries only items that are genuinely needed across every screen — nothing included because a reference pattern happened to have it.

**Amendment:** During implementation, this rail — even in its collapsed icon-only form — repeatedly failed to read as intentional (reported multiple times as "why is this here, why doesn't it retract" despite functioning as designed). Rather than continue patching a UI element that wasn't earning its keep, it was removed entirely from the mockup. The requirements it existed to serve (returning to the empty canvas, revisiting recent work) are satisfied by the existing Home/Canvas merged screen itself, per UI1. This rule is kept in place, marked superseded rather than deleted, per this corpus's traceability requirement (G1, G3) — the same treatment CR3 and NT10 received.

**Grounding:** This is the standard resolution to the tension between UI1 (Collapse Stops — minimize navigational surface) and UI3 (Recognition over Recall — actions should be visible, not memorized): a collapsed icon rail satisfies both, converged on independently by Miro, Notion, and Figma's own sidebar patterns as the standard answer for canvas-based tools specifically. Precedent is Miro's own left rail, used here as a case study the same way Railway's dashboard was used earlier — followed for the collapse behavior, deliberately not followed for content (profile switcher, Starred, Your recordings, Spaces are workspace/collaboration concepts excluded per the PRD's Non-Goals).

**Applies to:** Nothing currently — superseded. Retained for history only.

**Predicate:** Not enforced; see amendment.

---

## UI12 — Planning Artifacts Render as Diagrams by Default, Text on Demand

**Statement:** Each of the six planning artifacts in DP11 (PRD, Tech Design Document, App Flow, Design Brief, Backend Schema, Engineering Plan) has a corresponding diagrammatic view — a central document card with 4-6 satellite cards pulling out its key structural pieces (hub-and-spoke layout) — and this diagram is the *default* view when the artifact is opened in the folder scaffold. The full text document remains available, but is not the first thing shown. This applies with particular weight to the Python Workflow Tree output: folder and function structure is shown diagrammatically first, matching the pattern already built for the Level 1/2/3 Python browser, not as a wall of markdown.

**Grounding:** Direct extension of UI9 (Gestalt Grouping — hierarchy shown through structure, not just labels) and UI4 (Progressive Disclosure) to planning documents specifically, rather than only to the task tree. The specific hub-and-spoke visual pattern (central card, 4-6 satellite cards, dotted connector lines) is a documented reference pattern the person supplied directly for each of the six DP11 artifact types, used here as a case-study precedent the same way Railway and Miro were used for other UI rules.

**Applies to:** Any tool that renders a planning artifact from DP11's sequence — this is a rendering requirement, parallel to how `n8n-canvas-rules.md` governs rendering of the Workflow Tree; a future `planning-artifact-rendering.md` file may be warranted if this grows past a single rule, but is not created until a second rule in this family is actually needed (per this corpus's own standard: don't add a file for one rule).

**Predicate:**
```
opening any of the six DP11 artifact types in the folder scaffold
displays its hub-and-spoke diagram first; the full text document is
one interaction away, never the default first view; the Python
Workflow Tree folder/function browser satisfies this rule already for
the Engineering Plan artifact specifically
```

---

## Summary Table

| ID | Rule | Grounding |
|----|------|-----------|
| UI1 | Collapse Stops | Railway dashboard behavior (case study) |
| UI2 | Visibility of System Status | Nielsen heuristic 1 |
| UI3 | Recognition Over Recall | Nielsen heuristic 6 |
| UI4 | Progressive Disclosure | Nielsen Norman Group; Raskin, 2000 |
| UI5 | Consistency and Standards | Nielsen heuristic 4 |
| UI6 | Error Prevention and Recovery | Nielsen heuristics 5, 9 |
| UI7 | Fitts's Law | Fitts, 1954; Card, Moran & Newell, 1983 |
| UI8 | Hick's Law | Hick, 1952; Hyman, 1953 |
| UI9 | Gestalt Grouping | Wertheimer, Koffka, Köhler |
| UI10 | Accessibility | WCAG 2.1/2.2 |
| UI11 | ~~Navigation Rail Collapses by Default~~ (superseded, see note) | Miro/Notion/Figma precedent |
| UI12 | Planning Artifacts Render as Diagrams by Default | Hub-and-spoke reference pattern; extends UI4, UI9 |

This file is referenced from `RULES-INDEX.md`. Next in the corpus: development process.
