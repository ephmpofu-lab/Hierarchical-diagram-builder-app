"""Knowledge retrieval and context assembly (Phase 6 §5): match by category + domain +
keyword, expand one hop via KnowledgeRelationship, then rank and cap. Ranking/capping are
conceptual contracts in the approved architecture ("not a specific retrieval algorithm,
which is an implementation decision for Phase 11/12") -- this is that implementation
decision: keyword-overlap scoring, one-hop expansion, a fixed result cap.

`domain` is a soft keyword hint here, not a separate structured filter -- the Phase 3 meta
model never gave KnowledgeConcept its own TOGAF-domain field (only `category`, which maps to
the Knowledge Base's folder taxonomy, a different axis), so folding it into the same
keyword match is honest about what WP3 actually has to match against rather than inventing
a field beyond this pass's scope.

This retrieves Knowledge-side context only. The Enterprise Repository half of Phase 4 §4's
Reasoning Context (existing DecompositionNodes/Requirements) is the Intelligence Engine's own
concern once it exists (WP4/5) -- out of scope here, since WP3 has no dependency on it."""

import re
from typing import List, Optional

from ..models import KnowledgeConcept, KnowledgeRelationship

DEFAULT_CAP = 20

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set:
    return set(_WORD.findall(text.lower()))


def _concept_text(concept: KnowledgeConcept) -> str:
    return " ".join(
        [
            concept.name,
            concept.category,
            concept.definition,
            concept.purpose or "",
            " ".join(concept.characteristics),
            " ".join(concept.rules),
            " ".join(concept.validation_criteria),
        ]
    )


def retrieve(
    objective: str,
    active_concepts: List[KnowledgeConcept],
    relationships: List[KnowledgeRelationship],
    stage: Optional[str] = None,
    domain: Optional[str] = None,
    cap: int = DEFAULT_CAP,
) -> List[KnowledgeConcept]:
    query_tokens = _tokens(" ".join(filter(None, [objective, stage, domain])))
    if not query_tokens:
        return []

    by_id = {c.concept_id: c for c in active_concepts}
    scored = [
        (c, len(query_tokens & _tokens(_concept_text(c))))
        for c in active_concepts
    ]
    seeds = [c for c, score in sorted(scored, key=lambda pair: pair[1], reverse=True) if score > 0]

    result_ids: List[str] = []
    for c in seeds:
        if c.concept_id not in result_ids:
            result_ids.append(c.concept_id)

    # One-hop expansion: any concept directly related to a seed, via KnowledgeRelationship
    # in either direction, joins the result set (after the direct matches, not ranked above them).
    for rel in relationships:
        for seed_id, other_id in ((rel.from_concept_id, rel.to_concept_id), (rel.to_concept_id, rel.from_concept_id)):
            if seed_id in result_ids and other_id in by_id and other_id not in result_ids:
                result_ids.append(other_id)

    return [by_id[cid] for cid in result_ids[:cap]]
