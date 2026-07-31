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
from typing import Any, Dict, List, Optional

from ..models import DomainChecklist, DomainTaskTree

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_TAXONOMIES_DIR = _REPO_ROOT / "taxonomies"
_CHECKLISTS_DIR = _REPO_ROOT / "rules" / "domain_checklists"
_REFERENCE_ARCHITECTURES_DIR = _REPO_ROOT / "rules" / "reference_architectures"
_PRINCIPLES_PATH = _REPO_ROOT / "rules" / "decomposition_principles.json"


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


# ---------- Settings (hidden Screen 3, AMENDMENT 4 item 7) ----------
# Deliberately raw dict in/out, not round-tripped through DomainChecklist/etc -- Settings is
# a lower-guardrail, "reached deliberately" admin surface (spec's own words); a malformed
# save is only caught later, when the pipeline actually tries to use that file, same as
# editing any of these files by hand in git would be.


def list_checklist_domains() -> List[str]:
    """Every domain with a checklist file -- a superset of list_domains() (a domain can
    have a checklist without a frozen tree yet, mid-authoring)."""
    if not _CHECKLISTS_DIR.exists():
        return []
    return sorted(p.stem for p in _CHECKLISTS_DIR.glob("*.json"))


def load_checklist_raw(domain: str) -> Optional[Dict[str, Any]]:
    path = _CHECKLISTS_DIR / f"{domain}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_checklist_raw(domain: str, data: Dict[str, Any]) -> None:
    _CHECKLISTS_DIR.mkdir(parents=True, exist_ok=True)
    path = _CHECKLISTS_DIR / f"{domain}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_reference_architectures() -> List[str]:
    if not _REFERENCE_ARCHITECTURES_DIR.exists():
        return []
    return sorted(p.stem for p in _REFERENCE_ARCHITECTURES_DIR.glob("*.json"))


def load_reference_architecture_raw(name: str) -> Optional[Dict[str, Any]]:
    path = _REFERENCE_ARCHITECTURES_DIR / f"{name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_reference_architecture_raw(name: str, data: Dict[str, Any]) -> None:
    _REFERENCE_ARCHITECTURES_DIR.mkdir(parents=True, exist_ok=True)
    path = _REFERENCE_ARCHITECTURES_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_principles_raw() -> Dict[str, Any]:
    return json.loads(_PRINCIPLES_PATH.read_text(encoding="utf-8"))


def save_principles_raw(data: Dict[str, Any]) -> None:
    _PRINCIPLES_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
