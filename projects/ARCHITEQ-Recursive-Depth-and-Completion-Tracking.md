# ARCHITEQ — Recursive Depth & Completion Tracking

Addendum to `ARCHITEQ-Decomposition-Engine-Spec.md`, `ARCHITEQ-Dual-Tree-Architecture.md`, and `PROGRESS.md`. Corrects an implicit assumption in the earlier specs: the four C4-derived levels (Layer/Sub-task/Atomic step/Variable, and Capability/Component/Attribute Group/Attribute) are category names, not a depth cap. Real trees may recurse far deeper within those categories. This addendum also introduces node-level completion tracking with mandatory rollup, so progress can be ticked off at any depth, not only at the whole-module grain `PROGRESS.md` currently tracks.

---

## 1. Depth Is Determined by Atomicity, Never by a Fixed Level Count

**The four named levels are categories, not a ceiling.** `Layer → Sub-task → Atomic step → Variable` and `Capability → Component → Attribute Group → Attribute` name *what kind* of node something is, not *how many times* decomposition may recurse to get there. A single "Atomic step" candidate may need to split recursively many times — ten, twenty, thirty levels of refinement — before every resulting leaf actually passes the Atomicity Test (P1) or the Attribute-leaf test (CD4). The stopping condition is never "we've reached level 4." It is always: **does this specific node pass the test now, regardless of how many recursive splits it took to get here.**

**House-building analogy, made explicit:** Planning and Architecture (the top of the tree) come before Engineering, which comes before Tasks, which come before the smallest physical thing a task needs (a specific fastener, a specific length of tape). Nothing about this process implies a fixed number of steps between "build a house" and "this specific roll of tape" — the real answer depends on how deep that particular branch actually needs to go before it's truly atomic. Some branches bottom out in three levels. Others take fifteen. Both are correct if the leaf actually passes the atomicity test at that depth.

**Grounding:** This is the Work Breakdown Structure (WBS) principle from project management standard practice (Project Management Institute, "Practice Standard for Work Breakdown Structures"; also formalized in PMBOK). A WBS decomposes a project to arbitrary depth until reaching a "work package" — the smallest unit that can be independently scheduled, assigned, and verified complete. Depth is never fixed in advance; it is determined by when a work package is actually small enough to be unambiguous and verifiable, exactly the same stopping condition the Atomicity Test already uses.

**Amendment to Decomposition Engine Spec Section 2.2 (C4 Model):** the "exactly 4 levels" language is amended to read: *four named categories, each of which may itself require recursive sub-decomposition to reach a leaf that actually satisfies the Atomicity Test (P1) or Attribute-leaf test (CD4); the category name does not change as recursion goes deeper, only the depth does.*

**Predicate:**
```
a node is only a leaf (Atomic step or Attribute) if it independently
passes the relevant atomicity test; a node that has NOT been split
further purely because a level-count target was reached, while still
failing the atomicity test, is a Validator violation
```

---

## 2. Node-Level Completion Tracking

Every node, at any depth in either tree, carries a completion status using the same convention already established in `PROGRESS.md`:

- `[ ]` = Not started (not yet built/verified present)
- `[-]` = In progress
- `[x]` = Completed (built and verified present)

This status lives on the node itself — in the Workflow Tree, on every Layer, Sub-task, Atomic step, and (where independently trackable) Variable; in the Component Tree, on every Capability, Component, Attribute Group, and Attribute.

**In the UI:** the Node Detail Panel (per `ARCHITEQ-UI-and-Dev-Loop-Directive.md` Screen 2) gains a checkbox/status control. Ticking a leaf node `[x]` is how a user marks "this atomic piece is confirmed present" — the tape, in the house analogy. Ticking an n8n node complete in the canvas view and ticking a Python tree node complete both use this same mechanism; it is not two separate systems.

---

## 3. The 100% Rule — Completion Rolls Up, It Is Never Set Independently on a Parent

**Statement:** A non-leaf node's completion status is always computed from its children. It cannot be manually ticked `[x]` while any child beneath it is not `[x]`.

- All children `[x]` → parent automatically becomes `[x]`.
- Any child `[-]` or a mix of `[ ]`/`[x]` → parent is automatically `[-]`.
- All children `[ ]` → parent is `[ ]`.

**Grounding:** This is the WBS "100% Rule" (Practice Standard for Work Breakdown Structures, PMI) — the work represented by a parent element must be 100% accounted for by the sum of its children, with nothing left implicit and nothing double-counted. Applied to completion tracking specifically: a parent cannot be "done" while a child underneath it is not, because that would mean the parent's completion doesn't actually represent all the work it claims to.

**Applies to:** Every non-leaf node in either tree; also governs how Module-level status in `PROGRESS.md` is computed.

**Predicate:**
```
for each non-leaf node:
    node.status = "[x]" if all children.status == "[x]"
    node.status = "[ ]" if all children.status == "[ ]"
    node.status = "[-]" otherwise
no non-leaf node's status field is directly writable by a user action;
it is always derived
```

---

## 4. Relationship to `PROGRESS.md`

`PROGRESS.md`'s existing Module-level tracking (Section 4a of the PRD) becomes the **top-level rollup view** of this same mechanism, not a separately maintained status. A Module in `PROGRESS.md` is `[x]` only when every node beneath its corresponding requirement's tree(s) is `[x]`, per the 100% Rule above — this makes Module-level completion an honest reflection of actual leaf-level completion, rather than a status someone updates by hand based on impression.

**Predicate:**
```
PROGRESS.md's module status is generated from tree node statuses,
never edited directly and independently of them
```

---

## 5. Practical Effect

- A user can drill into any branch of either tree, arbitrarily deep, and tick off the smallest atomic piece once it's actually confirmed present (built, tested, or otherwise verified) — the tape, the specific file-reading atomic step, the specific config attribute.
- Nobody can mark a Layer or Component "done" while something underneath it is still unticked. This is enforced structurally, not by convention.
- `PROGRESS.md` stops being something someone updates from memory and becomes a computed rollup of what's actually true at the leaf level, which directly satisfies DP8 (Documentation Sync Is Part of Definition of Done) with far less manual effort than updating it by hand.
