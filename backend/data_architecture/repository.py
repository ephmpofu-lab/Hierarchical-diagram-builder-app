"""File-based storage for frozen per-domain Data Architectures (Module 13, sub-plan 13a) --
byte-identical convention to backend/component/repository.py's own role for the Component
Tree. A separate directory and module: the Data Architecture is a companion but structurally
distinct artifact, derived from (not merged into) the Workflow Tree."""

import json
from pathlib import Path
from typing import Optional

from ..models import DataArchitecture

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_ARCHITECTURES_DIR = _REPO_ROOT / "data_architectures"


def load_data_architecture(domain: str) -> Optional[DataArchitecture]:
    path = _DATA_ARCHITECTURES_DIR / f"{domain}.json"
    if not path.exists():
        return None
    return DataArchitecture(**json.loads(path.read_text(encoding="utf-8")))


def save_data_architecture(tree: DataArchitecture) -> None:
    _DATA_ARCHITECTURES_DIR.mkdir(parents=True, exist_ok=True)
    path = _DATA_ARCHITECTURES_DIR / f"{tree.domain}.json"
    path.write_text(json.dumps(tree.model_dump(), indent=2), encoding="utf-8")
