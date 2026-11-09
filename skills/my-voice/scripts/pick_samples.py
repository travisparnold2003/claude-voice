#!/usr/bin/env python3
"""Print real writing samples + the user's own past edits for one format.

Usage: python3 -I pick_samples.py <post|email|message> [--n 5] [--edits 4]

Reads (all private, outside git):
  <root>/corpus-<account>.jsonl      messages they typed to Claude Code (optional)
  <root>/samples/<format>/            longer things they wrote themselves (*.md)
  <root>/edits.jsonl                  before/after pairs saved by save_edit.py
  (root = $CLAUDE_VOICE_DIR, default ~/.claude-voice)
"""
import os, argparse, json, random, time
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_VOICE_DIR") or Path.home() / ".claude-voice")

ap = argparse.ArgumentParser()
ap.add_argument("format", choices=["post", "email", "message"])
ap.add_argument("--n", type=int, default=5)
ap.add_argument("--edits", type=int, default=4)
a = ap.parse_args()
rng = random.Random(int(time.time() // 3600))  # varies by the hour, so drafts don't all copy the same lines

out = []

# 1. Longer pieces they wrote themselves, for this format
long_dir = ROOT / "samples" / a.format
longs = sorted(long_dir.glob("*.md")) if long_dir.exists() else []
rng.shuffle(longs)
for p in longs[: max(2, a.n // 2)]:
    try:
        body = "\n".join(l for l in p.read_text(errors="ignore").splitlines() if not l.startswith("<!--")).strip()
    except OSError:
        continue
    if body:
        out.append(("their own " + a.format, body))

# 2. Chat messages they typed: pick substantial ones spread over time (diversity beats topic match)
rows = []
for corpus in sorted(ROOT.glob("corpus*.jsonl")):
    try:
        for l in corpus.open(errors="ignore"):
            try:
                r = json.loads(l)
            except ValueError:
                continue
            if isinstance(r, dict) and isinstance(r.get("text"), str):
                rows.append(r)
    except OSError:
        continue
if rows:
    rows.sort(key=lambda r: str(r.get("ts", "")))
    rows = [r for r in rows if 20 <= len(r["text"].split()) <= 180 and "/" not in r["text"][:3]]
    k = a.n - len(out) if len(out) < a.n else 2
    k = min(k, len(rows))
    if k > 0:
        # k evenly spaced chunks over the whole list (so the newest chunk can be picked), one random row from each
        picks = [rng.choice(rows[i * len(rows) // k:(i + 1) * len(rows) // k]) for i in range(k)]
        out += [("chat", r["text"]) for r in picks]

own = [t for k, t in out if k != "chat"]
chat = [t for k, t in out if k == "chat"]
if own:
    print(f"REAL {a.format.upper()}S THE USER WROTE THEMSELVES (this is the register to match)\n")
    for i, text in enumerate(own, 1):
        print(f"--- {a.format} {i} ---\n{text}\n")
if chat:
    head = ("HOW THEY TALK (messages they typed to Claude; match this directly)" if a.format == "message" else
            "HOW THEY TALK (chat messages to Claude: use for tone and word choice only, not spelling or register)")
    print(head + "\n")
    for i, text in enumerate(chat, 1):
        print(f"--- chat {i} ---\n{text}\n")

# 3. Their edits: what Claude wrote vs what they changed it to (same format first, newest first)
edits = ROOT / "edits.jsonl"
if edits.exists() and a.edits > 0:
    pairs = []
    try:
        for l in edits.open(errors="ignore"):
            try:
                p = json.loads(l)
            except ValueError:
                continue
            if isinstance(p, dict) and isinstance(p.get("before"), str) and isinstance(p.get("after"), str):
                pairs.append(p)
    except OSError:
        pass
    pairs.sort(key=lambda p: (p.get("format") == a.format, str(p.get("ts", ""))), reverse=True)
    pairs = pairs[: a.edits]
    if pairs:
        print("THEIR EDITS TO EARLIER CLAUDE DRAFTS (the gap between the two is their style)\n")
        for i, p in enumerate(pairs, 1):
            print(f"--- edit {i} ({p.get('format')}) ---\nCLAUDE WROTE:\n{p['before']}\n\nTHE USER CHANGED IT TO:\n{p['after']}\n")
