"""Workflow Verification Tool (ADR-006, WP16g) -- backend/tools/tool.py's
WORKFLOW_VERIFICATION_TOOL entry, upgraded from not_built to built.

Evidence base: BPMN 2.0's structural well-formedness requirements (at least one start
event, at least one end event, no dead/unreachable activities) and van der Aalst's
workflow-net soundness criteria (option to complete: every activity must be reachable
from a start). These are graph-reachability and graph-cycle problems -- real algorithms
(BFS reachability, DFS-based cycle detection), not a judgment call an LLM would be asked
to make.

Operates on an explicit directed graph (node ids, marked start/end ids, edges) rather
than reading a live project's Reference/relationship data directly -- this tool is a pure
function over that graph, the same boundary WP16a-f all keep; a future caller assembles
the graph from a project's actual dependency data (WP11d's Dependencies workspace,
`backend/change/impact.py`'s existing traversal) and passes it in.

A detected cycle is reported but does NOT by itself make the verdict Unsound -- some
workflows have intentional loops (retry, review-and-revise) that are not a defect. Only
missing start/end or an actually-unreachable activity make the graph Unsound, matching
BPMN's own structural requirements rather than a stricter DAG-only assumption that would
be wrong for real-world workflows.

Deliberately NOT wired into any existing endpoint yet -- same reasoning as WP16a-f.
Exists today as its own independently callable tool."""

from ..models import WorkflowVerificationResult, WorkflowVerificationSignals


def _build_adjacency(node_ids: list, edges: list) -> dict:
    graph = {nid: [] for nid in node_ids}
    for edge in edges:
        if edge.from_id in graph:
            graph[edge.from_id].append(edge.to_id)
    return graph


def _reachable_from(starts: list, graph: dict) -> set:
    visited: set = set()
    stack = list(starts)
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                stack.append(neighbor)
    return visited


def _has_cycle(node_ids: list, graph: dict) -> bool:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {nid: WHITE for nid in node_ids}

    def dfs(node: str) -> bool:
        color[node] = GRAY
        for neighbor in graph.get(node, []):
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY:
                return True
            if color[neighbor] == WHITE and dfs(neighbor):
                return True
        color[node] = BLACK
        return False

    for nid in node_ids:
        if color[nid] == WHITE and dfs(nid):
            return True
    return False


def assess(signals: WorkflowVerificationSignals) -> WorkflowVerificationResult:
    graph = _build_adjacency(signals.node_ids, signals.edges)
    findings: list[str] = []

    has_start = len(signals.start_ids) > 0
    has_end = len(signals.end_ids) > 0
    if not has_start:
        findings.append("No start node identified -- BPMN requires at least one start event.")
    if not has_end:
        findings.append("No end node identified -- BPMN requires at least one end event.")

    reachable = _reachable_from(signals.start_ids, graph) if has_start else set()
    unreachable = [nid for nid in signals.node_ids if nid not in reachable]
    if unreachable:
        findings.append(
            f"Unreachable from any start node: {', '.join(unreachable)} -- violates "
            f"workflow soundness' 'no dead activities' criterion (van der Aalst)."
        )

    has_cycle = _has_cycle(signals.node_ids, graph)
    if has_cycle:
        findings.append(
            "A directed cycle exists in the workflow graph -- may be an intentional "
            "loop (e.g. retry or review-and-revise), but flagged since an unintended "
            "cycle risks livelock per workflow soundness theory."
        )

    verdict = "Sound" if (has_start and has_end and not unreachable) else "Unsound"
    return WorkflowVerificationResult(
        verdict=verdict,
        rationale=(
            f"Start present: {has_start}; end present: {has_end}; unreachable "
            f"activities: {len(unreachable)}; cycle present: {has_cycle}. A workflow is "
            f"Sound only when it has a start, an end, and no unreachable activities."
        ),
        has_cycle=has_cycle,
        unreachable_node_ids=unreachable,
        findings=findings,
        signals=signals,
    )


def explain(result: WorkflowVerificationResult) -> str:
    """Optional: phrase an already-computed verdict in prose. Never re-derives
    `verdict` -- mirrors WP16a-f's own explain() split."""
    from ..ai import service as ai_service

    prompt = (
        f"In two or three sentences, explain to a non-technical stakeholder why this "
        f"workflow was assessed as '{result.verdict}', given: {result.rationale}"
    )
    response = ai_service.complete(
        system="You explain workflow-soundness findings in plain language for a non-technical audience.",
        prompt=prompt,
        max_tokens=200,
    )
    return response.text.strip()
