"""The 6 decomposition strategies (Phase 5 section 4) -- WP8, plus Operations (Journey 5
WP21 Amendment 2). Elaborates Phase 4's reasoning pipeline (WP5) one level further: WP5
produces a flat initial proposal for a whole objective; this generates the next level of
children for ONE already-committed node, using whichever strategy its domain (and
abstraction level) selects (section 9). Governance is not one of TOGAF's four architecture
domains, but it decomposes the same way the other four do -- a principle breaks down into
enforceable controls, per section 4's own text.

Operations is likewise not a TOGAF domain -- it is pure operational decomposition (what
work exists: Workspace -> Activity -> Task), used BEFORE any TOGAF domain is assigned.
TOGAF architecture generation only begins once a node's Operations decomposition reaches a
real, atomic Task -- see backend/engineering/service.py::generate_task_architecture. This
is the framework's own stated sequence (Operations Engineering -> Task Classification ->
Recursive Decomposition -> THEN TOGAF Architecture Generation), not a 7th architecture
domain."""

from dataclasses import dataclass, field
from typing import FrozenSet


@dataclass(frozen=True)
class Strategy:
    name: str
    child_guidance: str  # what "one level down" means, for the AI prompt
    stopping_description: str  # human-readable, section 5's stopping condition
    leaf_node_types: FrozenSet[str] = field(default_factory=frozenset)  # node_type values
    # that count as this strategy's terminal level (section 4's "leaf" column)


BUSINESS = Strategy(
    name="Business",
    child_guidance=(
        "Objective decomposes to Capability, Capability decomposes to Process, Process "
        "decomposes to Sub-process. Propose the next level down from the given node."
    ),
    stopping_description="A Process is single-actor, single-step, or realization begins.",
    leaf_node_types=frozenset({"Sub-process"}),
)
DATA = Strategy(
    name="Data",
    child_guidance=(
        "Data Domain decomposes to Entity, Entity decomposes to Attribute. Propose the "
        "next level down from the given node."
    ),
    stopping_description="An Attribute is atomic -- no further sub-fields.",
    leaf_node_types=frozenset({"Attribute"}),
)
APPLICATION = Strategy(
    name="Application",
    child_guidance=(
        "Application decomposes to Module, Module decomposes to Service, Service "
        "decomposes to Interface. Propose the next level down from the given node."
    ),
    stopping_description="A well-defined service/interface boundary is reached.",
    leaf_node_types=frozenset({"Interface"}),
)
TECHNOLOGY = Strategy(
    name="Technology",
    child_guidance=(
        "Service/Component decomposes to Engine, Engine to Component, Component to "
        "Function, Function to Method/Variable/Task. Propose the next level down from "
        "the given node."
    ),
    stopping_description="Task level: directly executable, single owner.",
    leaf_node_types=frozenset({"Task"}),
)
GOVERNANCE = Strategy(
    name="Governance",
    child_guidance=(
        "Principle/Requirement decomposes to Rule, Rule to Validation Criterion, "
        "Validation Criterion to Control. Propose the next level down from the given node."
    ),
    stopping_description="A Control is independently testable/enforceable.",
    leaf_node_types=frozenset({"Control"}),
)
OPERATIONS = Strategy(
    name="Operations",
    child_guidance=(
        "Workspace decomposes to Activity, Activity decomposes to Task. Propose the next "
        "level down from the given node. This is pure operational decomposition -- what "
        "work exists -- never assign a TOGAF domain here."
    ),
    stopping_description="A Task is atomic: directly executable, single owner, ready for "
    "TOGAF architecture generation.",
    leaf_node_types=frozenset({"Task"}),
)

STRATEGIES = {s.name: s for s in (BUSINESS, DATA, APPLICATION, TECHNOLOGY, GOVERNANCE, OPERATIONS)}
