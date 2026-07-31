# Rules and Principles: Prompting

Part of `rules/principles/`. Governs how ARCHITEQ itself constructs prompts internally — for the Intent Parser's LLM fallback, the Stage 2.5 Operator/Builder grounding simulations, and any future LLM call the system makes. This is not user-facing prompting advice; it is the standard the system's own internal prompts must meet.

Template per rule: **Statement | Grounding | Applies to | Predicate**

---

## PR1 — Structured Output Over Free Text

**Statement:** Any internal LLM call whose result feeds a downstream process (the tree, a checklist, a grounding trace) must request a fixed, parseable structure (JSON matching a declared schema), never free-form prose the system then tries to interpret.

**Grounding:** Anthropic's own published prompt engineering guidance on structured outputs and tool use (docs.claude.com/en/docs/build-with-claude/prompt-engineering) recommends explicit output schemas for any response a program will parse, precisely because free text parsing is a recurring source of silent failure.

**Applies to:** Intent Parser (LLM fallback), Stage 2.5 Operator/Builder simulations, Decomposition Engine's tree proposal step.

**Predicate:**
```
every internal LLM call whose output is consumed by another system
component specifies a target schema in the prompt and validates the
response against that schema before use; an unparseable response is
treated as a failure (per WD2, No Silent Failure), not silently
coerced into a best guess
```

---

## PR2 — Role and Task Are Stated Explicitly, Never Implied

**Statement:** Every internal prompt states plainly what role the model is being asked to play (e.g. "you are simulating a developer implementing this sub-task") and what the single task is, rather than relying on the model to infer intent from context alone.

**Grounding:** Anthropic's prompt engineering guidance on being clear and direct — explicit role and task framing measurably improves output consistency versus leaving intent implicit; this is also the direct restatement of WD10 (Explicit Over Implicit) applied to prompt construction itself.

**Applies to:** Stage 2.5 Operator Simulation and Builder Simulation prompts specifically, since these depend on the model correctly adopting one of two distinct perspectives.

**Predicate:**
```
every simulation prompt begins with an explicit role statement and a
single stated task, before any domain-specific content is included
```

---

## PR3 — Examples Anchor Ambiguous Tasks

**Statement:** Where a task is prone to producing output at the wrong level of granularity (e.g. the grounding simulation, which must avoid both "collect_raw_documents" style over-abstraction and excessive micro-splitting), the prompt includes at least one worked example of correct granularity, not just a description of the target granularity.

**Grounding:** Few-shot prompting is a long-established technique for anchoring model output to a specific format or granularity (documented across Anthropic's prompt engineering guidance and the broader few-shot learning literature, e.g. Brown et al., "Language Models are Few-Shot Learners," 2020) — a worked example disambiguates what description alone often cannot.

**Applies to:** Stage 2.5 grounding simulation prompts specifically, given the concrete failure already observed with `collect_raw_documents`.

**Predicate:**
```
the Operator and Builder simulation prompts each include at least one
worked example demonstrating correct atomic-level granularity, sourced
from an already-validated tree (e.g. the corrected ingestion example)
```

---

## PR4 — Step-by-Step Reasoning Is Requested Where the Task Requires Decomposition

**Statement:** Any internal prompt that itself asks the model to decompose, sequence, or validate something requests explicit intermediate reasoning before the final structured output, rather than asking for the final answer directly.

**Grounding:** Chain-of-thought prompting (Wei et al., "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models," 2022) is well-documented to improve accuracy on multi-step reasoning tasks specifically; Anthropic's own prompt engineering guidance recommends this for tasks with genuine internal structure, distinct from simple lookups where it adds no value.

**Applies to:** Stage 2.5 simulations (both Operator and Builder are inherently sequential decomposition tasks), any future Validator-adjacent LLM call.

**Predicate:**
```
prompts for tasks classified as multi-step (simulation, decomposition
proposals) request reasoning before the structured output; prompts for
single-fact lookups do not, since chain-of-thought adds latency without
benefit there
```

---

## PR5 — Negative Examples Prevent Recurrence of Known Failure Modes

**Statement:** Once a specific failure mode has been identified (e.g. `collect_raw_documents` passing as falsely atomic), the prompt that produces that category of output includes an explicit negative example showing the failure and why it is wrong, not just a positive example of correct behavior.

**Grounding:** Anthropic's prompt engineering guidance on using both positive and negative examples — showing what not to do, and why, closes a specific failure mode more reliably than positive examples alone, which can be satisfied in multiple ways including the unwanted one.

**Applies to:** Stage 2.5 grounding simulation prompts (must reference the `collect_raw_documents` failure specifically), and any future prompt tied to a documented defect.

**Predicate:**
```
whenever a defect is logged against a specific prompt (per G8, Immutable
Record-Keeping), the next revision of that prompt must incorporate the
defect as a negative example before it is considered corrected
```

---

## PR6 — Prompts Are Versioned Artifacts, Not Inline Strings

**Statement:** Internal prompts used for grounding simulation, intent parsing, or any repeated system function are stored as versioned files, not embedded as inline strings scattered through application code.

**Grounding:** This applies WD4 (Determinism) and G3 (Auditability) to prompt text specifically — an inline prompt buried in code cannot be diffed, reviewed, or rolled back the way a versioned artifact can, undermining both reproducibility and audit trail.

**Applies to:** All internal LLM calls.

**Predicate:**
```
every internal prompt template lives in a dedicated, version-controlled
location (e.g. prompts/{name}.md), referenced by the code that uses it,
never written inline at the call site
```

---

## PR7 — Output Length and Format Are Specified, Not Assumed

**Statement:** Every internal prompt states the expected length, format, and any XML/structural tags required in the response, rather than leaving the model to guess an appropriate output shape.

**Grounding:** Anthropic's prompt engineering guidance on specifying format and requesting XML tags for structured extraction — an unspecified format is itself a form of the implicit assumption WD10 already forbids, applied here to prompt construction.

**Applies to:** All internal LLM calls, particularly Stage 2.5 simulations and the Intent Parser's LLM fallback.

**Predicate:**
```
every internal prompt explicitly states the required output format
(e.g. "respond only with JSON matching schema X, no preamble") before
being sent
```

---

## Summary Table

| ID | Rule | Grounding |
|----|------|-----------|
| PR1 | Structured Output Over Free Text | Anthropic prompt engineering guidance |
| PR2 | Role and Task Stated Explicitly | Anthropic guidance; restates WD10 |
| PR3 | Examples Anchor Ambiguous Tasks | Few-shot prompting; Brown et al., 2020 |
| PR4 | Step-by-Step Reasoning for Decomposition Tasks | Wei et al., Chain-of-Thought, 2022 |
| PR5 | Negative Examples Prevent Recurrence | Anthropic guidance on positive/negative examples |
| PR6 | Prompts Are Versioned Artifacts | Restates WD4, G3 for prompt text specifically |
| PR7 | Output Length and Format Specified | Anthropic guidance on format specification |

This file is referenced from `RULES-INDEX.md`. One decision remains open: whether node translation (currently folded into WD9) should be split into its own file given how central it is to the n8n rendering path.
