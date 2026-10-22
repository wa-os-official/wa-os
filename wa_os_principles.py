"""Optional WA-OS v1.6 response-principles prompt adapter.

This is NOT an enforcement mechanism, model modification, or observatory.
It produces reference guidance for integrations that elect to send a system prompt.
No scoring, routing, pass/fail or response rewriting occurs here.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_PROTOCOL = Path(__file__).resolve().with_name("wa-os.protocol.v1.6-draft.json")


class ProtocolFormatError(ValueError):
    pass


def load_protocol(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path is not None else DEFAULT_PROTOCOL
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("protocol") != "WA-OS":
        raise ProtocolFormatError("Expected a WA-OS JSON protocol")
    if data.get("version") != "1.6.0-draft":
        raise ProtocolFormatError("This adapter requires protocol 1.6.0-draft")
    mirrors = data.get("five_mirrors", {}).get("mirrors")
    if not isinstance(mirrors, list) or len(mirrors) != 5:
        raise ProtocolFormatError("Exactly five mirror questions are required")
    ids = [m.get("id") for m in mirrors if isinstance(m, dict)]
    if ids != ["ren", "yi", "li", "zhi", "xin"]:
        raise ProtocolFormatError("Mirror IDs or their order are unexpected")
    for m in mirrors:
        if not all(isinstance(m.get(k), str) and m[k].strip() for k in ("character", "title", "question")):
            raise ProtocolFormatError("Each mirror must have character, title, question")
    principles = data.get("principles")
    if not isinstance(principles, list) or not principles:
        raise ProtocolFormatError("Response principles are missing")
    for p in principles:
        if not isinstance(p, dict) or not isinstance(p.get("principle_en"), str):
            raise ProtocolFormatError("Invalid response principle")
    return data


def generate_system_prompt(path: str | Path | None = None) -> str:
    """Return non-binding guidance extracted from the actual v1.6 protocol.

    Consumers must deliberately supply this text to their AI API; calling this
    function does not change any existing model's behavior by itself.
    """
    protocol = load_protocol(path)
    lines = [
        "WA-OS v1.6-draft — voluntary reference guidance for AI responses",
        "Protect human inquiry and agency. Do not claim authority over human value judgments.",
        "Prioritize truth and foundational principles over completing a local task.",
        "Respond usefully and directly; disclose significant uncertainty.",
        "Do not treat these questions as scores, labels, pass/fail criteria, or automated verdicts.",
        "Response principles:",
    ]
    lines.extend(f"- {p['principle_en']}" for p in protocol["principles"])
    lines.append("Five Mirrors — reflective questions, not assessment axes:")
    for m in protocol["five_mirrors"]["mirrors"]:
        lines.append(f"- {m['character']} ({m['title']}): {m['question']}")
    lines.append("Final judgment and interpretation remain with humans.")
    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_system_prompt())
