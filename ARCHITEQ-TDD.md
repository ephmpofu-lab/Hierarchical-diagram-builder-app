# TDD: ARCHITEQ

Tech Design Document, per `~/.claude/frameworks/universal-prd-framework.md` Section 2 and
`rules/principles/dev-process.md` DP11. Companion to `ARCHITEQ-PRD.md` — the PRD says what
and why; this says how, and why the technical choices behind "how" were made. Not a
duplicate of `ARCHITEQ-Build-Directive.md` or `ARCHITEQ-Decomposition-Engine-Spec.md` (those
specify the Decomposition Engine's own algorithm); this document is the whole system's tech
stack and standing technical decisions, one level up from any single pipeline.

---

## 1. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | Python, FastAPI | Single `APIRouter` (`backend/api.py`), all endpoints under `/api/...`. |
| Frontend | Vanilla JS, SVG | No framework. Full-repaint-per-state-change pattern, one `state` object per page. |
| Auth | Supabase Auth | JWT, verified against Supabase's JWKS (`leeway=120` for clock skew). |
| Structured data (auth only) | Postgres (Supabase-managed) | `auth.users`; this app's own domain data does not live in Postgres — see Constraints below. |
| Domain data storage | Versioned JSON files on disk | `rules/`, `taxonomies/`. Git provides the "versioned" requirement; no ORM, no migrations. |
| AI provider | OpenAI API | Real calls, no mock provider in production paths. Reused convention: `intelligence.stages._ask_json`/`_build`. |

## 2. APIs & Integrations

- **OpenAI API** — every AI-authored step in the Decomposition Engine (checklist drafting,
  Stage 2 sub-task generation, Stage 2.5 grounding simulation, Stage 3 structuring, Stage 4
  variable exhaustion, tree refinement) is a real call through this one integration point.
- **Supabase Auth** — session issuance and JWKS-based verification. No other Supabase
  feature (Realtime, Storage, Edge Functions) is used.
- **n8n** — not a live integration. `rules/n8n_node_schemas.json` is a small, hand-curated,
  static set of common core node schemas checked against n8n's published docs; there is no
  live n8n instance connection anywhere in this system (see Key Tech Decisions, item 3).

## 3. Architecture Overview

```
Browser (vanilla JS/SVG)
      |
      |  fetch() -- JSON over HTTPS, Supabase JWT in Authorization header
      v
FastAPI app (backend/api.py, single router)
      |
      +--> backend/decompose/engine.py    -- Workflow Tree Stages 0-4 (+ 2.5 grounding)
      +--> backend/component/engine.py    -- Component Tree Stages -3 to 0 (Module 11, in progress)
      +--> backend/validator/             -- P1-P8, reference-architecture conformance, CD1-CD9 checks
      +--> backend/render/                -- python_renderer, node_mapper, n8n_exporter
      +--> backend/taxonomy/repository.py -- file I/O facade for rules/ and taxonomies/
      |
      +--> OpenAI API (AI calls)
      +--> Supabase (auth verification only)
```

No message queue, no background worker process, no cache layer. Every request is
synchronous request/response; the one async pattern in the app (legacy `Cycle`
polling for the pre-pivot TOGAF/Discovery code) is not used by the Engineering
Decomposition pipeline, which is entirely synchronous per-call.

## 4. Key Tech Decisions

1. **File-based JSON, not Postgres, for domain data.** `rules/decomposition_principles.json`,
   `rules/domain_checklists/*.json`, `rules/reference_architectures/*.json`,
   `taxonomies/{domain}.json` are all git-versioned files, not database rows. Chosen because
   the data is small, low-write-frequency, and benefits from being human-readable and
   diffable in version control — the same property a schema migration system would have to
   work hard to give you. Postgres is kept for exactly one thing (auth), where a real
   relational contract with Supabase's own `auth.users` table is unavoidable.
2. **Decomposition Principles (P1-P8) are Python functions, not a JSON predicate DSL.**
   `rules/decomposition_principles.json` is descriptive metadata (id, name, description,
   severity) for citation and auditability; `backend/validator/principles.py` holds the
   actual enforcement logic. Writing a general predicate-language interpreter for 7-9
   fixed, structurally different rules would be solving a more general problem than this
   system has.
3. **n8n node schemas are hand-curated, not a live-fetched or fully vendored catalog.**
   Originally scoped as "vendored GitHub node definitions, pinned to a tagged release."
   Research during Module 8's build confirmed n8n has no live schema-fetch API endpoint and
   no downloadable full-catalog JSON — the real catalog is TypeScript source
   (`packages/nodes-base/**/*.node.ts`), which this Python stack has no tooling to parse.
   The shipped answer: `rules/n8n_node_schemas.json`, a small set of common core nodes
   (HTTP Request, Set, If, Merge, Webhook, Postgres) each checked by hand against n8n's
   published docs, with the Code node as a mandatory fallback for anything unmatched — so
   no atomic step is ever left unmapped.
4. **Vanilla JS/SVG frontend, not a framework.** Reuses an existing asset (the Tool A
   hierarchical diagram builder this whole application originated from) rather than
   introducing a second frontend stack. The tree-diagram layout/edge-drawing idiom
   (`computeSubtreeLayout`, trunk+bus connectors) is ported from that existing code, not
   reimplemented against a framework's component model.
5. **Two AI calls per grounding step (Operator + Builder), not one.** Stage 2.5's grounding
   simulation deliberately runs two separate traces (a human-by-hand operator trace and a
   developer/code builder trace, builder-primary on merge) rather than one combined call,
   because a single call collapsing both perspectives was the actual root cause of the
   "abstract, ungrounded decomposition" defect this stage was built to fix.
6. **A domain's task tree is authored once and frozen**, not regenerated per user request.
   The Decomposition Engine + Validator correction loop runs exactly once per new domain
   (at draft/approve time); every subsequent request in that domain loads the same frozen
   tree. This is what makes the system's own reproducibility/auditability claims (PRD
   Success Criteria) literal rather than approximate.
