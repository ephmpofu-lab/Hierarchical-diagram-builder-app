"""Deployment Architecture Tool (ADR-006, WP16j) -- backend/tools/tool.py's
DEPLOYMENT_ARCHITECTURE_TOOL entry, upgraded from not_built to built.

Evidence base: the 12-Factor App methodology (Heroku, 2011) -- a specific, well-known,
citable subset of its 12 factors that are checkable as plain booleans: Config (III,
externalized from code), Dependencies (II, explicitly declared and pinned), Processes
(VI, stateless), Build/release/run (V, strictly separated stages), Logs (XI, treated as
event streams to stdout rather than managed by the app). The other 7 factors (Codebase,
Backing services, Port binding, Concurrency, Disposability, Dev/prod parity, Admin
processes) are real but not reduced to a single boolean here -- included only what's
genuinely checkable without inventing a proxy signal, rather than forcing all 12 in for
completeness.

This project's own deployment (WP13c's CI/CD, Railway) is real evidence several of these
already hold in practice -- e.g. config via environment variables (SUPABASE_URL,
DATABASE_URL, AI_PROVIDER), not hardcoded.

Deliberately NOT wired into any existing endpoint yet -- same reasoning as WP16a-i.
Exists today as its own independently callable tool."""

from ..models import DeploymentReadinessResult, DeploymentReadinessSignals

_FACTOR_CHECKS = {
    "Config": "has_externalized_config",
    "Dependencies": "has_pinned_dependencies",
    "Processes": "is_stateless",
    "Build, release, run": "has_separate_build_release_run",
    "Logs": "logs_to_stdout",
}


def assess(signals: DeploymentReadinessSignals) -> DeploymentReadinessResult:
    satisfied = [name for name, field in _FACTOR_CHECKS.items() if getattr(signals, field)]
    unmet = [name for name, field in _FACTOR_CHECKS.items() if not getattr(signals, field)]
    count = len(satisfied)

    if count == len(_FACTOR_CHECKS):
        verdict = "Fully Ready"
    elif count >= 3:
        verdict = "Substantially Ready"
    elif count >= 1:
        verdict = "Partially Ready"
    else:
        verdict = "Not Ready"

    return DeploymentReadinessResult(
        verdict=verdict,
        rationale=(
            f"{count}/{len(_FACTOR_CHECKS)} of the checked 12-Factor App criteria are "
            f"satisfied ({', '.join(satisfied) or 'none'}), which maps to {verdict}."
        ),
        factors_satisfied=satisfied,
        factors_unmet=unmet,
        signals=signals,
    )


def explain(result: DeploymentReadinessResult) -> str:
    """Optional: phrase an already-computed verdict in prose. Never re-derives
    `verdict` -- mirrors WP16a-i's own explain() split."""
    from ..ai import service as ai_service

    prompt = (
        f"In two or three sentences, explain to a non-technical stakeholder why this "
        f"was assessed as '{result.verdict}', given: {result.rationale}"
    )
    response = ai_service.complete(
        system="You explain deployment-readiness assessments in plain language for a non-technical audience.",
        prompt=prompt,
        max_tokens=200,
    )
    return response.text.strip()
