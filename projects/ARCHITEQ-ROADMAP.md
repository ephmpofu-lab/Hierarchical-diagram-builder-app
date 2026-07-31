# ARCHITEQ Roadmap — Remaining Workstreams

Planning document only. No implementation in this file. Sequences what comes after the current rules corpus and dual-tree architecture, in the order it should be tackled.

---

## Phase 11: Database/SQL Schema Representation in Nodes

**Problem:** any node or component that touches a database currently shows a generic input/output. It needs to show the actual table structure — fields, types, primary keys, foreign keys — not a blob labeled "data."

**What this requires:**
- A schema representation format attached to any atomic step/attribute tagged as database-related: table name, column list (name, type, nullable), primary key(s), foreign key(s) with their referenced table/column.
- This is a new field type on top of the existing `requires`/`produces`/`rules` fields — call it `schema_ref` — populated whenever a node's data contract is a relational table rather than an opaque object.
- Applies to both trees: in the Component Tree, a database-backed Component's Attributes include its table schema; in the Workflow Tree, a Storage/Retrieval-layer atomic step's `produces`/`requires` shows the actual table it reads/writes.

**Grounding to use when this is written up properly:** Entity-Relationship Modeling (Peter Chen, "The Entity-Relationship Model," 1976) — the standard notation for representing entities, attributes, and relationships (which is exactly primary/foreign key structure) independent of any specific database engine.

**Sequencing note:** this slots into the existing corpus as an extension of P4/CD (dependency and attribute rules) and NT6 (constraints become node parameters) rather than a new rule category — it's a specific case of "rules[] becomes visible on the node," applied to database-backed nodes specifically.

---

## Phase 12: Agent Orchestration Decision Framework

**Problem:** whether ARCHITEQ (or a system it designs) should use one agent or several, and if several, which orchestration pattern (LangGraph supervisor, swarm, hierarchical, network), needs to be a deterministic, grounded decision — not a preference call made per project.

**Grounding already confirmed, ready to use when this is written up:**

- Anthropic's own published guidance (<cite index="39-1">"Building Effective Agents"</cite>) is explicit: start simple, add agentic complexity only when a single agent demonstrably falls short, since <cite index="39-1">agentic systems trade latency and cost for better task performance.</cite>
- Anthropic's follow-up guidance names the three specific conditions under which multiple agents outperform one: <cite index="36-1">when context pollution degrades performance, when tasks can run in parallel, and when specialization improves tool selection or task focus.</cite> Outside those three, <cite index="36-1">coordination costs typically exceed the benefits.</cite>
- Cost reality that must be part of the decision, not an afterthought: <cite index="41-1">multi-agent systems consume approximately fifteen times more tokens than standard chat interactions,</cite> so <cite index="41-1">they are best suited for tasks where the value of the outcome outweighs the expense,</cite> and <cite index="41-1">they excel at problems that can be divided into parallel strands... but are less effective for tightly interdependent tasks such as coding.</cite> This last point matters directly for ARCHITEQ, since the Decomposition Engine's own output feeds tightly interdependent code generation — a candidate case for staying single-agent even where parallelism looks tempting.
- If multi-agent is warranted, LangGraph's own pattern vocabulary gives the deterministic choice of shape: **Supervisor** (one central orchestrator routes to specialists, most widely used, best when tasks are clearly separable), **Swarm** (agents hand off to each other directly, no central orchestrator, better for conversational handoff), **Hierarchical** (supervisor of supervisors, for genuinely large specialist teams), **Network** (every agent can call every other agent — flagged in the source material itself as the least controlled option, effectively a last resort).

**What this becomes when written up:** a decision tree, not a discussion — e.g. "does the task require context isolation, parallelism, or specialization? No to all three → single agent. Yes → which LangGraph pattern fits the team size and interdependency shape?" This should be a genuinely deterministic predicate, same discipline as everything else in the corpus, not a judgment call left to whoever is building.

**Sequencing note:** this becomes its own new rules file — `rules/principles/agent-orchestration.md` — the corpus's 9th file, since it's a distinct decision domain (not workflow design, not governance, not node translation) with its own grounding.

---

## Phase 13: Orchestration-Specific Prompting Rules

**Problem:** `prompting.md` currently governs ARCHITEQ's own internal LLM calls (Intent Parser, grounding simulation). It does not yet cover how a multi-agent system ARCHITEQ designs should be prompted — supervisor-to-subagent task handoff, subagent-to-supervisor result reporting, context isolation boundaries between agents.

**What this requires:** extend `prompting.md` with rules specific to inter-agent prompting — e.g. a supervisor's delegation instruction to a subagent must state scope boundaries explicitly (grounded in Anthropic's own documented failure mode: <cite index="38-1">vague instructions... often were vague enough that subagents misinterpreted the task or performed the exact same searches as other agents</cite>), and a subagent's report back to its supervisor must be distilled, not raw context dump (this is literally the context-isolation benefit from Phase 12's own grounding, made into a prompting rule).

**Sequencing note:** this depends on Phase 12 existing first — the orchestration pattern decision determines what shape the prompting rules need to take (supervisor/subagent framing is different from swarm handoff framing).

---

## Phase 14: Deep-Tree Visual Navigation ("Where Am I")

**Problem:** now that tree depth is uncapped (per the Recursive Depth addendum) and can genuinely run ten, twenty, thirty levels deep, a user drilling into one branch can lose track of where they are relative to the whole tree, especially since it won't fit on one screen.

**What this requires, sequenced as its own design pass:**
- A persistent breadcrumb trail showing the path from root to current node (e.g. `RAG → Ingestion → Document Ingestion → Parsing → extract_text_content`), always visible, not something you have to scroll up to find.
- A minimap or collapsed overview of the whole tree, showing current position as a highlighted marker against the full structure — the same pattern IDEs use for large files and games use for large maps, so the brain has a fixed reference point even while deep in one branch.
- Depth is communicated visually (e.g. indentation, breadcrumb length) so a user can tell "I am 14 levels deep" at a glance without counting.
- This must be designed as an extension of the existing UI corpus, not a bolt-on: UI9 (Gestalt Grouping) already governs hierarchy legibility; this phase adds the specific mechanism for legibility *at depth*, which UI9 doesn't yet cover on its own.

**Grounding to use when this is written up:** Kevin Lynch, "The Image of the City" (1960) — the foundational wayfinding-design literature on how people orient themselves in large, complex spaces using landmarks and paths; directly applicable to navigating a large, complex tree, not just physical space. Also standard IDE/file-explorer minimap conventions as a live precedent, the same way Railway's dashboard was used as a precedent earlier.

**Sequencing note:** this becomes new rules appended to `ui-design.md` (UI11, UI12) once written up properly — not a new file, since it's clearly still UI design territory, just a gap UI1-10 didn't anticipate before depth became uncapped.

---

## Phase 15: CI/CD (deferred, noted for later strategizing)

Not detailed yet. Once Phases 11-14 are written up and implemented, CI/CD (automated testing on commit, deployment pipeline for the app itself, not the workflows it generates) becomes the next logical planning session. Flagged here only so it isn't lost, not sequenced in detail yet.

---

## Recommended Order

```
Phase 11 (DB schema) and Phase 12 (orchestration decision) can be planned in parallel —
they don't depend on each other.

Phase 13 (orchestration prompting) depends on Phase 12 being decided first.

Phase 14 (deep-tree navigation) can be planned independently of 11-13, but should be
written up before the app is used on any tree that actually goes past ~5-6 levels deep
in practice, since that's when the "lost in the tree" problem becomes real rather than
theoretical.

Phase 15 (CI/CD) is deferred until 11-14 are settled.
```

## What This Roadmap Deliberately Does Not Do

Per the instruction this document was created under: no rule files are written yet, no predicates, no schema formats finalized. This is the sequencing and grounding-source plan only. Each phase above becomes its own detailed, grounded addendum (following the same Statement/Grounding/Applies-to/Predicate template as the rest of the corpus) when its turn comes.
