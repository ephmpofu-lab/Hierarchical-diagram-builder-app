"""Database Design Tool (ADR-006, WP16f) -- backend/tools/tool.py's
DATABASE_DESIGN_TOOL entry, upgraded from not_built to built.

Evidence base: Codd's relational model and the classical normal-form definitions (1NF
atomicity/entity-integrity, 2NF no partial key dependencies, 3NF no transitive
dependencies) -- a deterministic, half-century-old, citable checklist, not a judgment
call. Each higher normal form is defined in terms of satisfying the one below it, so this
tool checks them in order and stops at the first one violated, exactly matching Codd's
own nested definitions.

Operates on the Data domain's existing Entity/Attribute decomposition (WP8's Data
strategy already produces Domain -> Entity -> Attribute nodes) via explicit structured
signals about one entity's key structure -- not by parsing raw schema text, since
"does this attribute depend on only part of the key" is a semantic fact about the data,
not something derivable from a label string.

Deliberately NOT wired into the Data Architecture decomposition strategy yet -- same
reasoning as WP16a-e. Exists today as its own independently callable tool."""

from ..models import DatabaseDesignResult, DatabaseDesignSignals


def assess(signals: DatabaseDesignSignals) -> DatabaseDesignResult:
    findings: list[str] = []

    if not signals.has_primary_key:
        findings.append(
            "No primary key defined -- fails 1NF's entity-integrity requirement (Codd, 1970)."
        )
    if signals.has_repeating_groups:
        findings.append(
            "Repeating groups or a multi-valued attribute present -- fails 1NF's "
            "atomicity requirement; split into a separate related entity."
        )
    is_1nf = signals.has_primary_key and not signals.has_repeating_groups
    if not is_1nf:
        return DatabaseDesignResult(
            normal_form="Not 1NF",
            rationale="1NF is not satisfied -- see findings.",
            findings=findings,
            signals=signals,
        )

    if signals.has_composite_key and signals.has_partial_key_dependency:
        findings.append(
            "A non-key attribute depends on only part of the composite primary key -- "
            "fails 2NF; split into a separate entity keyed on that partial key."
        )
    is_2nf = not (signals.has_composite_key and signals.has_partial_key_dependency)
    if not is_2nf:
        return DatabaseDesignResult(
            normal_form="1NF",
            rationale="1NF satisfied; 2NF is not -- see findings.",
            findings=findings,
            signals=signals,
        )

    if signals.has_transitive_dependency:
        findings.append(
            "A non-key attribute depends on another non-key attribute rather than "
            "directly on the primary key -- fails 3NF (transitive dependency); split "
            "into a separate entity."
        )
    is_3nf = not signals.has_transitive_dependency
    normal_form = "3NF" if is_3nf else "2NF"
    rationale = (
        "1NF and 2NF satisfied; 3NF is also satisfied -- no repeating groups, no partial "
        "or transitive dependencies."
        if is_3nf
        else "1NF and 2NF satisfied; 3NF is not -- see findings."
    )
    return DatabaseDesignResult(
        normal_form=normal_form, rationale=rationale, findings=findings, signals=signals
    )


def explain(result: DatabaseDesignResult) -> str:
    """Optional: phrase an already-computed normal form in prose. Never re-derives
    `normal_form` -- mirrors WP16a-e's own explain() split."""
    from ..ai import service as ai_service

    prompt = (
        f"In two or three sentences, explain to a non-technical stakeholder why this "
        f"entity was assessed as '{result.normal_form}', given: {result.rationale}"
    )
    response = ai_service.complete(
        system="You explain database normalization findings in plain language for a non-technical audience.",
        prompt=prompt,
        max_tokens=200,
    )
    return response.text.strip()
