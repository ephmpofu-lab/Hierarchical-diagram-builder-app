"""Security Architecture Tool (ADR-006, WP16e) -- backend/tools/tool.py's
SECURITY_ARCHITECTURE_TOOL entry, upgraded from not_built to built.

Evidence base: NIST Cybersecurity Framework's five core functions (Identify, Protect,
Detect, Respond, Recover), OWASP's input-validation discipline, Zero Trust's "verify
explicitly, never assume" principle for authentication/authorization.

Unlike Governance Assessment Tool (WP16c), there is no single named hard gate here --
NIST CSF doesn't nominate one function as overriding the others the way ISO 38500 singles
out Conformance, so this tool is a plain tiered checklist, not a gate-plus-tier model.
Protect is the only function backed by more than one signal (authn/authz, encryption,
input validation) and requires all three -- a partially protected system is not
"protected" in any meaningful sense, so partial credit isn't given within a function,
only across functions.

Deliberately NOT wired into any existing endpoint yet -- same reasoning as WP16a-d.
Exists today as its own independently callable tool."""

from ..models import SecurityAssessmentResult, SecurityAssessmentSignals

_FUNCTION_CHECKS = {
    "Identify": lambda s: s.has_asset_inventory,
    "Protect": lambda s: (
        s.has_authentication_and_authorization
        and s.has_encryption_at_rest_and_in_transit
        and s.has_input_validation
    ),
    "Detect": lambda s: s.has_monitoring_and_logging,
    "Respond": lambda s: s.has_incident_response_plan,
    "Recover": lambda s: s.has_backup_and_recovery_plan,
}


def assess(signals: SecurityAssessmentSignals) -> SecurityAssessmentResult:
    satisfied = [name for name, check in _FUNCTION_CHECKS.items() if check(signals)]
    unmet = [name for name, check in _FUNCTION_CHECKS.items() if not check(signals)]
    count = len(satisfied)

    if count == len(_FUNCTION_CHECKS):
        verdict = "Fully Compliant"
    elif count >= 3:
        verdict = "Substantially Compliant"
    elif count >= 1:
        verdict = "Partially Compliant"
    else:
        verdict = "Non-Compliant"

    return SecurityAssessmentResult(
        verdict=verdict,
        rationale=(
            f"{count}/{len(_FUNCTION_CHECKS)} NIST CSF functions are satisfied "
            f"({', '.join(satisfied) or 'none'}), which maps to {verdict}."
        ),
        functions_satisfied=satisfied,
        functions_unmet=unmet,
        signals=signals,
    )


def explain(result: SecurityAssessmentResult) -> str:
    """Optional: phrase an already-computed verdict in prose. Never re-derives
    `verdict` -- mirrors WP16a-d's own explain() split."""
    from ..ai import service as ai_service

    prompt = (
        f"In two or three sentences, explain to a non-technical stakeholder why this "
        f"was assessed as '{result.verdict}', given: {result.rationale}"
    )
    response = ai_service.complete(
        system="You explain security assessments in plain language for a non-technical audience.",
        prompt=prompt,
        max_tokens=200,
    )
    return response.text.strip()
