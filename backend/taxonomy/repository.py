"""File-based storage for frozen per-domain task-tree taxonomies and domain checklists
(Engineering Decomposition pipeline, Phase 1). Deliberately NOT a Postgres table like
Project/Node -- a domain's taxonomy is authored once (via the Decomposition Engine +
Validator correction loop) and reused identically by every user request in that domain, so
git itself is the right versioning mechanism: inspectable, diffable, and reproducible
without a migration. Mirrors backend/db/postgres_*_repository.py's role as a thin, swappable
storage facade -- everything else in this pipeline calls through this module, never touches
the filesystem directly."""

import json
from pathlib import Path
from typing import List, Optional

from ..models import DomainChecklist, DomainTaskTree

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_TAXONOMIES_DIR = _REPO_ROOT / "taxonomies"
_CHECKLISTS_DIR = _REPO_ROOT / "rules" / "domain_checklists"


def list_domains() -> List[str]:
    """Domains with a frozen task tree -- the set of domains actually usable end to end.
    A domain can have a checklist without a tree yet (mid-authoring); it isn't "usable"
    until both exist, so this is the authoritative list, not the checklist directory."""
    if not _TAXONOMIES_DIR.exists():
        return []
    return sorted(p.stem for p in _TAXONOMIES_DIR.glob("*.json"))


def load_tree(domain: str) -> Optional[DomainTaskTree]:
    path = _TAXONOMIES_DIR / f"{domain}.json"
    if not path.exists():
        return None
    return DomainTaskTree(**json.loads(path.read_text(encoding="utf-8")))


def save_tree(tree: DomainTaskTree) -> None:
    _TAXONOMIES_DIR.mkdir(parents=True, exist_ok=True)
    path = _TAXONOMIES_DIR / f"{tree.domain}.json"
    path.write_text(json.dumps(tree.model_dump(), indent=2), encoding="utf-8")


def load_checklist(domain: str) -> Optional[DomainChecklist]:
    path = _CHECKLISTS_DIR / f"{domain}.json"
    if not path.exists():
        return None
    return DomainChecklist(**json.loads(path.read_text(encoding="utf-8")))


def save_checklist(checklist: DomainChecklist) -> None:
    _CHECKLISTS_DIR.mkdir(parents=True, exist_ok=True)
    path = _CHECKLISTS_DIR / f"{checklist.domain}.json"
    path.write_text(json.dumps(checklist.model_dump(), indent=2), encoding="utf-8")
