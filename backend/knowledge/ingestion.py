"""Knowledge acquisition: ingestion + parsing (Phase 6 §3 stages 2-3). A curated Markdown
document carries one or more fenced ```yaml blocks, one KnowledgeConcept per block. The
schema is a common core (id, name, category, source, definition, purpose, characteristics,
rules, validation, related) plus an open extension -- any other key a curator writes (e.g.
`domains:`, `lifecycle:`, both real fields already seen in the Knowledge Base's own content)
is retained in `extended`, never silently discarded.

A malformed block is reported as an error string and skipped -- one bad concept in a
multi-concept document must not abort the rest of the batch (Phase 6 §3)."""

import re
from typing import List, Tuple

import yaml

from ..models import KnowledgeConceptCreate
from .classification import classify

_YAML_BLOCK = re.compile(r"```ya?ml\s*\n(.*?)```", re.DOTALL)

_CORE_KEYS = {
    "id",
    "name",
    "category",
    "source",
    "chapter_source",
    "section_source",
    "definition",
    "purpose",
    "characteristics",
    "rules",
    "validation",
    "related",
    "supersedes",
}


def parse_markdown(markdown_text: str) -> Tuple[List[KnowledgeConceptCreate], List[str]]:
    candidates: List[KnowledgeConceptCreate] = []
    errors: List[str] = []

    blocks = _YAML_BLOCK.findall(markdown_text)
    if not blocks:
        errors.append("No ```yaml blocks found in the document.")
        return candidates, errors

    for index, block in enumerate(blocks, start=1):
        try:
            candidates.append(_parse_block(block))
        except (yaml.YAMLError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"Block {index}: {exc}")

    return candidates, errors


def _parse_block(block: str) -> KnowledgeConceptCreate:
    data = yaml.safe_load(block)
    if not isinstance(data, dict):
        raise ValueError("YAML block did not parse to a mapping")

    for required in ("id", "name", "category", "definition"):
        if not data.get(required):
            raise ValueError(f"missing required field '{required}'")

    category = classify(str(data["category"]))

    chapter_source = data.get("chapter_source")
    section_source = data.get("section_source")
    source = data.get("source")
    if isinstance(source, dict):
        chapter_source = chapter_source if chapter_source is not None else source.get("chapter")
        section_source = section_source if section_source is not None else source.get("section")

    extended = {k: v for k, v in data.items() if k not in _CORE_KEYS}

    return KnowledgeConceptCreate(
        concept_id=str(data["id"]),
        name=str(data["name"]),
        category=category,
        chapter_source=chapter_source,
        section_source=str(section_source) if section_source is not None else None,
        definition=str(data["definition"]),
        purpose=str(data["purpose"]) if data.get("purpose") is not None else None,
        characteristics=[str(c) for c in (data.get("characteristics") or [])],
        rules=[str(r) for r in (data.get("rules") or [])],
        validation_criteria=[str(v) for v in (data.get("validation") or [])],
        related=[str(r) for r in (data.get("related") or [])],
        extended=extended,
        supersedes=str(data["supersedes"]) if data.get("supersedes") is not None else None,
    )
