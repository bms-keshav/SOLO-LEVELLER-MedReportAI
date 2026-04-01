import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.rule_engine import RuleEngine


def test_hemoglobin_normal_low_high():
    engine = RuleEngine()

    status, _ = engine.validate_value("Hemoglobin", "14.0")
    assert status == "normal"

    status, _ = engine.validate_value("Hemoglobin", "10.0")
    assert status == "low"

    status, _ = engine.validate_value("Hemoglobin", "18.0")
    assert status == "high"


def test_alias_resolution_hb_and_parentheses():
    engine = RuleEngine()

    status, _ = engine.validate_value("Hb", "13.2")
    assert status == "normal"

    status, _ = engine.validate_value("Hemoglobin (Hb)", "11.5")
    assert status == "low"


def test_unknown_parameter_returns_unknown():
    engine = RuleEngine()
    status, ref = engine.validate_value("Imaginary Marker", "123")

    assert status == "unknown"
    assert ref is None
