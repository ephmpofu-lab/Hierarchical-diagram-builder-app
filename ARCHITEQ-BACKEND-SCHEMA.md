# Backend Schema: ARCHITEQ

Per `~/.claude/frameworks/universal-prd-framework.md` Section 2 and `ARCHITEQ-TDD.md` Key
Tech Decision 1. ARCHITEQ's own domain data has no relational database — the schema of
record is the set of Pydantic models below plus the file layout they're persisted to, not a
SQL table set. The one real relational structure in this system is Supabase's own
`auth.users`, referenced but not owned by this app (see Section 5).

Only the Engineering Decomposition & Solution Generation pipeline's models are documented
here (this is the system's live, in-scope domain, per `ARCHITEQ-PRD.md`). The pre-pivot
TOGAF/Project/Node model family in `backend/models.py` is left in place, unused, not wired
into navigation, and is out of scope for this document — see `ARCHITEQ-PRD.md`'s own Context
note on that decision.

---

## 1. Workflow Tree (Layer -> Sub-task -> Atomic step -> Variable)

**`Variable`** — one configurable parameter on an Atomic step.
| Field | Type | Notes |
|---|---|---|
| `name` | str | |
| `default` | str, optional | |
| `description` | str | |

**`TaskTreeNode`** — one node at any level of the Workflow Tree.
| Field | Type | Notes |
|---|---|---|
| `id` | str | |
| `label` | str | |
| `level` | str | `"Layer"` \| `"Sub-task"` \| `"Atomic step"` |
| `parent_id` | str, optional | |
| `children` | list[str] | |
| `requires` | list[str] | other Atomic step ids this one depends on (topological sequencing) |
| `consumes` | str, optional | single named input artifact (Atomicity Test criterion 2) |
| `produces` | str, optional | single named output (Atomicity Test criterion 3) |
| `terminal_output` | bool | true if `produces` is a final output, never consumed downstream |
| `variables` | list[Variable] | Atomic step level only |
| `pillar_tags` | list[str] | Well-Architected pillar ids this step addresses |
| `rules` | list[str] | real constraints (e.g. "accepted formats: pdf, docx, txt"); empty is valid |
| `notes` | str | also used to distinguish same-labeled repeated Layer branches |

**`DomainTaskTree`** — the frozen, versioned taxonomy for one domain.
| Field | Type | Notes |
|---|---|---|
| `domain` | str | |
| `version` | int | |
| `root_ids` | list[str] | top-level Layer node ids, in order; may repeat a label across multiple ids |
| `nodes` | dict[str, TaskTreeNode] | flat, id-keyed — mirrors `Project.nodes`'s own established shape |

**Storage:** `taxonomies/{domain}.json`, one file per domain, written once at approve time.

## 2. Domain Checklist (reference-architecture grounding)

**`LayerChecklistEntry`**
| Field | Type | Notes |
|---|---|---|
| `layer` | str | |
| `tdsp_stage` | str, optional | one of `rules/reference_architectures/tdsp.json`'s stage ids, or None if cross-cutting |
| `cross_cutting` | bool | |
| `input_contract` | list[str] | artifact names this layer consumes |
| `output_contract` | list[str] | artifact names this layer must produce |

**`DomainChecklist`**
| Field | Type | Notes |
|---|---|---|
| `domain` | str | |
| `derived_from` | str | e.g. `"tdsp"` |
| `mandatory_layers` | list[LayerChecklistEntry] | |

**Storage:** `rules/domain_checklists/{domain}.json`.

## 3. Validation

**`PrincipleViolation`**: `principle_id` (P1-P8, or `RefArch`/`C4`), `message`, `node_id`
(optional). **`ValidationResult`**: `passed: bool`, `violations: list[PrincipleViolation]`.
Not persisted — computed per draft/approve/refine call.

## 4. Intent, Rendering, n8n Export

- **`IntentResult`**: `domain`, `confidence`, `extracted_constraints: dict[str, str]`,
  `tree_available: bool`.
- **`RenderedCodeBlock`**: `step_id`, `label`, `code`. Not persisted — rendered per request
  from the frozen tree.
- **`N8nNode`**: `step_id`, `name`, `type`, `type_version`, `position: [float, float]`,
  `parameters: dict`. **`N8nWorkflow`**: `name`, `nodes: list[N8nNode]`,
  `connections: dict`. Not persisted server-side; downloaded client-side as
  `workflow.json`.

## 5. Grounding Simulation (Stage 2.5)

Not yet a named Pydantic model — grounding output is stored as a raw dict via
`backend/taxonomy/repository.py::save_grounding(domain, data)`, keyed by the winning
attempt's frozen sub-task ids, versioned (`grounding_version`, incremented on confirmed
regroup). **Storage:** `rules/domain_checklists/{domain}.grounding.json`.

## 6. Component Tree (Module 11, in progress)

Not yet built. Planned shape, per `ARCHITEQ-Dual-Tree-Architecture.md` and `ARCHITEQ-PRD.md`
R24-R33: `ComponentTreeNode` mirroring `TaskTreeNode`'s flat id-keyed structure, `level` one
of `"Capability" | "Component" | "Attribute Group" | "Attribute"`, plus
`traced_requirements: list[str]` (Capability level, CD1), `realizes_capability: str`
(Component level, CD2), `is_ui: bool` (Component level, marks a UI-bearing component and
gates R33/CD10's conditional App-Flow/Design-Brief requirement), `rationale: Optional[str]`
(Component level, R32/CD10 — required non-empty only when that component's realization was
a genuine, non-deterministic implementation choice). `ExtractedRequirement` (sub-plan 11a,
`text`/`prd_requirement_id`/`domain`) is the first piece of this model family, not yet
committed. `TaskTreeNode` (Workflow Tree) also gains `rationale: Optional[str]` per R32 for
the same reason, checked only when an Atomic step's node-mapping was a genuine choice. This
section is updated as Module 11's sub-plans land, per DP8.

## 7. Auth (not owned by this app)

`AuthenticatedUser` is a request-scoped object built from a verified Supabase JWT, not a
stored model. The only foreign reference into Supabase's own `auth.users` table is
`owner_id` fields on legacy `Project`-family models (unused by the Engineering
Decomposition pipeline, which has no per-user ownership concept — a domain's frozen tree is
shared, not owned).

## 8. What This Explicitly Is Not

Not a relational schema, not a set of SQL `CREATE TABLE` statements, no primary/foreign key
constraints beyond the informal `id`-string references shown above (e.g.
`TaskTreeNode.parent_id` referencing another `TaskTreeNode.id` within the same
`DomainTaskTree.nodes` dict). If a future requirement genuinely needs relational guarantees
(uniqueness, referential integrity enforced at the storage layer, concurrent-write safety),
that is a real, separate architectural decision to make explicitly — not something to
retrofit onto file-based JSON silently.
