#!/usr/bin/env bash
# Installs claude-voice into ~/.claude: skill, two hooks, output style, optional commands.
# Anything it would overwrite is copied to ~/.claude/.claude-voice-backup-<time>/ first.
# settings.json is backed up too and validated before it is touched. Re-running is safe.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
C="$HOME/.claude"
D="${CLAUDE_VOICE_DIR:-$HOME/.claude-voice}"
stamp="$(date +%Y%m%d-%H%M%S)"
B="$C/.claude-voice-backup-$stamp"
S="$C/settings.json"

read -r -d '' SETTINGS_PY <<'EOF' || true
import json, os, shutil, sys, tempfile
mode, p, stamp = sys.argv[1], sys.argv[2], sys.argv[3]
def die(msg):
    print(f"claude-voice: {msg}\nNothing was changed in settings.json. Fix it and run install.sh again.", file=sys.stderr)
    sys.exit(1)
d = {}
if os.path.exists(p):
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
    except (ValueError, OSError) as e:
        die(f"{p} is not valid JSON ({e}).")
if not isinstance(d, dict):
    die(f"{p} must hold a JSON object.")
hooks = d.get("hooks", {})
if not isinstance(hooks, dict):
    die('"hooks" in settings.json is not an object.')
for event in ("UserPromptSubmit", "Stop"):
    if not isinstance(hooks.get(event, []), list):
        die(f'hooks.{event} in settings.json is not a list.')
if mode == "check":
    sys.exit(0)

def add(event, script):
    cmd = f'python3 "$HOME/.claude/hooks/{script}"'
    groups = hooks.setdefault(event, [])
    found = any(isinstance(g, dict) and isinstance(g.get("hooks"), list)
                and any(isinstance(h, dict) and h.get("command") == cmd for h in g["hooks"]) for g in groups)
    if not found:
        groups.append({"hooks": [{"type": "command", "command": cmd, "timeout": 5}]})

if os.path.exists(p):
    orig = p + ".orig-claude-voice"
    if not os.path.exists(orig):  # the first-ever copy is kept for good
        shutil.copy2(p, orig)
    shutil.copy2(p, f"{p}.bak-claude-voice-{stamp}")
    print(f"Backed up settings.json to {p}.bak-claude-voice-{stamp} (first-ever copy: {orig})")
d["hooks"] = hooks
add("UserPromptSubmit", "voice-router.py")
add("Stop", "pushback-check.py")
d.setdefault("outputStyle", "Plain")
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p) or ".", prefix=".settings-", suffix=".tmp")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    if os.path.exists(p):
        shutil.copymode(p, tmp)
    os.replace(tmp, p)
except BaseException:
    if os.path.exists(tmp):
        os.unlink(tmp)
    raise
EOF

# Validate settings.json first: if it is broken we stop before touching anything.
python3 -I -c "$SETTINGS_PY" check "$S" "$stamp"

backed=0
backup() {  # copy an existing file/dir into the backup folder, unless the new one is identical
  local target="$1" src="$2" rel
  [ -e "$target" ] || return 0
  diff -rq "$target" "$src" >/dev/null 2>&1 && return 0
  rel="${target#"$C"/}"
  mkdir -p "$B/$(dirname "$rel")"
  cp -R "$target" "$B/$rel"
  backed=1
  echo "Backed up existing $rel to $B/$rel"
}

mkdir -p "$C/skills" "$C/hooks" "$C/output-styles" "$C/commands" "$D"/{samples/email,samples/post,samples/message,drafts}
chmod 700 "$D"

backup "$C/skills/my-voice" "$here/skills/my-voice"
rm -rf "$C/skills/my-voice"          # replace cleanly so no stale files stay behind
cp -R "$here/skills/my-voice" "$C/skills/"
for f in voice-router.py pushback-check.py; do
  backup "$C/hooks/$f" "$here/hooks/$f"
  cp "$here/hooks/$f" "$C/hooks/"
done
backup "$C/output-styles/plain.md" "$here/output-styles/plain.md"
cp "$here/output-styles/plain.md" "$C/output-styles/"
for f in "$here/commands/"*.md; do
  backup "$C/commands/$(basename "$f")" "$f"
  cp "$f" "$C/commands/"
done

[ -f "$S" ] || echo '{}' > "$S"
python3 -I -c "$SETTINGS_PY" write "$S" "$stamp"

python3 -I "$C/skills/my-voice/scripts/extract_voice.py" || true
echo
echo "Installed. Start a new Claude Code session to load the hooks and the Plain style."
echo "Your data lives in $D (never in this repo)."
if [ "$backed" -eq 1 ]; then echo "Files that were replaced are saved in $B"; fi
echo "Optional: drop a few emails/posts you wrote yourself (no AI) into samples/email and samples/post there."
