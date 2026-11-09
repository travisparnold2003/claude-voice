#!/usr/bin/env python3
"""Pull the messages the user typed themselves out of Claude Code transcripts.

Keeps only human-typed text: no tool results, no subagent (sidechain) prompts,
no hook/system text, no pasted blocks, no slash-command wrappers.
Writes JSONL to $CLAUDE_VOICE_DIR (default ~/.claude-voice)/corpus-<account>.jsonl (optional, outside every git repo).

Set CLAUDE_VOICE_SKIP to a regex to skip project folders whose name matches it (for example
sessions driven by scripts or demos). Default: skip nothing.

Usage: python3 -I extract_voice.py [projects_dir] [out_file]
"""
import json, os, re, sys, hashlib
from pathlib import Path

projects = Path(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.claude/projects"))
ROOT = Path(os.environ.get("CLAUDE_VOICE_DIR") or Path.home() / ".claude-voice")
out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / f"corpus-{os.environ.get('USER', 'me')}.jsonl"
out.parent.mkdir(parents=True, exist_ok=True)

STRIP = re.compile(r"<(system-reminder|pasted_content[^>]*)>.*?</\1[^>]*>", re.S)
SKIP_START = ("<", "[Image", "Caveat:", "[Request interrupted", "This session is being continued",
              "Base directory for this skill", "[SYSTEM NOTIFICATION")
try:
    SKIP_PROJECT = re.compile(os.environ["CLAUDE_VOICE_SKIP"]) if os.environ.get("CLAUDE_VOICE_SKIP") else None
except re.error:
    SKIP_PROJECT = None
seen, rows = set(), []

for f in sorted(projects.rglob("*.jsonl")):
    if "subagents" in f.parts:
        continue
    # sessions driven by scripts (automations, demos) are not typed by the user: skip them via CLAUDE_VOICE_SKIP
    if SKIP_PROJECT and SKIP_PROJECT.search(f.parent.name):
        continue
    try:
        fh = f.open(errors="ignore")
    except OSError:
        continue
    with fh:
        try:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(d, dict):
                    continue
                if d.get("type") != "user" or d.get("isSidechain") or d.get("isMeta") or d.get("isCompactSummary"):
                    continue
                msg = d.get("message")
                c = msg.get("content") if isinstance(msg, dict) else None
                if isinstance(c, str):
                    parts = [c]
                elif isinstance(c, list):
                    parts = [x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text"]
                else:
                    parts = []
                for t in parts:
                    if not isinstance(t, str):
                        continue
                    t = STRIP.sub("", t).strip()
                    if len(t) < 12 or len(t) > 2000 or t.startswith(SKIP_START):
                        continue
                    h = hashlib.sha1(t.lower().encode("utf-8", "ignore")).hexdigest()
                    if h in seen:
                        continue
                    seen.add(h)
                    rows.append({"ts": str(d.get("timestamp", "")), "project": f.parent.name, "text": t})
        except OSError:
            continue

rows.sort(key=lambda r: r["ts"])
with out.open("w", encoding="utf-8") as fh:
    for r in rows:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
words = sum(len(r["text"].split()) for r in rows)
print(f"{len(rows)} messages, {words} words -> {out}")
