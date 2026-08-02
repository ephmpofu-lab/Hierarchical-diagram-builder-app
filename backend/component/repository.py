"""File-based storage for frozen per-domain Component Trees (Module 11, sub-plan 11l) --
byte-identical convention to backend/taxonomy/repository.py's own role for the Workflow
Tree. A separate directory and module, not a reuse of taxonomy/repository.py: the Component
Tree and Workflow Tree are companion but structurally distinct artifacts for the same
domain (flat, label-linked lists vs. a real id-keyed node tree)."""

import json
from pathlib import Path
from typing import Optional

from ..models import ComponentTree

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_COMPONENT_TREES_DIR = _REPO_ROOT / "component_trees"


def load_component_tree(domain: str) -> Optional[ComponentTree]:
    path = _COMPONENT_TREES_DIR / f"{domain}.json"
    if not path.exists():
        return None
    return ComponentTree(**json.loads(path.read_text(encoding="utf-8")))


def save_component_tree(tree: ComponentTree) -> None:
    _COMPONENT_TREES_DIR.mkdir(parents=True, exist_ok=True)
    path = _COMPONENT_TREES_DIR / f"{tree.domain}.json"
    path.write_text(json.dumps(tree.model_dump(), indent=2), encoding="utf-8")
