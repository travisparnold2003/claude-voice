#!/usr/bin/env python3
"""UserPromptSubmit hook: makes the my-voice loop automatic.

1. Learns from rewrites: if the user's message looks like their rewrite of a recent
   Claude draft (saved drafts or quoted/fenced blocks in the last few replies),
   the pair is saved to the shared voice folder and Claude is told.
2. Writing requests (email, post, message...) -> tells Claude to use my-voice.
3. Their own text pasted for checking -> grammar-only mode.
4. Refreshes the corpus of their typed messages once a day, in the background.

Never blocks the prompt. Off switch: touch $CLAUDE_VOICE_DIR (default ~/.claude-voice)/voice-off
"""
import difflib, json, os, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_VOICE_DIR") or Path.home() / ".claude-voice")
SKILL = Path.home() / ".claude" / "skills" / "my-voice" / "scripts"

WRITE_REQ = re.compile(
    r"\b(draft|write|reply|respond|answer)\b.{0,60}\b(email|mail|message|msg|post|linkedin|substack|dm|whatsapp|"
    r"letter|caption|bio|cover letter)\b|"
    r"\breply to \w+|\b(linkedin|substack) post\b|\bcover letter\b|\bemail (to|for|back)\b|\bmessage (to|for)\b",
    re.I | re.S,
)
CODE_WORDS = re.compile(r"\b(script|function|readme|code|api|test|bug|repo|file|endpoint|commit)\b", re.I)
CHECK_REQ = re.compile(
    r"\b(check (this|my)|proofread|proof read|grammar check|spell check|spellcheck|"
    r"fix my (text|grammar|spelling|writing)|any typos)\b",
    re.I,
)
CHECK_CODE_WORDS = re.compile(r"\b(code|function|script|bug|error|test|api|file|repo|deploy|build)\b", re.I)
SENT = re.compile(
    r"\b(i('?ve| have)? ?(just )?(sent|submitted|posted|published|scheduled|replied|emailed|messaged)|"
    r"(sent|submitted|posted|published|scheduled) (it|that|the \w+)|(it'?s|its) (sent|submitted|posted|live|published)|"
    r"pressed (send|post|submit|schedule)|done,? sent)\b|^\s*(sent|submitted|posted|published|scheduled)\b",
    re.I,
)
CODEY = re.compile(r"[{};=<>]|def |function |import |\$ |```")
SENT_TOPIC = re.compile(r"\b(email|mail|post|linkedin|substack|message|whatsapp|form|application)\b", re.I)
INSTRUCTION = re.compile(r"here'?s|heres|my version|rewrote|rewritten|changed it|how about", re.I)
TAIL_BYTES = 1_500_000
MAX_CMP_WORDS = 600


def words(t):
    return re.findall(r"[\w']+", t.lower())


def tail_lines(path):
    """Lines from the last ~1.5 MB of a file (never the whole transcript); the first partial line is dropped."""
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


def candidates(transcript_path):
    """Recent Claude drafts: saved draft files + quoted/fenced prose in the last replies."""
    out = []
    d = ROOT / "drafts"
    if d.exists():
        for p in d.glob("*.md"):
            try:
                if time.time() - p.stat().st_mtime < 7 * 86400 and not p.stem.endswith("-final"):
                    out.append((p.read_text(errors="ignore"), p.name))
            except OSError:
                continue
    seen = 0
    for line in reversed(tail_lines(transcript_path)[-400:]):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if not isinstance(e, dict) or e.get("type") != "assistant":
            continue
        msg = e.get("message")
        content = msg.get("content") if isinstance(msg, dict) else None
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        if not isinstance(content, list):
            continue
        for c in content:
            if not isinstance(c, dict) or c.get("type") != "text":
                continue
            t = c.get("text", "")
            if not isinstance(t, str):
                continue
            blocks = re.findall(r"```(?:\w+)?\n(.*?)```", t, re.S)
            quote = "\n".join(l[1:].lstrip() for l in t.splitlines() if l.startswith(">"))
            if quote:
                blocks.append(quote)
            for b in blocks:
                if len(words(b)) >= 25 and not CODEY.search(b):
                    out.append((b, "chat"))
        seen += 1
        if seen >= 4:
            break
    return out


def strip_instruction(text):
    """Drop a short leading instruction line ("here's my version:") so only the rewrite is kept."""
    text = text.strip()
    parts = re.split(r"\n\s*\n", text, maxsplit=1)
    if len(parts) < 2:
        parts = text.split("\n", 1)
    if len(parts) == 2 and parts[1].strip():
        first = parts[0].strip()
        if len(words(first)) < 15 and (first.endswith(":") or INSTRUCTION.search(first)):
            return parts[1].strip()
    return text


def load_pairs():
    out = set()
    f = ROOT / "edits.jsonl"
    try:
        for l in f.open(errors="ignore"):
            try:
                d = json.loads(l)
            except ValueError:
                continue
            if isinstance(d, dict):
                out.add((str(d.get("before", "")).strip(), str(d.get("after", "")).strip()))
    except OSError:
        pass
    return out


def guess_format(text):
    first = text.strip().splitlines()[0] if text.strip() else ""
    if re.match(r"(hi|hey|hello|dear)\b", first, re.I) and re.search(r"\n(best|cheers|thanks|regards|kind regards)\b", text, re.I):
        return "email"
    return "post" if len(words(text)) > 80 else "message"


def save_pair(before, after, fmt):
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / "edits.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "format": fmt, "source": "auto",
                             "before": before.strip(), "after": after.strip()}, ensure_ascii=False) + "\n")


def refresh_corpus():
    c = ROOT / f"corpus-{os.environ.get('USER', 'me')}.jsonl"
    script = SKILL / "extract_voice.py"
    if script.exists() and (not c.exists() or time.time() - c.stat().st_mtime > 86400):
        try:
            c.touch()  # claim the slot so parallel prompts don't all start a scan
            subprocess.Popen([sys.executable, "-I", str(script)], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError:
            pass


def run():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(data, dict) or (ROOT / "voice-off").exists():
        return 0
    prompt = data.get("prompt")
    if not isinstance(prompt, str):
        prompt = ""
    refresh_corpus()
    notes = []

    # 1. Their rewrite of a recent draft?
    after = strip_instruction(prompt)
    pw = words(after)
    if len(pw) >= 15:
        best, best_src, best_r = None, "", 0.0
        for text, src in candidates(data.get("transcript_path", "")):
            cw = words(text)
            if not cw or not (0.4 <= len(pw) / len(cw) <= 2.5):
                continue
            r = difflib.SequenceMatcher(None, cw[:MAX_CMP_WORDS], pw[:MAX_CMP_WORDS], autojunk=False).ratio()
            if r > best_r:
                best, best_src, best_r = text, src, r
        if best and 0.3 <= best_r < 0.97:
            fmt = guess_format(after)
            if (best.strip(), after.strip()) in load_pairs():
                notes.append("")  # already saved: stay quiet, and skip the other hints for this prompt
            else:
                save_pair(best, after, fmt)
                notes.append(
                    f"The user's message looks like their own rewrite of your earlier draft ({round(best_r * 100)}% similar, from {best_src}). "
                    f"It was saved automatically as a {fmt} voice example in the shared voice folder. "
                    "Treat their version as the final text: don't rewrite it back towards your draft. If they asked for changes, keep their wording and only fix what they asked."
                )

    # 1b. They say they sent/posted something Claude drafted -> go find the final and learn from it
    if not notes and SENT.search(prompt) and len(words(prompt)) <= 60:
        dd = ROOT / "drafts"
        recent = []
        try:
            recent = [p.name for p in dd.glob("*.md") if time.time() - p.stat().st_mtime < 7 * 86400] if dd.exists() else []
        except OSError:
            pass
        if recent or SENT_TOPIC.search(prompt):
            notes.append(
                "The user says they sent/submitted/posted something. If you (or an earlier session) drafted it, go and find the version they "
                "actually sent before you reply: their Sent mail (a mail connector, or the browser), "
                "the live post (in a new browser tab), or wherever they submitted it. Compare it with the draft"
                + (f" (recent drafts in {ROOT}/drafts: {', '.join(sorted(recent)[-5:])})" if recent else f" (check {ROOT}/drafts and this chat)")
                + ". If it changed, save the pair: python3 -I ~/.claude/skills/my-voice/scripts/save_edit.py <post|email|message> <draft file> <file with the sent text>, "
                "and tell them in one line what they changed. If you can't reach the sent version, say so in one line. If nothing was drafted by Claude, ignore this."
            )

    # 2. Writing that goes out under their name
    if not notes and WRITE_REQ.search(prompt) and not CODE_WORDS.search(prompt) and not CODEY.search(prompt[:300]):
        notes.append(
            "This looks like writing that goes out under the user's name. Follow the my-voice skill: get their own take first if the piece "
            "needs their opinion or story, run pick_samples.py for the format, draft like the next sample, and save the draft to "
            f"{ROOT}/drafts/ so their rewrite gets learned automatically. For pieces over about 250 words, agree a short outline first."
        )

    # 3. Their own text, pasted for a check
    if (not notes and CHECK_REQ.search(prompt[:200]) and len(words(prompt)) >= 40
            and not CHECK_CODE_WORDS.search(prompt) and not CODEY.search(prompt)):
        notes.append(
            "The user pasted text they wrote themselves for a check. Fix only spelling, grammar and clear typos. Keep their words, order, slang and tone. "
            "Return the corrected text as one copyable block, then each change as `old -> new`."
        )

    notes = [n for n in notes if n]
    if notes:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "\n".join(notes)}}))
    return 0


def main():
    try:
        return run()
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
