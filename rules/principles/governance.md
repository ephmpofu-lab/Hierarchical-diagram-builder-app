# Rules and Principles: Governance

Part of `rules/principles/`. Governs traceability, accountability, and oversight across every part of ARCHITEQ — the decomposition engine, the renderers, and the workflows it produces. This file is the general-purpose governance layer; AISA (Dr. Mpofu's existing governance framework) sits on top of this as the applied/domain-specific layer, not as a replacement for it.

Template per rule: **Statement | Grounding | Applies to | Predicate**

---

## G1 — Traceability

**Statement:** Every element in a generated tree, rendered output, or n8n workflow must be traceable back to the specific requirement, rule, or grounded trace entry that produced it.

**Grounding:** NIST AI Risk Management Framework (AI RMF 1.0), the Map function, which requires context and provenance to be established and traceable before a system is deployed; also EU AI Act Article 12 (record-keeping obligations for high-risk AI systems).

**Applies to:** Decomposition Engine, Validator, Node Mapper, JSON Exporter.

**Predicate:**
```
for each atomic_step:
    a traceable origin exists: either a grounded trace entry (Stage 2.5) or
    an explicit manual edit record
    else REJECT, reason: "step has no traceable origin"
```

---

## G2 — Accountability

**Statement:** Every action that changes a tree, a checklist, or a cached grounding file has an identifiable responsible party — a named user, or the system component acting under an explicit rule.

**Grounding:** ISO/IEC 42001 (AI management systems standard), which requires defined roles and responsibilities for AI system governance; EU AI Act Article 26, which places specific obligations on deployers to know who is responsible for what.

**Applies to:** Domain checklist authoring, grounding refinement (Section 2a of the Simulation Grounding addendum), Settings screen edits.

**Predicate:**
```
every write to rules/domain_checklists/, rules/*.grounding.json, or
rules/decomposition_principles.json carries an actor field
(user id, or "system: <rule id>" for automated writes)
```

---

## G3 — Auditability

**Statement:** Any past state of a tree, checklist, or grounding cache must be reconstructable after the fact, not just its current state.

**Grounding:** EU AI Act Article 12, which requires automatic logging of events across a high-risk AI system's lifecycle sufficient to reconstruct what happened; this is also the practical justification for the `grounding_version` mechanism already specified.

**Applies to:** Grounding cache (Section 2a), domain checklists, Validator decisions.

**Predicate:**
```
no destructive overwrite is permitted on grounding_version history,
domain checklist versions, or Validator rejection logs; all changes
are append-only with a version/timestamp
```

---

## G4 — Human Oversight on Irreversible Actions

**Statement:** Any action that is not reversible without cost (deploying a rendered workflow, overwriting a cached grounding trace, deleting rather than archiving legacy code) requires an explicit human confirmation step before execution.

**Grounding:** EU AI Act Article 14 (human oversight requirement for high-risk AI systems); also directly consistent with the Reset & Rebuild Directive's own rule of moving discarded code to `legacy/` rather than deleting it outright.

**Applies to:** Reset/rebuild operations, grounding refinement triggers, n8n JSON export (the export itself is reversible; actually deploying it into a live n8n instance is the irreversible action and sits outside ARCHITEQ's own scope per the PRD's Non-Goals).

**Predicate:**
```
for each action tagged irreversible == true:
    an explicit confirmation step precedes execution
    else REJECT, reason: "irreversible action attempted without human confirmation"
```

---

## G5 — Transparency of Function

**Statement:** Every atomic step must be describable, in plain language, in terms a non-technical stakeholder can understand what it does and why it exists in the tree.

**Grounding:** EU AI Act Article 13 (transparency and provision of information to users); this is also why the Atomicity Test's single-verb, single-object criterion (Decomposition Engine Spec Section 5) doubles as a transparency mechanism, not just a structural one — a step that can't be described in one clear sentence is also a step nobody outside the build team could audit.

**Applies to:** Node Detail Panel (UI directive Screen 2), tree generation.

**Predicate:**
```
every atomic_step's description field is a single sentence, single verb,
single object (already enforced by the Atomicity Test); no jargon-only
labels without an accompanying plain-language description
```

---

## G6 — Data Provenance

**Statement:** Every external data input a workflow consumes (uploaded files, API responses, database records) must have its origin documented at the point it enters the tree, not assumed.

**Grounding:** NIST AI RMF Map function (data and content provenance); ISO/IEC 42001's requirements around data quality and lineage management.

**Applies to:** Ingestion-type layers specifically, Stage 2.5 grounding simulation (the Operator/Builder trace should surface where data actually originates).

**Predicate:**
```
every atomic_step in a layer classified as an entry point (no requires[]
from within the tree) must declare a data_source field describing where
its input originates externally
```

---

## G7 — Risk Tiering

**Statement:** Every domain checklist declares a risk tier for the class of system it produces, using the EU AI Act's own categories, so downstream governance obligations scale appropriately rather than applying one blanket standard to everything.

**Grounding:** EU AI Act's risk-based approach: unacceptable risk, high risk, limited risk, minimal risk. A RAG system handling personal data, for instance, sits differently than a RAG system over public documentation.

**Applies to:** Domain checklist files (`rules/domain_checklists/{domain}.json`), which should gain a `risk_tier` field alongside the existing `derived_from` field.

**Predicate:**
```
every domain checklist file declares risk_tier: one of
"unacceptable" | "high" | "limited" | "minimal"
a tree cannot be generated from a checklist with risk_tier == "unacceptable"
```

---

## G8 — Immutable Record-Keeping

**Statement:** Committed trees, rendered outputs, and Validator rejection events are logged in an append-only record, distinct from the live working state, so the system's history cannot be silently altered.

**Grounding:** EU AI Act Article 12 (automatic logging); NIST AI RMF Manage function (ongoing monitoring and incident response depends on an intact historical record).

**Applies to:** PROGRESS.md's own module-completion history, Validator, JSON Exporter.

**Predicate:**
```
every Validator pass/fail decision and every Commit event (per the
Development Loop) is appended to a log file, never overwritten in place
```

---

## G9 — Least Privilege

**Statement:** Any atomic step or node that requires access to credentials, external systems, or user data declares exactly the access it needs and no broader scope.

**Grounding:** NIST SP 800-53 and ISO/IEC 27001, the standard security-governance principle that access should be minimized to what a function actually requires, reducing blast radius on failure or compromise.

**Applies to:** Node Mapper (n8n nodes touching credentials, e.g. HTTP Request nodes with API keys), Python Renderer (function stubs that take config/secrets as arguments).

**Predicate:**
```
every atomic_step tagged security_relevant (per P8) declares an
access_scope field naming exactly what it needs; no step is granted
broader credentials than its declared scope
```

---

## G10 — Contestability

**Statement:** A user must be able to ask why any specific atomic step exists or is structured the way it is, and receive an answer that points to a specific rule, grounded trace entry, or requirement — not a generic justification.

**Grounding:** EU AI Act's transparency obligations combined with GDPR Article 22's right to explanation for automated decisions — while ARCHITEQ's output isn't itself an automated decision about a person, the same discipline (a decision must be explicable, not just assertable) is the right standard to hold the Decomposition Engine to, given it's producing governance-relevant systems as its actual output.

**Applies to:** Node Detail Panel (should surface "why this step" on request), persistent refine input (a user's "why is X here" question should resolve to a rule citation, not a restated description).

**Predicate:**
```
for any atomic_step, a query "why does this step exist" resolves to at
least one of: the domain checklist's derived_from, the grounded trace
entry, or a specific rule ID (P1-P8, WD1-WD10, G1-G10) — never "the
model generated it this way" with no further citation
```

---

## Summary Table

| ID | Rule | Grounding |
|----|------|-----------|
| G1 | Traceability | NIST AI RMF (Map); EU AI Act Art. 12 |
| G2 | Accountability | ISO/IEC 42001; EU AI Act Art. 26 |
| G3 | Auditability | EU AI Act Art. 12 |
| G4 | Human Oversight on Irreversible Actions | EU AI Act Art. 14 |
| G5 | Transparency of Function | EU AI Act Art. 13 |
| G6 | Data Provenance | NIST AI RMF (Map); ISO/IEC 42001 |
| G7 | Risk Tiering | EU AI Act risk-based approach |
| G8 | Immutable Record-Keeping | EU AI Act Art. 12; NIST AI RMF (Manage) |
| G9 | Least Privilege | NIST SP 800-53; ISO/IEC 27001 |
| G10 | Contestability | EU AI Act transparency obligations; GDPR Art. 22 (by analogy) |

## Relationship to AISA

AISA is Dr. Mpofu's existing applied governance framework (referenced at dr-ephraim-mpofu.com/aisa). This file is the general-purpose grounding layer beneath it: where AISA makes domain-specific or client-specific governance judgments, it should cite back to G1-G10 (or the source standards directly) rather than restating governance theory independently. This keeps ARCHITEQ's internal governance and Dr. Mpofu's external consulting framework consistent with each other instead of drifting into two separate vocabularies for the same underlying obligations.

This file is referenced from `RULES-INDEX.md`. Next in the corpus: UI design.
