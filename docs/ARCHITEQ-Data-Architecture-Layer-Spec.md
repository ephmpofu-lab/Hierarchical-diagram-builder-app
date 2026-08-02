# ARCHITEQ — Data Architecture Layer Specification

Implement the DATA ARCHITECTURE LAYER as a connected architectural layer of the existing Architeq Workflow Layer.

IMPORTANT:
Do not build Data Architecture as an independent ERD/database drawing page.

The Workflow Layer is the MASTER REFERENCE for the system.

The Data Layer is a separate architectural layer/view, but every relevant data object must remain traceable to the exact workflow, exact node, and exact operation that requires it.

---

## 1. Core Architecture Principle

Architeq contains multiple synchronized architectural layers.

For this implementation:

```
WORKFLOW LAYER
      ↕
DATA ARCHITECTURE LAYER
```

The layers have:

- separate layouts;
- separate active views;
- their own optimal arrangement;
- shared architectural relationships.

RULE: LAYERS SHARE RELATIONSHIPS — NOT LAYOUTS.

Do NOT force database tables to occupy the same coordinates as workflow nodes.

The Workflow Layer should have the optimal n8n layout. The Data Layer should have the optimal ERD/data-model layout. Architeq maintains the mappings between them.

## 2. Workflow Is the Master Reference

The Workflow Layer defines execution. The Data Layer should be derived from actual workflow data requirements.

For each workflow node determine whether it: CREATEs data, READs data, WRITEs data, UPDATEs data, DELETEs data, QUERYs data, or only PASSES/TRANSFORMS transient data.

Do NOT automatically create a SQL table for every node output. Distinguish TRANSIENT EXECUTION DATA from PERSISTENT DATA. Only create/suggest persistent data entities where persistence is actually required.

## 3. Workflow + Node Identification

A system may contain multiple workflows. Therefore NEVER identify a relationship using only `N01` or only `WF01`. Every node relationship must preserve BOTH Workflow ID and Node ID.

Example: `WF01:N01`, `WF01:N02`, `WF02:N01`, `WF02:N02` — because N02 can exist in multiple workflows.

```
WF01 — Document Ingestion
    N01 — Define Source Scope
    N02 — Collect Upload Source
    N03 — Extract Text Content

WF02 — Embedding Pipeline
    N01 — Prepare Embedding
    N02 — Embed Chunks
    N03 — Store Embeddings
```

## 4. Data Object Identification

Every persistent data object/table receives its own stable Data ID.

```
D01 — documents
D02 — document_chunks
D03 — embeddings
D04 — users
D05 — chat_sessions
```

These IDs must remain stable across layers.

## 5. Node → Data Mapping

Relevant workflow nodes must receive Data Anchors, e.g.:

```
WF01:N03 Extract Text Content       -> D01 WRITE
WF02:N01 Split Text Into Chunks     -> D02 WRITE
WF02:N02 Embed Chunks               -> D02 READ, D03 WRITE
```

The anchor communicates WHICH DATA OBJECT + WHAT THE NODE DOES TO IT.

## 6. Do Not Duplicate Tables

If multiple nodes use the same table, do NOT create multiple copies of that table. `Split Into Chunks` (D02 WRITE), `Attach Metadata` (D02 UPDATE), and `Embed Chunks` (D02 READ) all reference the SAME `D02 — document_chunks`.

## 7. Data Relationship Types

Keep two relationship families separate:

- A. WORKFLOW ↔ DATA: CREATE, READ, WRITE, UPDATE, DELETE, QUERY
- B. DATA ↔ DATA: PK → FK, 1:1, 1:N, N:M, REFERENCE

Never confuse execution/data-access relationships with relational database relationships.

## 8. Workflow Layer Active

When Workflow is selected: Workflow Layer = 100% prominence, Data Layer = faint underlay/reference. Do NOT place both layers at equal prominence. The workflow remains the primary canvas. Relevant workflow nodes show compact Data Anchors (e.g. `D01 CREATE`, `D02 WRITE`, `D02 READ`, `D03 UPDATE`). The faint Data Layer may appear underneath as a referenced architectural layer. It must NOT interfere with workflow readability.

## 9. Data Layer Active

When the user switches to DATA, reverse the hierarchy: Data Layer = 100% prominence, Workflow Layer = faint master-reference underlay. The Data Layer displays: TABLES, ATTRIBUTES, DATA TYPES, PRIMARY KEYS, FOREIGN KEYS, CONSTRAINTS, RELATIONSHIPS, CARDINALITY.

```
┌─────────────────────────┐
│ D01 documents           │
│ PostgreSQL              │
├─────────────────────────┤
│ id          UUID     PK │
│ filename    TEXT        │
│ mime_type   TEXT        │
│ status      TEXT        │
│ created_at  TIMESTAMPTZ │
└────────────┬────────────┘
             │ 1:N
             ▼
┌─────────────────────────┐
│ D02 document_chunks     │
│ PostgreSQL              │
├─────────────────────────┤
│ id          UUID     PK │
│ document_id UUID     FK │
│ content     TEXT        │
│ chunk_index INTEGER     │
│ metadata    JSONB       │
└─────────────────────────┘
```

## 10. Data Layer Has Its Own Layout

Do NOT reproduce workflow rows as the Data Architecture layout. Arrange tables according to their data relationships (e.g. `documents -> 1:N -> document_chunks -> 1:N -> embeddings`), not workflow row/column position. The Data Layer must be a clean, understandable data model.

## 11. Faint Workflow Reference

When Data Layer is active, retain the Workflow Layer as a faint reference. Do NOT show an unrelated decorative workflow — it must be the REAL underlying workflow(s): workflow name/ID + node IDs + actual node names. Use approximately 10-20% prominence for the underlay. This should feel like CAD/Revit architectural underlay behaviour.

## 12. Cross-Layer Traceability

The user must NEVER wonder "why does this table exist?" or "which workflow/node uses this table?" Every table must be traceable back to the relevant workflow nodes, e.g.:

```
D02 document_chunks
USED BY:
WF01:N08 — Split Text Into Chunks — WRITE
WF01:N09 — Attach Chunk Metadata — UPDATE
WF02:N02 — Embed Chunks — READ
```

## 13. Bidirectional Navigation

Mappings must work both ways.

WORKFLOW → DATA: click a workflow node and expose its associated tables, fields where known, operation type.

DATA → WORKFLOW: click a table and identify/highlight every workflow node using it, e.g. clicking `D02 document_chunks` highlights `WF01:N08 — WRITE`, `WF01:N09 — UPDATE`, `WF02:N02 — READ`.

## 14. Do Not Permanently Draw Every Cross-Layer Line

This creates spaghetti for large architectures. Normal state: compact anchors and matching IDs (e.g. `D02 WRITE`). On HOVER or SELECT: reveal the actual cross-layer relationship lines. When deselected, fade/hide these cross-layer lines again. The relationship remains stored even when the line is hidden.

## 15. Highlight on Select

Selecting either side illuminates the relationship. Selecting `WF02:N02 Embed Chunks` highlights `D02 document_chunks — READ`, `D03 embeddings — WRITE`. Selecting `D03 embeddings` highlights all nodes that CREATE/READ/WRITE/UPDATE/DELETE/QUERY it.

## 16. Table Detail Panel

Selecting a table opens a detail panel containing: Table ID, Table name, Description, Database/platform, Attributes, Data types, PK, FK, Constraints, Indexes where applicable, Relationships, Workflow usage, Node mappings, SQL definition.

## 17. SQL Must Come From the Same Data Model

Do NOT independently generate ERD, SQL, and workflow mappings — they must come from ONE canonical Data Architecture model:

```
DATA ENTITY
   ├── ID
   ├── Name
   ├── Attributes
   ├── Types
   ├── PK
   ├── FK
   ├── Constraints
   ├── Relationships
   ├── Indexes
   ├── Database/Dialect
   └── Workflow/Node Mappings
```

From this single model generate: Visual Table + ERD Relationships + SQL DDL + Workflow Data Anchors.

## 18. SQL View

The selected table should allow viewing/copying generated SQL, e.g.:

```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (document_id)
        REFERENCES documents(id)
);
```

The SQL must remain synchronized with the visual table definition.

## 19. Table Visual Hierarchy

Keep the canvas minimal. Collapsed/default: `D02 / document_chunks / PostgreSQL`. Expanded/selected: full attribute list with types and PK/FK markers. Do not show large SQL blocks directly on the main canvas.

## 20. Data Relationship Routing

Table relationships should be clean and structured. Prefer horizontal/vertical routing + rounded corners. Avoid large diagonal connections, large Bézier curves, lines crossing table bodies, unnecessary crossings. Clearly show cardinality (1, N, or equivalent ERD notation).

## 21. Layer Controls

Provide simple controls: Data Architecture — Active/Underlay/Hidden; Workflow — Active/Underlay/Hidden. Faintness: approximately 10-20% default for underlay. Highlight on Select: ON. Show Relationships: ON/OFF. Show Anchors: ON/OFF. Show Labels: ON/OFF.

## 22. Important Scaling Rule

The system must work with multiple workflows, multiple rows per workflow, many nodes, many tables, and tables shared by multiple workflows. Do not build assumptions around one RAG workflow — the RAG example is only an example of the Architeq architecture engine.

## 23. Final Architecture Model

```
ARCHITEQ SYSTEM MODEL
        ├── Workflow Graph
        │      ├── Workflows
        │      ├── Nodes
        │      └── Execution relationships
        ├── Data Graph
        │      ├── Entities/Tables
        │      ├── Attributes
        │      └── Relationships
        └── Cross-Layer Mapping
               ├── Workflow ID
               ├── Node ID
               ├── Data ID
               └── Operation
```

The Cross-Layer Mapping is what keeps both layers synchronized.

## 24. Non-Negotiable Rules

DO NOT:
- create an independent disconnected Data page;
- force Data layout to copy Workflow layout;
- create a table for every transient node output;
- duplicate a table because several nodes use it;
- identify mappings only by Node ID;
- identify mappings only by Workflow ID;
- permanently show hundreds of cross-layer lines;
- mix SQL code into every canvas table;
- make the faint underlay compete visually with the active layer;
- allow ERD, SQL and workflow mappings to become separate sources of truth.

ALWAYS:
- use Workflow ID + Node ID;
- give persistent data objects stable Data IDs;
- show the operation type;
- maintain bidirectional traceability;
- keep one canonical data model;
- synchronize visual ERD and SQL;
- preserve the Workflow Layer as the master execution reference;
- allow each layer to have its own optimal layout;
- maintain cross-layer relationships regardless of which layer is active.

## Final Target

The user should be able to look at ANY workflow node and understand: "What data does this node use and what does it do to it?" And look at ANY table and understand: "Why does this table exist, which workflow uses it, and exactly which nodes interact with it?"

The Data Layer must therefore be a real architectural layer connected to the Workflow Layer — not merely an ERD displayed underneath it.

---

## Grounding note added during PRD integration (2026-08-02)

This spec's own "WF01/WF02" multi-workflow framing is written generically; ARCHITEQ's real,
current data model has exactly one Workflow Tree (one `DomainTaskTree`) per domain, which
already maps 1:1 to exactly one exportable n8n workflow (`n8n_exporter.py`). Rather than
inventing a new "multiple workflows per domain" concept this app doesn't have, the
Workflow ID in every "WF:N" compound key below is realized as the domain name itself
(already real, already the unit of uniqueness this app uses everywhere else — two different
domains' Atomic steps can otherwise collide on id, e.g. both having an "a1"). Node ID is
realized as the real, already-existing `TaskTreeNode.id` (Atomic step level only — Layers
and Sub-tasks are organizational, never a data-anchor target, matching this spec's own
Section 2's node-level framing). See `ARCHITEQ-PRD.md`'s Data Architecture Layer section
(R41-R50) and `.agent/plans/13.data-architecture-layer.md` for how this spec's 24 sections
map onto real, buildable requirements and sub-plans.
