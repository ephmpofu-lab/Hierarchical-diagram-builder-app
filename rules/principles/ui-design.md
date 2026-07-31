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

This file is referenced from `RULES-INDEX.md`. Next in the corpus: development process.
