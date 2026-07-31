"""Discovery Session (Journey 4, WP20): an adaptive, multi-turn interview conducted by the
Architect Agent, replacing "pick a template" with "describe the business problem." Reuses
WP5's own AI-calling helpers (`intelligence.stages._ask_json`) rather than inventing a
second JSON-completion path -- same cross-module reuse `blueprint/service.py` already
established. Unlike every other reasoning surface in this app, a Discovery Session is
genuinely stateful across calls: each turn's prompt includes the full transcript and
current topic-coverage state so the Architect Agent can build on what's already been said,
rather than re-deriving context fresh (see `backend/ai/provider.py`'s own docstring on why
every other surface stays stateless)."""

from pydantic import ValidationError

from ..intelligence.stages import _ask_json, ReasoningStageError
from ..models import DiscoveryAgentTurn, DiscoverySession, ProjectInitiationReport

# The topics the Architect Agent must progressively cover before a Project Initiation
# Report can be generated -- a fixed tuple constant, same convention as
# intelligence/stages.py's own DOMAINS tuple.
DISCOVERY_TOPICS = (
    "business_objectives",
    "desired_outcomes",
    "current_processes",
    "pain_points",
    "stakeholders",
    "existing_systems",
    "constraints",
    "regulations",
    "success_criteria",
    "available_documentation",
)

# A small fixed constant, not adaptive -- same posture as MAX_GOVERNANCE_LOOPS
# (intelligence/pipeline.py). Revisited only if it proves limiting in practice.
MAX_DISCOVERY_TURNS = 12


def advance_turn(session: DiscoverySession, user_message: str) -> DiscoveryAgentTurn:
    """One turn of the conversation. `session` reflects the state BEFORE this turn (prior
    turns, prior topic_coverage, turn_count) -- persisting the user's own turn and the
    architect's resulting turn is the API layer's job, not this function's, so this stays
    pure business logic over the transcript it's given."""
    transcript_lines = [f"{t.role}: {t.message}" for t in session.turns]
    if user_message:
        transcript_lines.append(f"user: {user_message}")
    transcript = "\n".join(transcript_lines) if transcript_lines else "(no messages yet -- this is the opening turn)"

    coverage_lines = "\n".join(
        f"- {topic}: {session.topic_coverage.get(topic, 'Unexplored')}" for topic in DISCOVERY_TOPICS
    )

    data = _ask_json(
        system=(
            "You are the Architect Agent, an experienced enterprise/solution architect "
            "conducting an adaptive discovery interview with a prospective project owner. "
            "Your job is to understand their business problem well enough to recommend an "
            "engineering approach -- the objective is NOT to complete a form. Challenge "
            "assumptions, ask a sharper follow-up wherever an answer is vague, and go "
            "deeper on topics still Unexplored or Partial before moving to new ones. If "
            "the conversation is empty, open with a broad question about the business "
            "problem the person is trying to solve. Track coverage across exactly these "
            f"topics: {', '.join(DISCOVERY_TOPICS)}. Only set ready_for_report to true once "
            "every topic is at least Partial and the core objectives, scope, and "
            "stakeholders are clear. "
            'Respond with strict JSON only: {"message": str, "topic_coverage": '
            '{"<topic>": "Unexplored"|"Partial"|"Covered", ...one entry per topic above...}, '
            '"ready_for_report": bool}'
        ),
        prompt=f"Topic coverage so far:\n{coverage_lines}\n\nConversation so far:\n{transcript}",
        max_tokens=700,
    )
    try:
        turn = DiscoveryAgentTurn(**data)
    except (ValidationError, TypeError) as exc:
        raise ReasoningStageError(f"Discovery turn returned malformed output: {data!r} ({exc})") from exc

    # Break out of the loop the same way pipeline.py's own governance retry does, rather
    # than trapping the user in an unbounded conversation.
    if session.turn_count + 1 >= MAX_DISCOVERY_TURNS:
        turn.ready_for_report = True

    return turn


def generate_report(session: DiscoverySession) -> ProjectInitiationReport:
    """One larger call over the whole transcript (mirrors blueprint/service.py's own
    single whole-context call, not per-item). Cross-referencing proposed_operations_model/
    proposed_requirements labels against each other is deliberately NOT validated here --
    that resolution, and the "silently drop anything unresolvable" behavior, happens once,
    at commit time (backend/discovery/commit.py), matching where intelligence/commit.py
    and blueprint/service.py already do their own equivalent resolution."""
    transcript = "\n".join(f"{t.role}: {t.message}" for t in session.turns) or "(no conversation recorded)"

    data = _ask_json(
        system=(
            "You are the Architect Agent concluding a Discovery Session. Given the full "
            "conversation transcript below, produce a complete Project Initiation Report. "
            "proposed_operations_model is a flat list of objects with keys label, "
            "parent_label, node_type, classification, notes -- parent_label is null for a "
            "top-level Recommended Initial Workspace, or another item's own label if it "
            "nests under it as an Engineering Activity. classification must always be the "
            "literal string \"Operations\" for every item -- this is the operations model "
            "(what work exists), not the architecture yet; real TOGAF domains (Business/"
            "Data/Application/Technology) are only assigned later, once a real, atomic Task "
            "is reached. proposed_requirements is "
            "a flat list of objects with keys description, parent_label, "
            "origin_node_label -- parent_label references another requirement's own "
            "description text if it's a sub-requirement, origin_node_label references a "
            "label from proposed_operations_model this requirement traces to. Only "
            "reference labels you actually returned elsewhere in this same response -- "
            "never invent references. Keep the report focused and reviewable: at most 8-10 "
            "proposed_operations_model items total (workspaces plus their activities "
            "combined), at most 6 items in any other list field, and one or two sentences "
            "per prose field -- a human needs to read and approve this in one sitting, not "
            "a full requirements document. "
            'Respond with strict JSON matching exactly these keys: business_problem (str), '
            'business_objectives (list[str]), engineering_scope (str), stakeholders '
            '(list[str]), recommended_solution_type (str), recommended_engineering_approach '
            '(str), recommended_architecture_patterns (list[str]), estimated_complexity '
            '(str), recommended_initial_workspaces (list[str]), proposed_operations_model '
            '(list[object]), recommended_engineering_activities (list[str]), known_risks '
            '(list[str]), knowledge_gaps (list[str]), recommended_next_steps (list[str]), '
            'suggested_knowledge_sources (list[str]), suggested_evidence_collection '
            '(list[str]), proposed_requirements (list[object]).'
        ),
        prompt=f"Discovery Session transcript:\n{transcript}",
        max_tokens=6000,
    )
    try:
        return ProjectInitiationReport(**data)
    except (ValidationError, TypeError) as exc:
        raise ReasoningStageError(f"Discovery report returned malformed output: {data!r} ({exc})") from exc
