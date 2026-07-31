"""Intent Parser (doc section 4.1) -- rule-based keyword classifier against known, already-
frozen domains first; LLM fallback (reusing WP5/WP8's own _ask_json convention) only when
the rule-based match is weak or absent. A "new domain" (not in taxonomy.repository's known
list) is a valid result, not an error -- it just means Decomposition Engine's one-time
authoring flow (backend/decompose/engine.py) needs to run before this domain is usable."""

import re
from typing import List, Optional, Tuple

from ..intelligence.stages import _ask_json
from ..models import IntentResult
from ..taxonomy import repository as taxonomy_repo

# Below this, a rule-based hit is too weak to trust on its own -- falls through to the LLM.
_RULE_CONFIDENCE_THRESHOLD = 0.6


def _rule_based_match(text: str, domains: List[str]) -> Optional[Tuple[str, float]]:
    lowered = text.lower()
    best: Optional[Tuple[str, float]] = None
    for domain in domains:
        if re.search(rf"\b{re.escape(domain)}\b", lowered):
            score = 0.95  # whole-word match against a known domain name
        elif domain in lowered:
            score = 0.7  # bare substring hit -- weaker, e.g. a domain name inside another word
        else:
            continue
        if best is None or score > best[1]:
            best = (domain, score)
    return best


def parse_intent(text: str) -> IntentResult:
    domains = taxonomy_repo.list_domains()
    match = _rule_based_match(text, domains)
    if match and match[1] >= _RULE_CONFIDENCE_THRESHOLD:
        domain, confidence = match
        return IntentResult(domain=domain, confidence=confidence, tree_available=True)

    domain_list = ", ".join(domains) if domains else "(none yet)"
    data = _ask_json(
        system=(
            "You are an intent parser for an engineering decomposition system. Given free "
            "text describing something a user wants to build, identify the single-word "
            "domain it belongs to (e.g. 'rag', 'etl', 'chatbot') and any constraints they "
            f"mentioned. Known domains with an existing decomposition: {domain_list} -- "
            "prefer one of these if it genuinely fits; otherwise propose a new, short, "
            "lowercase domain name. "
            'Respond with strict JSON only: {"domain": str, "confidence": float, '
            '"extracted_constraints": {str: str}}'
        ),
        prompt=text,
        max_tokens=300,
    )
    domain = str(data.get("domain", "")).strip().lower() or "unknown"
    confidence = float(data.get("confidence", 0.5))
    constraints = data.get("extracted_constraints") or {}
    return IntentResult(
        domain=domain, confidence=confidence, extracted_constraints=constraints,
        tree_available=domain in domains,
    )
