#!/usr/bin/env python3
"""Save one before/after pair: Claude's draft vs what the user actually sent.

Usage: python3 -I save_edit.py <post|email|message> <before_file> <after_file>
       (use - for after_file to read the final text from the clipboard via pbpaste)

Skips the pair when nothing changed or when the identical pair is already stored. Appends to ~/.claude-voice/edits.jsonl.
"""
import os, json, subprocess, sys, time, difflib
from pathlib import Path

if len(sys.argv) != 4 or sys.argv[1] not in ("post", "email", "message"):
    sys.exit(__doc__)
fmt, before_f, after_f = sys.argv[1:]
before = Path(before_f).read_text(errors="ignore").strip()
after = (subprocess.run(["pbpaste"], capture_output=True, text=True).stdout if after_f == "-" else Path(after_f).read_text(errors="ignore")).strip()

ratio = difflib.SequenceMatcher(None, before, after).ratio()
if not after or ratio > 0.995:
    print("No real change between draft and final, nothing saved.")
    sys.exit(0)

ROOT = Path(os.environ.get("CLAUDE_VOICE_DIR") or Path.home() / ".claude-voice")
out = ROOT / "edits.jsonl"
out.parent.mkdir(parents=True, exist_ok=True)
if out.exists():
    for l in out.open(errors="ignore"):
        try:
            d = json.loads(l)
        except ValueError:
            continue
        if isinstance(d, dict) and str(d.get("before", "")).strip() == before and str(d.get("after", "")).strip() == after:
            print("Already saved.")
            sys.exit(0)
with out.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "format": fmt,
                         "before": before, "after": after}, ensure_ascii=False) + "\n")
n = sum(1 for _ in out.open(errors="ignore"))
print(f"Saved edit ({fmt}, {round((1 - ratio) * 100)}% changed). {n} edits stored.")
