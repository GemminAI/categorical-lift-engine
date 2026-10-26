"""The FAIL reason codes in the docs are the ones in the code (v0.4)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_fail_code_list_matches_the_code() -> None:
    code = (ROOT / "src/cle/representation/checks.py").read_text(encoding="utf-8")
    in_code = set(re.findall(r'"FAIL",\s*"([A-Z_]+)"', code))
    doc = (ROOT / "docs/representation_fail_codes.md").read_text(encoding="utf-8")
    in_doc = set(re.findall(r"^\| `([A-Z_]+)` \|", doc, flags=re.M))
    assert in_code == in_doc


def test_every_v04_decision_is_recorded_in_the_ambiguity_list() -> None:
    doc = (ROOT / "docs/representation_ambiguities.md").read_text(encoding="utf-8")
    for n in range(1, 26):
        assert f"D-{n:02d}" in doc, n
