"""The README's Result block has to match what the script actually prints.

Runs the real entry script (risk_tracker.py) end to end against the sample data
in data/, with charts and report files redirected to a temp directory so
assets/ is left alone. Every line of the fenced block under "## Result" in
README.md must then appear, in order and unbroken, in the captured output.
Change the code so the numbers move, and this fails until the README is
updated to match.
"""

from __future__ import annotations

import re
from pathlib import Path

import risk_tracker as tool

ROOT = Path(__file__).resolve().parents[1]


def _readme_result_block() -> list[str]:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "\n## Result" in text, "README.md has no '## Result' section"
    section = text.split("\n## Result", 1)[1].split("\n## ", 1)[0]
    match = re.search(r"```[^\n]*\n(.*?)```", section, re.S)
    assert match, "No fenced code block under '## Result' in README.md"
    return [line.rstrip() for line in match.group(1).rstrip("\n").splitlines()]


def _run_script(monkeypatch, tmp_path, capsys) -> list[str]:
    monkeypatch.setattr(tool, "ASSETS_DIR", str(tmp_path))
    tool.main()
    return [line.rstrip() for line in capsys.readouterr().out.splitlines()]


def test_readme_result_block_matches_script_output(monkeypatch, tmp_path, capsys):
    expected = _readme_result_block()
    output = _run_script(monkeypatch, tmp_path, capsys)
    n = len(expected)
    found = any(output[i:i + n] == expected for i in range(len(output) - n + 1))
    assert found, (
        "README.md's Result block no longer matches the script's output.\n"
        "Actual output:\n" + "\n".join(output)
    )


def test_committed_report_md_matches_regenerated(monkeypatch, tmp_path, capsys):
    """assets/report.md is linked from the README as the saved copy of the
    report, so it has to be what the current code actually produces."""
    _run_script(monkeypatch, tmp_path, capsys)
    regenerated = (tmp_path / "report.md").read_text(encoding="utf-8")
    committed = (ROOT / "assets" / "report.md").read_text(encoding="utf-8")
    assert regenerated == committed, (
        "assets/report.md is out of date: re-run the script and commit the "
        "regenerated file."
    )
