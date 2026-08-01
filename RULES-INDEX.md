# RULES-INDEX

Master pointer file for `rules/principles/`. Every rule ARCHITEQ enforces, across every part of the system, traces back to one of the files below. This index exists so no one — Claude Code or a human — has to already know the corpus exists to find it.

Shared template across every file: **Statement | Grounding | Applies to | Predicate.** No rule in this corpus is asserted without a named, citable source.

---

## Files in this corpus

| File | Rule prefix | Covers | Primary grounding |
|---|---|---|---|
| `workflow-design.md` | WD1-WD10 | How any workflow (Python or n8n) is structured, sequenced, and branched | Workflow Patterns (van der Aalst et al.), Dijkstra, Constantine & Yourdon, BPMN |
| `governance.md` | G1-G10 | Traceability, accountability, auditability, oversight | NIST AI RMF, ISO/IEC 42001, EU AI Act |
| `ui-design.md` | UI1-UI10 | The Home/Canvas screen, detail panel, tree diagram | Nielsen heuristics, Fitts's/Hick's Laws, Gestalt principles, WCAG |
| `dev-process.md` | DP1-DP11 | How ARCHITEQ itself gets built, module by module | Deming (PDCA), Boehm (Spiral Model), Beck (XP/TDD), Poppendieck (Lean), Scrum, IEEE 830/1016 |
| `decomposition.md` | P1-P8 | The task tree engine (prose companion to the machine-checkable JSON) | SOLID, C4 Model, TDSP, Well-Architected Framework |
| `prompting.md` | PR1-PR7 | ARCHITEQ's own internal LLM calls (Intent Parser, grounding simulations) | Anthropic prompt engineering guidance, few-shot/chain-of-thought literature |
| `node-translation.md` | NT1-NT9 | How a validated atomic step becomes a real n8n node | Extends WD9, P4, G9; n8n's actual node schema |
| `component-decomposition.md` | CD1-CD9 | The structural Component Tree (Python track): requirements to capabilities to components to attributes | ISO/IEC/IEEE 29148, TOGAF Business Capability Modeling, DeMarco/Yourdon Structured Analysis, DDD (Evans), PMI (WBS) |

---

## How to use this index

**If you're Claude Code, working on a specific component:** check which file governs it before writing new logic that touches structure, sequencing, UI, process, or output. If a rule already exists, implement to it. If a genuinely new situation isn't covered by any rule here, that is itself an Open Question (per the PRD framework) — flag it rather than inventing an ungrounded rule on the spot.

**If you're extending the corpus:** every new rule added to any file must follow the same four-part template and must cite a real, named source. A rule with no grounding does not belong in this corpus — put it in the PRD's Open Questions instead until a grounding is found or a deliberate decision is made to adopt it as a project-specific convention (and label it as such, not as an established principle).

**Cross-references between files are intentional, not duplication.** Several rules restate an earlier one at a more specific layer (e.g. NT8 restates WD8 at the node-configuration level, P3 restates WD10 at the variable level). Where this happens, the more specific file says so explicitly rather than re-deriving the same idea independently. This is deliberate: one underlying principle, applied consistently at every layer it touches, rather than seven unrelated rule sets that happen to agree by coincidence.

---

## Full rule count

- Workflow Design: 12
- Governance: 10
- UI Design: 10
- Development Process: 11
- Decomposition Engine: 8
- Prompting: 7
- Node Translation: 9
- Component & Requirements Decomposition: 9

**Total: 76 grounded rules**, each traceable to a named source, each written as a testable predicate.

---

## Relationship to other governing documents

This corpus sits alongside, not instead of:
- `ARCHITEQ-PRD.md` — the numbered requirements (R1-R23) this system must satisfy
- `ARCHITEQ-Build-Directive.md` — the pipeline and component specs
- `ARCHITEQ-Decomposition-Engine-Spec.md` — the machine-checkable JSON predicates this corpus's `decomposition.md` file explains in prose
- `ARCHITEQ-Simulation-Grounding-and-Visual-Fix.md` — the grounding simulation mechanism referenced throughout this corpus
- `ARCHITEQ-Dual-Tree-Architecture.md` — the Component Tree (Python) vs. Workflow Tree (n8n) split this corpus's `component-decomposition.md` file grounds
- `ARCHITEQ-Recursive-Depth-and-Completion-Tracking.md` — unbounded tree depth and the node-level completion rollup mechanism (WD11, WD12, CD9)
- `ARCHITEQ-UI-and-Dev-Loop-Directive.md` — the two-screen structure and dev loop this corpus's `ui-design.md` and `dev-process.md` files ground
- `PROGRESS.md` — module-level tracking against the PRD
- `~/.claude/CLAUDE.md` and the project's own `CLAUDE.md` — where the Autonomy Default and Documentation Sync rules (DP8, DP10) are actually recorded and enforced day to day
- `~/.claude/frameworks/universal-prd-framework.md` — the full six-document pre-build set (PRD, TDD, App Flow, Design Brief, Backend Schema, Engineering Plan) `dev-process.md`'s DP11 grounds; project-independent, applies to every project
- `ARCHITEQ-TDD.md`, `ARCHITEQ-APP-FLOW.md`, `ARCHITEQ-DESIGN-BRIEF.md`, `ARCHITEQ-BACKEND-SCHEMA.md`, `ARCHITEQ-ENGINEERING-PLAN.md` — this project's own instances of DP11's five non-PRD documents

If any of the above documents ever conflicts with a rule in this corpus, treat the conflict itself as an Open Question to resolve deliberately — do not silently let one override the other.
