#!/usr/bin/env bash
# Hook and script checks against a throwaway data folder. Usage: bash tests/run.sh
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
export CLAUDE_VOICE_DIR="$(mktemp -d)"
T="$CLAUDE_VOICE_DIR/t"; mkdir -p "$T"
touch "$CLAUDE_VOICE_DIR/corpus-${USER:-me}.jsonl"  # fresh corpus: the router won't start a background scan
pass=0; fail=0
check() { if [ "$2" = "$3" ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL: $1 (got '$2', want '$3')"; fi; }
fires() { [ -n "$1" ] && echo yes || echo no; }

transcript() {  # $1 user text, $2 assistant text
  python3 -I -c 'import json,sys
print(json.dumps({"type":"user","message":{"content":sys.argv[1]}}))
print(json.dumps({"type":"assistant","message":{"content":[{"type":"text","text":sys.argv[2]}]}}))' "$1" "$2" > "$T/tr.jsonl"
}
pushback() { echo "{\"transcript_path\":\"$T/tr.jsonl\",\"stop_hook_active\":${1:-false}}" | python3 -I "$here/hooks/pushback-check.py"; }
router() { python3 -I -c 'import json,sys;print(json.dumps({"prompt":sys.argv[1],"transcript_path":sys.argv[2]}))' "$1" "$T/tr.jsonl" | python3 -I "$here/hooks/voice-router.py"; }

# pushback check
transcript "i think we should rewrite it in rust, thoughts?" "Great idea! Rust is faster."
check "opinion + agreement fires" "$(fires "$(pushback)")" yes
check "runs only once per turn" "$(fires "$(pushback true)")" no
transcript "the test fails on line 40 with a TypeError" "You're right, that's a bug. Fixed."
check "bug report does not fire" "$(fires "$(pushback)")" no
transcript "deploy it" "Great call, deploying now."
check "plain instruction does not fire" "$(fires "$(pushback)")" no
transcript "i think tabs are better" "Tabs work in Python, but PEP 8, black and nearly every codebase use four spaces, so you would be fighting your tools on every file. Great idea to ask though."
check "agreement late in reply does not fire" "$(fires "$(pushback)")" no
touch "$CLAUDE_VOICE_DIR/pushback-off"; transcript "i think so, agree?" "You're right."
check "off switch" "$(fires "$(pushback)")" no; rm "$CLAUDE_VOICE_DIR/pushback-off"

# voice router
draft=$'Hi Sam,\n\nI hope this message finds you well. I wanted to follow up regarding the proposal we discussed last week. Could you please let me know whether there have been any updates on your side regarding the timeline and next steps?\n\nBest regards,\nAlex'
transcript "write sam a follow up email" $'Here is a draft:\n\n```\n'"$draft"$'\n```'
out="$(router $'Hi Sam,\n\nHope all is well! Any news on the proposal from last week? Would be great to know the timeline and next steps on your side.\n\nBest,\nAlex')"
check "rewrite detected" "$(echo "$out" | grep -c 'own rewrite' || true)" 1
check "rewrite saved" "$(wc -l < "$CLAUDE_VOICE_DIR/edits.jsonl" | tr -d ' ')" 1
check "write request" "$(router 'can u write a linkedin post about my new tool' | grep -c 'my-voice' || true)" 1
check "sent detection" "$(router 'ive sent the email' | grep -c 'actually sent' || true)" 1
check "sent without topic or draft is ignored" "$(fires "$(router 'i just published the npm package')")" no
check "duplicate rewrite saved once" "$(router $'Hi Sam,\n\nHope all is well! Any news on the proposal from last week? Would be great to know the timeline and next steps on your side.\n\nBest,\nAlex' >/dev/null; wc -l < "$CLAUDE_VOICE_DIR/edits.jsonl" | tr -d ' ')" 1
check "write request ignored for scripts" "$(fires "$(router 'write a script that sends a message to slack')")" no
check "grammar-only check" "$(router 'can u check this: i went to the shop yesterday and their was no milk so i went to the other one which was closed aswell, honestly what a day it has been for me and my mates who were with me' | grep -c 'Fix only spelling' || true)" 1
check "engineering prompt is not grammar-only" "$(router 'fix the login flow so it redirects properly and check that the session cookie is set before we render the dashboard and also make sure the logout button clears everything in local storage too please' | grep -c 'Fix only spelling' || true)" 0
check "code prompt ignored" "$(fires "$(router 'fix the error on line 40 in app.ts, the function returns undefined')")" no
check "unrelated prompt ignored" "$(fires "$(router 'can u prep a one pager for my meeting tomorrow about the api changes')")" no

# robustness: malformed transcript lines must not crash either hook
printf '%s\n' 'x' '[1]' '"str"' '{"type":"assistant","message":"oops"}' '{"type":"assistant","message":{"content":[1,"a",null]}}' '{"type":"user","message":{"content":[null]}}' > "$T/bad.jsonl"
rc=0; err="$(echo "{\"prompt\":\"i think we should do it, thoughts? $(printf 'word %.0s' $(seq 30))\",\"transcript_path\":\"$T/bad.jsonl\"}" | python3 -I "$here/hooks/voice-router.py" 2>&1 >/dev/null)" || rc=$?
check "router survives bad transcript" "$rc:$err" "0:"
rc=0; err="$(echo "{\"transcript_path\":\"$T/bad.jsonl\"}" | python3 -I "$here/hooks/pushback-check.py" 2>&1 >/dev/null)" || rc=$?
check "pushback survives bad transcript" "$rc:$err" "0:"
rc=0; err="$(echo '[1]' | python3 -I "$here/hooks/pushback-check.py" 2>&1)" || rc=$?
check "pushback survives non-object input" "$rc:$err" "0:"

# pushback: "let's" as an instruction is not an opinion
transcript "let's commit this" "Exactly."
check "let's instruction does not fire" "$(fires "$(pushback)")" no

# scripts
printf 'one two three four\n' > "$T/a.md"; printf 'one two three four\n' > "$T/b.md"
check "save_edit skips no-change" "$(python3 -I "$here/skills/my-voice/scripts/save_edit.py" email "$T/a.md" "$T/b.md" | grep -c 'nothing saved')" 1
printf 'one two three four five\n' > "$T/c.md"
python3 -I "$here/skills/my-voice/scripts/save_edit.py" email "$T/a.md" "$T/c.md" >/dev/null
check "save_edit dedups" "$(python3 -I "$here/skills/my-voice/scripts/save_edit.py" email "$T/a.md" "$T/c.md")" "Already saved."
check "pick_samples runs" "$(python3 -I "$here/skills/my-voice/scripts/pick_samples.py" email | grep -c 'EDITS')" 1

rm -rf "$CLAUDE_VOICE_DIR"
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
