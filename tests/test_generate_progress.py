"""R36 -- PROGRESS.md generated from real sub-plan checkboxes, not hand-written
independently of them. See scripts/generate_progress.py's own module docstring for why the
"tree" being rolled up here is ARCHITEQ's own .agent/plans/*.md files, not a generated
end-user domain's Workflow/Component Tree."""

from pathlib import Path

from scripts import generate_progress
from scripts.generate_progress import (
    apply_to_progress_md,
    compute_module_statuses,
    parse_leaf_status,
)


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_parse_leaf_status_all_combinations(tmp_path):
    all_done = _write(tmp_path, "all_done.md", "## Status\n\n- [x] Built\n- [x] Tested\n- [x] Committed\n")
    assert parse_leaf_status(all_done) == "[x]"

    none_done = _write(tmp_path, "none_done.md", "## Status\n\n- [ ] Built\n- [ ] Tested\n- [ ] Committed\n")
    assert parse_leaf_status(none_done) == "[ ]"

    mixed = _write(tmp_path, "mixed.md", "## Status\n\n- [x] Built\n- [x] Tested\n- [ ] Committed\n")
    assert parse_leaf_status(mixed) == "[-]"

    index_file = _write(tmp_path, "index.md", "# Plan 10: Index\n\n## Sub-plans\n\n1. **10a...**\n")
    assert parse_leaf_status(index_file) is None


def test_compute_module_statuses_against_real_repo_plans():
    # A real, verifiable assertion against this repo's own actual current state, not a
    # fixture -- Module 12 now has both leaves (12a, 12b) fully done and its own top-level
    # index plan file (12.planning-artifact-diagram-engine.md), so it correctly computes to
    # "[x]": sub-plan 12b resolved OQ6, giving all six DP11 artifacts a real generator.
    statuses = compute_module_statuses()
    assert statuses["Module 12:"] == "[x]"
    # Module 10 is genuinely back in progress: plan 10k (n8n canvas remaining spec items)
    # added real new leaves (10k-i.connection-arrowheads-and-flow-animation.md, currently
    # Built+Tested but not yet Committed) on top of the already-fully-done 10a-10j leaves --
    # "[-]" here is the honest, correct rollup, not a regression; will return to "[x]" once
    # 10k's own sub-plans are all committed, the same way this line was updated for Module
    # 12 once 12b actually landed.
    assert statuses["Module 10:"] == "[-]"
    assert statuses["Module 11:"] == "[x]"
    assert statuses["Module 13:"] == "[x]"


def test_compute_module_statuses_caps_at_in_progress_without_an_index_file(tmp_path, monkeypatch):
    monkeypatch.setattr(generate_progress, "PLANS_DIR", tmp_path)
    monkeypatch.setitem(generate_progress.MODULE_PREFIX_TO_HEADING, "99", "Module 99:")
    _write(tmp_path, "99a.only-leaf.md", "## Status\n\n- [x] Built\n- [x] Tested\n- [x] Committed\n")
    statuses = compute_module_statuses()
    assert statuses["Module 99:"] == "[-]"


def test_apply_to_progress_md_only_changes_targeted_lines(tmp_path):
    fixture = _write(tmp_path, "PROGRESS.md", (
        "# Progress\n\n"
        "### Module 10: UI Shell\n"
        "`[ ]` — R16 to R19. Some real prose that must survive untouched.\n\n"
        "### Module 99: Untracked Module\n"
        "`[ ]` — Not started, no plan files exist for this one.\n"
    ))
    result = apply_to_progress_md({"Module 10:": "[x]"}, fixture)
    lines = result.splitlines()
    assert lines[3] == "`[x]` — R16 to R19. Some real prose that must survive untouched."
    assert lines[6] == "`[ ]` — Not started, no plan files exist for this one."
