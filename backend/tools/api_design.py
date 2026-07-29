"""API Design Tool (ADR-006, WP16h) -- backend/tools/tool.py's API_DESIGN_TOOL entry,
upgraded from not_built to built.

Evidence base: REST's resource-oriented conventions (a resource path names a thing, not
an action), the HTTP method semantics RFC 7231 and most API style guides (Microsoft REST
API Guidelines, Google API Design Guide) agree on -- GET/DELETE conventionally carry no
request body -- and those same guides' recommendation to version an API from the start.
These are deterministic, citable lint-style checks over one endpoint's method and path,
not a judgment call.

This project's own backend/api.py is real evidence that these conventions matter in
practice -- every existing route (/api/projects/{id}/nodes/{id}/decompose, /api/tools/...)
already follows noun-resource naming; this tool makes that discipline checkable and
citable rather than implicit.

Deliberately NOT wired into api.py's own route table yet -- same reasoning as WP16a-g.
Exists today as its own independently callable tool that could, in the future, be pointed
at this project's own FastAPI route list."""

import re

from ..models import APIDesignResult, APIDesignSignals

_VERB_WORDS = {
    "get", "create", "update", "delete", "remove", "add", "set",
    "list", "retrieve", "fetch", "process",
}
_NO_BODY_METHODS = {"GET", "DELETE"}
# Splits on '/', '_', '-', and camelCase boundaries (lowercase followed by uppercase) --
# the standard technique for tokenizing a path into its constituent words.
_SEGMENT_SPLIT = re.compile(r"[/_\-]|(?<=[a-z])(?=[A-Z])")


def assess(signals: APIDesignSignals) -> APIDesignResult:
    findings: list[str] = []
    blocking = 0

    segment_words = {seg.lower() for seg in _SEGMENT_SPLIT.split(signals.path) if seg}
    found_verbs = sorted(_VERB_WORDS & segment_words)
    if found_verbs:
        findings.append(
            f"Path contains verb-like segment(s) {found_verbs} -- REST resource paths "
            f"should name a thing, not an action (Microsoft REST API Guidelines)."
        )
        blocking += 1

    method = signals.method.upper()
    if method in _NO_BODY_METHODS and signals.has_request_body:
        findings.append(
            f"{method} requests conventionally carry no request body (RFC 7231) -- "
            f"unconventional per REST guidelines."
        )
        blocking += 1

    if not signals.has_version_segment:
        findings.append(
            "No API version segment detected -- most API style guides recommend "
            "versioning from the start to avoid breaking changes later."
        )
        # informational only -- does not gate the verdict, since many APIs version via a
        # header or media type instead of a path segment, and that's not this tool's call to make

    verdict = "Needs Revision" if blocking > 0 else "Follows REST Conventions"
    return APIDesignResult(
        verdict=verdict,
        rationale=f"{blocking} blocking finding(s) out of {len(findings)} total.",
        findings=findings,
        signals=signals,
    )


def explain(result: APIDesignResult) -> str:
    """Optional: phrase already-computed findings in prose. Never adds, removes, or
    reweights a finding -- mirrors WP16a-g's own explain() split."""
    from ..ai import service as ai_service

    prompt = (
        f"In two or three sentences, explain to a non-technical stakeholder why this "
        f"API endpoint was assessed as '{result.verdict}', given these findings: "
        f"{'; '.join(result.findings) or 'none'}"
    )
    response = ai_service.complete(
        system="You explain API design findings in plain language for a non-technical audience.",
        prompt=prompt,
        max_tokens=200,
    )
    return response.text.strip()
