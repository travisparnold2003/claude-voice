---
name: my-voice
description: Writes anything that goes out under the user's name (posts, emails, messages to people) in their real voice, from real samples of their writing and their own past edits, and saves their edits afterwards so the next draft is closer. Use whenever you draft text the user will send or post. Not for replies to the user themselves.
---

# my-voice

Write the way the user actually writes. Learn it from their real text and from the changes they make to your drafts, not from a list of rules.

## 1. Get their take first (when it's their opinion or story)

If the piece needs their opinion, a story or a reason only they know, ask first. Ask one or two short questions in plain words, one at a time: what actually happened, what annoyed them, or how they would say it out loud. Use their words in the draft. Skip this for routine replies where the facts are already in the thread.

## 2. Load their writing

```bash
python3 -I ~/.claude/skills/my-voice/scripts/pick_samples.py <post|email|message>
```

It prints about 5 real samples (longer pieces they wrote, plus messages they typed to Claude) and their most recent edits to earlier drafts. Read them before writing a word.

- Copy the rhythm, sentence length, punctuation, openers and sign-offs of the samples. The edits show what they cut and what they add back.
- The samples are for voice only. Never reuse their facts, names or events.
- Keep casual spelling for chat messages. For emails and posts, their real email and post samples are the bar.

## 3. Draft

Write the draft so it reads like the next sample in the list. Keep only what they would say.

Save the draft you hand them to `$CLAUDE_VOICE_DIR/drafts/<YYYY-MM-DD>-<slug>.md` (default `~/.claude-voice`) so their edit can be captured later.

## 4. Save their edit

Mostly automatic: the `voice-router.py` hook saves the pair whenever they paste their own rewrite of a recent draft, and when they say they sent or posted something it tells you to go and find the sent version. When the final differs from your draft, save the pair:

```bash
python3 -I ~/.claude/skills/my-voice/scripts/save_edit.py <post|email|message> <draft file> <final file>   # or - to read the final from the clipboard
```

Every saved pair becomes an example for the next draft.

## Files (private, never in a git repo)

- `corpus-<account>.jsonl`: messages they typed to Claude Code. Refreshed daily by the hook, or run `extract_voice.py`.
- `samples/<email|post|message>/*.md`: longer things they wrote themselves, without AI.
- `edits.jsonl`: before/after pairs.

These samples and edits go to the model as context when this skill runs, the same as anything else in the chat.
