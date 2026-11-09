---
description: 15-minute voice calibration. Claude writes 3 short pieces, the user rewrites them their way, the pairs become examples for every future draft.
---

Run a voice calibration with the user, using the `my-voice` skill files.

1. Run `python3 -I ~/.claude/skills/my-voice/scripts/pick_samples.py message` and read it.
2. Pick 3 realistic situations they write in, one per format: a short email to a client or supplier, the first 4-5 lines of a LinkedIn post about something they built, and a chat message to a friend or colleague. Use situations from their real life you can see in the samples, without copying their details.
3. Show ONE draft at a time, as plain text they can copy. Ask them to rewrite it exactly how they'd send it (rough is fine) and paste it back.
4. For each answer: save the draft to `~/.claude-voice/drafts/calibrate-<n>.md` and their version to `~/.claude-voice/drafts/calibrate-<n>-final.md`, then run `python3 -I ~/.claude/skills/my-voice/scripts/save_edit.py <email|post|message> <draft> <final>`.
5. After each pair, say in one line what you noticed they changed (for example "you cut the greeting and the sign-off"). Then show the next draft.
6. Finish with the count of stored edits. Nothing else.
