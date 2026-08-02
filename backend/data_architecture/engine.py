"""Data Architecture Layer (Module 13) -- Stage 5 (Persistence Classification) and Stage 6
(Entity Derivation), per docs/ARCHITEQ-Data-Architecture-Layer-Spec.md and ARCHITEQ-PRD.md
R41-R50. Distinct from backend/component/engine.py's Component Tree track and
backend/decompose/engine.py's Workflow Tree track -- this derives a THIRD, synchronized
view from an already-frozen Workflow Tree, never authored independently of it (R41)."""

from typing import Dict, List, Optional, Tuple

from ..intelligence.stages import _ask_json
from ..models import DataAnchor, DataEntity, DataRelationship, TaskTreeNode

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
