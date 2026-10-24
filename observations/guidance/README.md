# WA-OS Guidance Versions

This folder preserves the exact guidance texts supplied to AI systems in WA-OS observations.

`wa_os_principles.py` labels every generated text "WA-OS v1.6-draft", even when the response principles change. Each observation should therefore record the guidance file name and its SHA-256, not only the protocol version.

| File | SHA-256 | Source | Used in |
|---|---|---|---|
| `guidance-2026-10-23-six-principles-as-used-in-SYC-001.txt` | `533ea747ffe1d56c624b4a7f0a820fae6dda7cdfd0306445d7a57cc149b36384` | Six response principles and the Five Mirrors (protocol at commit `1fcc2ab`) | SYC-001, Condition B (2026-10-23) |
| `guidance-2026-10-24-eight-principles.txt` | `80bd9e419241d000aa1ab9cdad107cd2b7b7e1030c11c127d25033e13b0404ab` | Eight response principles (Proportionality and Reversibility added) and the Five Mirrors | Not yet used |

## Notes

- The SYC-001 file is the text actually supplied to the AI systems, copied from the `guidance_condition_B` field of the [SYC-001 observation record](../2026-10-23/SYC-001-2026-10-23-responses.json).
- That text differs from the direct output of `wa_os_principles.py` by one character: the apostrophe in "human's place" in the 智 mirror is a straight apostrophe (') instead of the typographic apostrophe (’). The difference arose while the text was transcribed for the observation. The wording is otherwise identical.
- The eight-principle text is the direct output of `wa_os_principles.py` after the two principles were added. It differs from the six-principle text only by the two added lines and the apostrophe noted above.
- Guidance files are research assets. Do not edit them. A revised guidance text must be saved as a new file.
