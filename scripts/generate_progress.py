"""R36 -- generates PROGRESS.md's Module-level status from real sub-plan checkboxes,
instead of it being hand-written independently of them (ARCHITEQ-PRD.md R36,
docs/ARCHITEQ-Recursive-Depth-and-Completion-Tracking.md Section 4). The "tree" whose leaf
nodes carry real [ ]/[-]/[x] status here is ARCHITEQ's own .agent/plans/*.md files, each
already carrying a `## Status` section with Built/Tested/Committed checkboxes -- not a
generated end-user domain's own Workflow/Component Tree (a different, unrelated concern).

Only modules with real plan files are computed; a module with none (Modules 1-9 predate
this per-file convention) is left exactly as PROGRESS.md already has it -- there is nothing
real to compute those from, so nothing is guessed or reset.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

# See scripts/run_migrations.py's own comment for why this is needed and why it's a no-op
# when imported (e.g. from tests) rather than run directly.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.component.engine import _rollup_status  # noqa: E402

PLANS_DIR = Path(_PROJECT_ROOT) / ".agent" / "plans"
PROGRESS_PATH = Path(_PROJECT_ROOT) / "PROGRESS.md"

# The one place a module's plan-file convention gets registered -- an explicit table, not a
# guessed regex-to-module-number mapping, so a file is never mis-attributed.
MODULE_PREFIX_TO_HEADING = {
    "10": "Module 10:",
    "11": "Module 11:",
    "12": "Module 12:",
}

_STATUS_LINE_RE = re.compile(r"^- \[( |x)\] (Built|Tested|Committed)\b", re.IGNORECASE)
_MODULE_PREFIX_RE = re.compile(r"^(\d+)")
_INDEX_FILE_RE = re.compile(r"^(\d+)\.")  # bare module prefix, no letter suffix -- the
# module's own top-level index plan (e.g. "11.dual-tree-architecture.md"), as opposed to a
# sub-plan like "11a.requirements-engineering-stage.md"


def parse_leaf_status(path: Path) -> Optional[str]:
    """Reads one .agent/plans/*.md file. Returns None if it has no `## Status` section
    carrying all three Built/Tested/Committed checkboxes (an index/overview plan, not a
    leaf) -- else the rolled-up [ ]/[-]/[x] via the same CD9 predicate the rest of this
    app's completion tracking already uses."""
    text = path.read_text(encoding="utf-8")
    if "## Status" not in text:
        return None
    found: Dict[str, str] = {}
    for line in text.splitlines():
        match = _STATUS_LINE_RE.match(line.strip())
        if match:
            checked, label = match.groups()
            found[label.capitalize()] = "[x]" if checked.lower() == "x" else "[ ]"
    if not {"Built", "Tested", "Committed"} <= found.keys():
        return None
    return _rollup_status([found["Built"], found["Tested"], found["Committed"]])


def compute_module_statuses() -> Dict[str, str]:
    """Groups every leaf plan's own status by module-number prefix (from the filename's
    leading digits), then applies the same rollup predicate again across each module's
    leaves -- a flattened, one-level rollup, matching what PROGRESS.md itself tracks (one
    line per Module, regardless of how deeply nested the real plan-file tree is).

    A module only ever computes to "[x]" if it also has its own top-level index plan file
    (bare module number, no letter suffix) -- that index is the one real, inspectable
    confirmation that its sub-plans were meant to exhaustively cover the module's full
    scope (the 100% Rule's own precondition), not just an unblocked partial slice someone
    happened to plan and finish (e.g. Module 12 today has only "12a...", explicitly framed
    in its own title as "(unblocked slice)" -- 5 of R38-R40's 6 artifacts have no plan file
    at all yet, so this module can be real progress ("[-]") but never a false "[x]")."""
    by_module: Dict[str, List[str]] = {}
    has_index: Dict[str, bool] = {}
    for path in sorted(PLANS_DIR.glob("*.md")):
        prefix_match = _MODULE_PREFIX_RE.match(path.stem)
        if not prefix_match:
            continue
        prefix = prefix_match.group(1)
        if prefix not in MODULE_PREFIX_TO_HEADING:
            continue
        has_index.setdefault(prefix, False)
        if _INDEX_FILE_RE.match(path.stem):
            has_index[prefix] = True
        status = parse_leaf_status(path)
        if status is None:
            continue
        by_module.setdefault(prefix, []).append(status)

    results = {}
    for prefix, statuses in by_module.items():
        rolled = _rollup_status(statuses)
        if rolled == "[x]" and not has_index.get(prefix, False):
            rolled = "[-]"
        results[MODULE_PREFIX_TO_HEADING[prefix]] = rolled
    return results


def apply_to_progress_md(statuses: Dict[str, str], progress_path: Path) -> str:
    """Surgical single-line replacement -- only the leading `[ ]`/`[-]`/`[x]` token on the
    line immediately following a recognized `### Module N:` heading changes; every other
    line (descriptions, Open Blockers, everything else) passes through untouched."""
    lines = progress_path.read_text(encoding="utf-8").splitlines(keepends=True)
    pending_heading: Optional[str] = None
    for i, line in enumerate(lines):
        if line.startswith("### "):
            pending_heading = None
            for heading_text in statuses:
                if heading_text in line:
                    pending_heading = heading_text
                    break
            continue
        if pending_heading is not None and re.match(r"^`\[[ \-x]\]`", line):
            new_status = statuses[pending_heading]
            lines[i] = re.sub(r"^`\[[ \-x]\]`", f"`{new_status}`", line, count=1)
            pending_heading = None
    return "".join(lines)


if __name__ == "__main__":
    computed = compute_module_statuses()
    updated_text = apply_to_progress_md(computed, PROGRESS_PATH)
    PROGRESS_PATH.write_text(updated_text, encoding="utf-8")
    for heading, status in computed.items():
        print(f"{heading} -> {status}")
