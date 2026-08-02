"""Data Architecture Layer (Module 13) -- Stage 5 (Persistence Classification) and Stage 6
(Entity Derivation), per docs/ARCHITEQ-Data-Architecture-Layer-Spec.md and ARCHITEQ-PRD.md
R41-R50. Distinct from backend/component/engine.py's Component Tree track and
backend/decompose/engine.py's Workflow Tree track -- this derives a THIRD, synchronized
view from an already-frozen Workflow Tree, never authored independently of it (R41)."""

from typing import Dict, List, Optional, Tuple

from ..intelligence.stages import _ask_json
from ..models import (
    DataAnchor,
    DataArchitecture,
    DataAttribute,
    DataEntity,
    DataRelationship,
    DomainTaskTree,
    PrincipleViolation,
    TaskTreeNode,
    ValidationResult,
)

_VALID_OPERATIONS = {"CREATE", "READ", "WRITE", "UPDATE", "DELETE", "QUERY"}


def classify_atomic_step_operation(step: TaskTreeNode, reasoning_context: str) -> Optional[str]:
    """Stage 5 -- classifies one Atomic step's data-persistence operation (R42). Returns
    one of CREATE/READ/WRITE/UPDATE/DELETE/QUERY, or None when the step only passes/
    transforms transient, non-persisted data -- None is a real, valid answer (TRANSIENT is
    never itself a stored value, per 13a's own scope decision 2), not a failure."""
    data = _ask_json(
        system=(
            "You are classifying one workflow Atomic step's data-persistence behavior. "
            "Determine whether this step CREATEs new persistent data, READs existing "
            "persistent data, WRITEs new records, UPDATEs existing records, DELETEs "
            "records, QUERYs/searches persistent data, or does none of these (it only "
            "passes or transforms transient, in-memory data that is never itself "
            "persisted). Do not assume persistence just because a step produces an output "
            "-- only classify a real operation when the step's own label/notes genuinely "
            "describe touching a durable data store. "
            'Respond with strict JSON only: {"operation": "CREATE"|"READ"|"WRITE"|'
            '"UPDATE"|"DELETE"|"QUERY"|"TRANSIENT"}'
        ),
        prompt=(
            f"Atomic step: {step.label}\nNotes: {step.notes}\nConsumes: {step.consumes}\n"
            f"Produces: {step.produces}\n\nReasoning context:\n{reasoning_context}"
        ),
        max_tokens=200,
    )
    operation = (data.get("operation") or "").strip().upper()
    return operation if operation in _VALID_OPERATIONS else None


def derive_data_entities(
    domain: str,
    classified_steps: List[Tuple[TaskTreeNode, str]],
    reasoning_context: str,
) -> Tuple[List[DataEntity], List[DataAnchor], List[DataRelationship]]:
    """Stage 6 -- given every Atomic step already classified as touching persistent data
    (paired with its own operation from Stage 5), derives the deduplicated set of real Data
    Entities they operate on, in ONE call so two steps naming the same real-world object
    are never modeled as two separate entities (R43) -- the same reasoning
    identify_capabilities (Stage -2) already established for grouping a whole list at once."""
    if not classified_steps:
        return [], [], []

    steps_list = "\n".join(
        f"- [{step.id}] {step.label} ({operation}) -- consumes: {step.consumes}, produces: {step.produces}"
        for step, operation in classified_steps
    )
    data = _ask_json(
        system=(
            "You are deriving the persistent data model for one domain from its already-"
            "classified Atomic steps. Each step below touches persistent data with a known "
            "operation (CREATE/READ/WRITE/UPDATE/DELETE/QUERY). Group these steps by the "
            "real-world data entity/table each one actually operates on -- if two steps "
            "clearly operate on the same entity (e.g. both touch 'document chunks'), they "
            "must map to the SAME entity, never two separate ones. For each entity, "
            "propose a real table name (snake_case) and its real columns with SQL types "
            "(PostgreSQL: UUID, TEXT, INTEGER, TIMESTAMPTZ, JSONB, etc.), marking exactly "
            "one primary key and any foreign keys to another entity in this same list. "
            'Respond with strict JSON only: {"entities": [{"name": str, "description": '
            'str, "attributes": [{"name": str, "type": str, "is_primary_key": bool, '
            '"is_foreign_key": bool, "references_entity_name": str_or_null, "nullable": '
            'bool}]}], "step_entity_map": {"step_id": "entity_name"}}'
        ),
        prompt=f"Domain: {domain}\n\nClassified steps:\n{steps_list}\n\nReasoning context:\n{reasoning_context}",
        max_tokens=2000,
    )

    raw_entities = data.get("entities", [])
    name_to_id: Dict[str, str] = {}
    entities: List[DataEntity] = []
    for index, raw in enumerate(raw_entities):
        name = (raw.get("name") or "").strip()
        if not name:
            continue
        data_id = f"D{index + 1:02d}"
        name_to_id[name] = data_id

    for raw in raw_entities:
        name = (raw.get("name") or "").strip()
        if not name or name not in name_to_id:
            continue
        attrs = []
        for raw_attr in raw.get("attributes", []):
            attr_name = (raw_attr.get("name") or "").strip()
            attr_type = (raw_attr.get("type") or "").strip()
            if not attr_name or not attr_type:
                continue
            references_name = raw_attr.get("references_entity_name")
            attrs.append({
                "name": attr_name,
                "type": attr_type,
                "is_primary_key": bool(raw_attr.get("is_primary_key", False)),
                "is_foreign_key": bool(raw_attr.get("is_foreign_key", False)),
                "references_entity": name_to_id.get((references_name or "").strip()),
                "nullable": bool(raw_attr.get("nullable", True)),
            })
        entities.append(DataEntity(
            id=name_to_id[name], name=name, description=raw.get("description", ""),
            domain=domain, attributes=attrs,
        ))

    relationships: List[DataRelationship] = []
    for entity in entities:
        for attr in entity.attributes:
            if attr.is_foreign_key and attr.references_entity:
                relationships.append(DataRelationship(
                    from_entity=attr.references_entity, to_entity=entity.id, cardinality="1:N",
                ))

    step_entity_map = data.get("step_entity_map", {})
    step_by_id = {step.id: (step, operation) for step, operation in classified_steps}
    anchors: List[DataAnchor] = []
    for step_id, entity_name in step_entity_map.items():
        if step_id not in step_by_id or entity_name not in name_to_id:
            continue
        step, operation = step_by_id[step_id]
        anchors.append(DataAnchor(
            domain=domain, node_id=step.id, node_label=step.label,
            data_id=name_to_id[entity_name], operation=operation,
        ))

    return entities, anchors, relationships


# ============================================================================
# SQL DDL Generator (sub-plan 13c, R45/R17-18) -- deterministic, no AI call, a pure
# function of the canonical DataEntity/DataAttribute model. PostgreSQL only, per the PRD's
# own Non-Goals addition.
# ============================================================================


def _primary_key_name(entity: DataEntity) -> str:
    for attr in entity.attributes:
        if attr.is_primary_key:
            return attr.name
    return "id"  # defensive fallback -- shouldn't happen for a well-formed entity


def _topological_order_by_fk(entities: List[DataEntity]) -> List[DataEntity]:
    """A referenced entity's own CREATE TABLE always precedes any table with a FOREIGN KEY
    into it -- topological sort over the FK graph, mirroring python_renderer.py's own
    _topological_order shape but keyed on references_entity instead of requires."""
    by_id = {e.id: e for e in entities}
    depends_on: Dict[str, set] = {e.id: set() for e in entities}
    for entity in entities:
        for attr in entity.attributes:
            if attr.is_foreign_key and attr.references_entity in by_id and attr.references_entity != entity.id:
                depends_on[entity.id].add(attr.references_entity)

    ordered: List[DataEntity] = []
    placed: set = set()
    remaining = list(entities)
    while remaining:
        ready = [e for e in remaining if depends_on[e.id] <= placed]
        if not ready:
            # A real dependency cycle (shouldn't happen for a well-formed entity set) --
            # never silently drop an entity, just fall back to declared order for the rest.
            ready = remaining
        ready.sort(key=lambda e: e.id)
        for entity in ready:
            ordered.append(entity)
            placed.add(entity.id)
            remaining.remove(entity)
    return ordered


def _attribute_ddl(attr: DataAttribute) -> str:
    column = f"    {attr.name} {attr.type}"
    if attr.is_primary_key:
        column += " PRIMARY KEY"
    elif not attr.nullable:
        column += " NOT NULL"
    if attr.default is not None:
        column += f" DEFAULT {attr.default}"
    return column


def render_sql_ddl(entities: List[DataEntity]) -> str:
    by_id = {e.id: e for e in entities}
    ordered = _topological_order_by_fk(entities)

    statements = []
    for entity in ordered:
        column_lines = [_attribute_ddl(attr) for attr in entity.attributes]
        fk_lines = []
        for attr in entity.attributes:
            if attr.is_foreign_key and attr.references_entity in by_id:
                referenced = by_id[attr.references_entity]
                fk_lines.append(
                    f"    FOREIGN KEY ({attr.name})\n        REFERENCES {referenced.name}({_primary_key_name(referenced)})"
                )
        body = ",\n".join(column_lines + fk_lines)
        statements.append(f"CREATE TABLE {entity.name} (\n{body}\n);")

    return "\n\n".join(statements)


# ============================================================================
# propose_data_architecture orchestrator (sub-plan 13d) -- ties Stage 5 + Stage 6 +
# validation into one real, persistable DataArchitecture, mirroring
# backend/component/engine.py::propose_component_tree's exact retry shape.
# ============================================================================

MAX_DATA_ARCHITECTURE_RETRIES = 3


def validate_data_architecture(architecture: DataArchitecture, workflow_tree: DomainTaskTree) -> ValidationResult:
    """A real, independent safety net over Stage 6's own internal dedup -- same reasoning
    check_attribute_leaf (11h) gave for the Component Tree side: an inner loop trying to
    prevent a problem is not the same as a whole-result check that actually catches it."""
    messages: List[str] = []

    seen_names: Dict[str, str] = {}
    for entity in architecture.entities:
        if not entity.name.strip():
            messages.append(f"Data entity '{entity.id}' has no name")
        elif not any(a.is_primary_key for a in entity.attributes):
            messages.append(f"Data entity '{entity.name}' ({entity.id}) has no primary key attribute")
        if entity.name in seen_names and seen_names[entity.name] != entity.id:
            messages.append(
                f"Data entity name '{entity.name}' is claimed by more than one entity "
                f"({seen_names[entity.name]} and {entity.id}) -- must be deduplicated (R43)"
            )
        seen_names.setdefault(entity.name, entity.id)

    entity_ids = {e.id for e in architecture.entities}
    step_ids = {n.id for n in workflow_tree.nodes.values() if n.level == "Atomic step"}
    for anchor in architecture.anchors:
        if anchor.node_id not in step_ids:
            messages.append(f"Data anchor references a nonexistent Atomic step id '{anchor.node_id}' (R44)")
        if anchor.data_id not in entity_ids:
            messages.append(f"Data anchor references a nonexistent Data entity id '{anchor.data_id}' (R44)")

    violations = [PrincipleViolation(principle_id="DA", message=m) for m in messages]
    return ValidationResult(passed=not violations, violations=violations)


def propose_data_architecture(
    domain: str, workflow_tree: DomainTaskTree, reasoning_context: str
) -> Tuple[DataArchitecture, ValidationResult]:
    """Orchestrates Stage 5 (classify every real Atomic step) -> Stage 6 (derive the
    deduplicated entity set for the whole domain in one call) -> validation, retrying the
    whole pass with the specific violations appended to context on failure, bounded by
    MAX_DATA_ARCHITECTURE_RETRIES -- same posture as propose_tree/propose_component_tree's
    own outer retry loops."""
    context = reasoning_context
    atomic_steps = [n for n in workflow_tree.nodes.values() if n.level == "Atomic step"]
    architecture = DataArchitecture(domain=domain)

    for _ in range(MAX_DATA_ARCHITECTURE_RETRIES):
        classified_steps: List[Tuple[TaskTreeNode, str]] = []
        for step in atomic_steps:
            operation = classify_atomic_step_operation(step, context)
            if operation is not None:
                classified_steps.append((step, operation))

        entities, anchors, relationships = derive_data_entities(domain, classified_steps, context)
        architecture = DataArchitecture(
            domain=domain, entities=entities, anchors=anchors, relationships=relationships,
        )
        result = validate_data_architecture(architecture, workflow_tree)
        if result.passed:
            return architecture, result
        violation_lines = "\n".join(f"- {v.message}" for v in result.violations)
        context = (
            f"{reasoning_context}\n\nYour previous attempt had these violations -- avoid "
            f"them this time:\n{violation_lines}"
        )

    return architecture, result  # last attempt, even if still failing -- caller surfaces violations
