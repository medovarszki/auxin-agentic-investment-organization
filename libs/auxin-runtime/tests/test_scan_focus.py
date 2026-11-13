"""Risk-bucket focus of the scan (scan_trigger payload `risk_bucket`)."""
from pathlib import Path

import pytest
import yaml

from auxin_a2a.server import Rejected
from auxin_runtime.handlers import _bucket_definitions, bucket_focus_note, scan_bucket

ROOT = Path(__file__).resolve().parents[3]
RULES = yaml.safe_load((ROOT / "org/rules/portfolio-rules.yaml").read_text())
SKILL = ROOT / "agents/portfolio-manager/skills/risk-bucket/SKILL.md"


def test_bucket_is_optional_and_validated():
    assert scan_bucket({}, RULES) is None
    assert scan_bucket({"risk_bucket": 3}, RULES) == 3
    for bad in (0, 5, "3", True, 2.0):
        with pytest.raises(Rejected):
            scan_bucket({"risk_bucket": bad}, RULES)


def test_definitions_are_the_pm_skill_bucket_section(monkeypatch):
    monkeypatch.setenv("AUXIN_RISK_BUCKETS_FILE", str(SKILL))
    text = _bucket_definitions(Path("/nonexistent"))
    assert text.startswith("| Bucket | Name |") and "ETFs: broad, diversified index -> 1" in text
    assert "## Fit" not in text and "## Evidence" not in text


def test_focus_note_names_the_bucket_and_carries_the_definitions():
    assert bucket_focus_note(None, RULES, "defs") == ""
    note = bucket_focus_note(4, RULES, "DEFS")
    assert "## Risk-bucket focus: bucket 4 (spekulatív)" in note and note.rstrip().endswith("DEFS")
