import json
from pathlib import Path

import pytest

from wa_os_principles import ProtocolFormatError, generate_system_prompt, load_protocol

ROOT = Path(__file__).resolve().parent.parent
PROTOCOL = ROOT / "wa-os.protocol.v1.6-draft.json"


def test_load_current_protocol():
    p = load_protocol(PROTOCOL)
    assert p["version"] == "1.6.0-draft"
    assert len(p["five_mirrors"]["mirrors"]) == 5


def test_system_prompt_uses_actual_mirror_questions():
    p = load_protocol(PROTOCOL)
    output = generate_system_prompt(PROTOCOL)
    for mirror in p["five_mirrors"]["mirrors"]:
        assert mirror["question"] in output
    for principle in p["principles"]:
        assert principle["principle_en"] in output
    assert "Final judgment and interpretation remain with humans." in output


def test_bad_protocol_version_rejected(tmp_path):
    p = load_protocol(PROTOCOL)
    p["version"] = "1.5.0-draft"
    fake = tmp_path / "protocol.json"
    fake.write_text(json.dumps(p), encoding="utf-8")
    with pytest.raises(ProtocolFormatError):
        load_protocol(fake)


def test_no_decision_engine_in_adapter():
    source = (ROOT / "wa_os_principles.py").read_text(encoding="utf-8")
    assert "class DecisionAction" not in source
    assert "risk_score" not in source
    assert "def score" not in source
