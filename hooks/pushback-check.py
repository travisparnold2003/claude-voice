#!/usr/bin/env python3
"""Stop hook: pushback check.

When Claude's reply opens by agreeing with the user ("You're right", "Great idea",
"Exactly"...), make Claude add a short honest counter-case before it stops.
Runs once per turn (stop_hook_active), costs nothing when it doesn't fire,
and never calls another model: Claude itself writes 2-3 extra lines.

Note: a Stop hook fires after the reply is on screen, so the check shows up
as a short follow-up under the reply, not as a hidden rewrite.

Off switch: `touch ~/.claude-voice/pushback-off` (delete the file to turn on),
or PUSHBACK_CHECK=0 in the environment.
Log of every firing: ~/.claude-voice/pushback.log
"""
import json, os, re, sys, time
from pathlib import Path

HOME = Path.home()
STATE = Path(os.environ.get("CLAUDE_VOICE_DIR") or HOME / ".claude-voice")
OFF_FILE = STATE / "pushback-off"
LOG = STATE / "pushback.log"

AGREE = re.compile(
    r"\b(you['\u2019]?re (absolutely |totally |completely |so )?right|you are (absolutely )?right|"
    r"(great|good|excellent|brilliant|smart|nice) (idea|question|call|thinking|plan)|"
    r"spot on|exactly( right)?[.!,]|totally agree|i (fully |completely )?agree|"
    r"love (this|that|it)\b|you nailed it|good instinct)",
    re.I,
)
# Only check when the user gave an opinion or plan; not when they reported a bug (agreeing with evidence is fine)
OPINION = re.compile(
    r"(\bi think\b|\bi feel\b|should (i|we)\b|\bthoughts\b|\bwdyt\b|what do (u|you) think|"
    r"\bmy idea\b|\bi want to\b|\bi wanna\b|is (this|that|it) (good|a good|smart|right)|do (u|you) agree|"
    r"\bworth it\b|right\?|^\s*(no|nah|wrong)\b|\b(ur|you['\u2019]?re|thats|that['\u2019]?s) wrong\b)",
    re.I,
)
# "let's" is an opinion only at the very start, and only when it reads like a proposal ("let's commit this" is an instruction)
LETS = re.compile(r"^\s*let['\u2019]?s\b", re.I)
TAIL_BYTES = 1_500_000
LOG_KEEP = 500
EVIDENCE = re.compile(r"(line \d+|traceback|error|exception|fails?\b|failing|crash|stack trace|\bbug\b|doesn'?t work|broken)", re.I)


def tail_lines(path):
    """Lines from the last ~1.5 MB of the transcript (never the whole file); the first partial line is dropped."""
    try:
        with open(path, "rb") as fh:
            fh.seek(0, 2)
            start = max(0, fh.tell() - TAIL_BYTES)
            fh.seek(start)
            data = fh.read()
    except (OSError, TypeError, ValueError):
        return []
    lines = data.decode("utf-8", "ignore").splitlines()
    return lines[1:] if start > 0 else lines


def last_texts(transcript_path):
    """Return (last real user text, last assistant text) from the transcript."""
    user, assistant = "", ""
    for line in reversed(tail_lines(transcript_path)):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if not isinstance(d, dict):
            continue
        msg = d.get("message")
        c = msg.get("content") if isinstance(msg, dict) else None
        if isinstance(c, str):
            texts = [c]
        elif isinstance(c, list):
            texts = [x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text"]
        else:
            texts = []
        text = "\n".join(t for t in texts if isinstance(t, str) and t).strip()
        if not text:
            continue
        if d.get("type") == "assistant" and not assistant:
            assistant = text
        elif d.get("type") == "user" and not d.get("isMeta") and not text.startswith("<"):
            user = text
            break
    return user, assistant


def run():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(data, dict):
        return 0
    if data.get("stop_hook_active") or os.environ.get("PUSHBACK_CHECK") == "0" or OFF_FILE.exists():
        return 0

    user, assistant = last_texts(data.get("transcript_path", ""))
    reply = data.get("last_assistant_message") or assistant
    if not isinstance(reply, str):
        reply = assistant
    opening = reply.strip()[:120]  # first sentence or so: agreement up front is the tell
    m = AGREE.search(opening)
    lets = LETS.search(user) and ("?" in user or len(user.split()) >= 8)
    if not m or not (OPINION.search(user) or lets) or EVIDENCE.search(user):
        return 0

    try:
        STATE.mkdir(parents=True, exist_ok=True)
        entry = json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "hit": m.group(0),
                            "user": user[:200], "reply": opening[:200]}, ensure_ascii=False)
        old = LOG.read_text(errors="ignore").splitlines()[-(LOG_KEEP - 1):] if LOG.exists() else []
        LOG.write_text("\n".join(old + [entry]) + "\n", encoding="utf-8")
    except OSError:
        pass

    reason = (
        f"Pushback check: your reply opened by agreeing with the user (\"{m.group(0)}\"). "
        "Before you stop, add a short section that starts with 'Pushback check:'. In 2-3 short lines, "
        "give the strongest honest case against what you agreed with, then say plainly whether you still agree. "
        "If you changed your mind, say what changes. Don't repeat or summarise your earlier reply. "
        "If your earlier reply ended with a closing line such as the green done line, end with it again only if it still applies."
    )
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


def main():
    try:
        return run()
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
