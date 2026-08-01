# Plan 10b-iii: Configuration Mechanism (Chip Selection -> Confirm -> Collapse)

**Complexity: Medium.** Resolved by the user (2026-07-31 turn): chips draw from real,
doc-verified option lists added to `rules/n8n_node_schemas.json` (not invented); confirmed
values are client-side/session-scoped only (no new backend persistence). Proceeds through
Build/Test/Commit per the Autonomy Default.

## Requirement

Part of `10b.n8n-node-tile.md`: "suggestion/configuration mechanism (chip selection ->
confirm -> collapse, per-parameter user-input fields with live validation)," for a node
10b-i flags as needing configuration.

## Key finding that narrows scope honestly

Checked every current schema entry's empty-default parameters (`url`, `path`,
`fileSelector`, `query`, `errorMessage`, `jsCode`): every one of them is genuinely free-text
in n8n's own model (a URL, a webhook path, a file path, a SQL query, an error message,
JS code) — none has a real, bounded, doc-verified option set. The parameters that DO have
real finite option sets in n8n's docs (`method`, `httpMethod`) already ship with a sensible
non-empty default in this schema, so they never trigger 10b-i's "needs configuration" flag.
Consequence: chips and free-text inputs are not two treatments of the same "needs config"
field — they're the general mechanism for editing *any* real parameter (chips where a real
option list exists, validated text input otherwise), and today's "needs config" fields
happen to all land in the text-input branch. This is stated honestly rather than forcing
invented options onto the empty fields just to make chips appear there.

## Scope decisions

1. **Schema extension, doc-verified only for fields I'm genuinely confident about**:
   `httpRequest.method` and `webhook.httpMethod` get a new `parameter_options` array
   (`GET`/`POST`/`PUT`/`PATCH`/`DELETE`/`HEAD`/`OPTIONS` for HTTP Request,
   `GET`/`POST`/`PUT`/`PATCH`/`DELETE`/`HEAD` for Webhook — n8n's own well-established
   method dropdowns). Deliberately NOT extended to `postgres.operation`,
   `googleDrive.resource`, `notion.resource`, etc. — I can't verify their exact real option
   strings without live doc access in this environment, and guessing would be inventing
   content this corpus explicitly forbids. Marked with the same `_verified`-style
   "spot-check before import" disclaimer this file's other entries already carry.
2. **`parameter_options` reaches the frontend via the existing `N8nNode` fetch, not a new
   endpoint** — `N8nNode` gains `parameter_options: Dict[str, List[str]]`, populated by
   `_build_parameters` (node_mapper.py) from the matched schema, same "extend the existing
   response" simplification 10a-iii already established for `stage_zones`.
3. **The configuration UI lives inside the existing slide-in drawer**
   (`renderNodeDetailPanel`, opened by 10b-ii's click wiring), not a new panel — a
   "Configure" section appears when `state.mode === "n8n"`, listing every parameter that is
   either empty (per 10b-i's predicate) or a real, editable field: chips (radio-style,
   click to select) when `parameter_options` exists for that key, otherwise a text input.
   Live validation: an empty-value field with no `parameter_options` blocks Save until
   non-blank; a field with `parameter_options` is satisfied the moment a chip is selected.
4. **One "Save configuration" action per node, not per field** — matches "confirm ->
   collapse" as a whole-node action: clicking Save validates every field, and only on
   success writes `state.n8nNodeConfig[step_id]` and re-renders (the needs-config badge
   disappears -- "collapse" -- because 10b-i's predicate is re-evaluated against the merged
   effective parameters, not the raw ones).
5. **Client-side, session-scoped storage only** (`state.n8nNodeConfig`, a plain object keyed
   by `step_id`) — reset alongside `pythonRender`/`n8nRender` whenever the domain changes,
   matching `ARCHITEQ-PRD.md`'s own standing "stateless per-request execution for v1" scope
   decision. Confirmed values are merged into the actual downloaded `workflow.json` (real
   effect, not cosmetic) via a new `n8nEffectiveParameters(node)` helper used both by
   10b-i's badge predicate and by `downloadWorkflowJson`.

## Build

1. **`rules/n8n_node_schemas.json`** — `parameter_options` added to `httpRequest` and
   `webhook` entries only, per scope decision 1.
2. **`backend/models.py`** — `N8nNode.parameter_options: Dict[str, List[str]] =
   Field(default_factory=dict)`.
3. **`backend/render/node_mapper.py::_build_parameters`** (or a small sibling helper) —
   copies the matched schema's own `parameter_options` onto the built `N8nNode`.
4. **`static/js/decompose.js`**:
   - `state.n8nNodeConfig: {}`, reset in `selectDomain`.
   - `n8nEffectiveParameters(node)` — merges `state.n8nNodeConfig[node.step_id]` over
     `node.parameters`.
   - `n8nNeedsConfiguration` (10b-i) updated to check the effective, merged parameters.
   - A "Configure" section inside `renderNodeDetailPanel`, only for `state.mode === "n8n"`:
     one row per parameter needing a real value or offering real chips; a "Save
     configuration" button running the validation above.
   - `downloadWorkflowJson` merges each node's effective parameters into the exported
     `nodes[]` before building the blob.

## Test

1. **Backend (`tests/test_engineering_decomposition.py`)** — `map_tree`/`export_workflow`:
   an HTTP-Request-matching step's mapped node carries `parameter_options.method` with the
   real 7-item list; a step matching a schema with no `parameter_options` (e.g. Postgres)
   carries an empty dict, never a crash or a fabricated list.
2. **Frontend (standalone Playwright harness)** — opening the drawer for a node needing
   configuration shows the Configure section; selecting a chip for a chip-backed field and
   typing a value for a text-backed field, then clicking Save, updates
   `state.n8nNodeConfig` and clears the node's needs-config badge on the next render;
   Save is disabled/blocked while a required text field is still empty. Zero JS errors.

## Commit

One commit: "Add configuration mechanism -- chips, validated inputs, confirm-to-collapse -- for n8n node tiles (sub-plan 10b-iii)."

Once this lands, **Module 10b (n8n Node Tile) is fully complete.**

## Status

- [x] Built — `parameter_options` added to `httpRequest`/`webhook` schema entries;
  `N8nNode.parameter_options`; `_build_parameters`/`map_tree` copy it through;
  `state.n8nNodeConfig`, `n8nEffectiveParameters`, updated `n8nNeedsConfiguration`,
  `renderN8nConfigureSection` (chips or validated text input per parameter, one
  Save-configuration action per node), `downloadWorkflowJson` merges confirmed values into
  the real export, all in `decompose.js`; new config-row/chip/input CSS.
- [x] Tested — 2 new backend tests (`parameter_options` populated correctly for HTTP
  Request, empty for a schema with none); standalone Playwright harness: chip-selection
  path (7 real HTTP methods rendered, Save gated until a chip is picked, badge clears on
  save), real text-input path (HTTP node's own empty `url` field has no chips as expected,
  Save gated until non-blank, badge clears on save), Code node's `jsCode` text field same
  flow — zero JS errors, screenshot-confirmed layout.
- [ ] Committed
