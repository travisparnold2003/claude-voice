# claude-voice

Makes Claude Code write like you, and learn from every rewrite you make.

Rule lists ("never say delve", "no em dashes") only go so far. Claude still sounds like Claude, and telling a model what not to write can even make it more likely to write it. This kit takes a different route: Claude reads real things you wrote, and every time you change one of its drafts, the before and after get saved as an example for next time.

It also adds a pushback check, so Claude stops agreeing with your ideas just to be nice.

## What it does

Everything runs on its own once installed. You don't type any commands.

1. **Learns from your rewrites.** A rewrite is recognised when you paste your version of a draft Claude showed in a code block or quote, or saved to the drafts folder, in its last few replies or the last 7 days. The pair is saved. Say "sent", "submitted" or "posted" (and mention an email, post, message or similar, or have a recent draft in the folder), and Claude goes to find the version you actually sent and saves the difference.
2. **Writes from your real writing.** When you ask for an email, post or message, Claude first reads about 5 real samples (things you wrote yourself plus messages you typed to Claude Code) and your latest rewrites. If the piece needs your opinion, it asks you first.
3. **Fixes only grammar when you wrote it.** Paste your own text (40+ words) with "check this", "check my", "proofread" or "grammar check" and it fixes spelling and grammar, keeps your words, and lists each change. It stays off when the message talks about code, files, tests or builds.
4. **Pushback check.** When you share an opinion or a plan and Claude opens its reply by agreeing ("You're right", "Great idea"), it adds 2-3 lines with the strongest case against, then says whether it still agrees. Bug reports don't trigger it.
5. **Plain reply style.** An output style for Claude's replies to you: point first, short sentences, plain words, no "Great question!".

Optional commands: `/calibrate` (Claude writes 3 short pieces, you rewrite them, a quick way to seed examples), `/polish` and `/para` (write a long piece one paragraph at a time).

## Install

```
git clone https://github.com/travisparnold2003/claude-voice
cd claude-voice && bash install.sh
```

Then start a new Claude Code session. The installer backs up your `~/.claude/settings.json` first, adds two hooks, and turns on the Plain output style unless you already picked one. Before it overwrites a file you already have, it copies it to `~/.claude/.claude-voice-backup-<timestamp>/`; the first-ever copy of your settings is also kept as `settings.json.orig-claude-voice`. Run `bash tests/run.sh` to check the hooks.

For better results, put a few emails and posts you wrote yourself, without AI, in `~/.claude-voice/samples/email` and `~/.claude-voice/samples/post`. Leave out anything AI wrote, or Claude will learn to copy itself.

## Where your data goes

- Your samples, drafts and rewrites live in `~/.claude-voice` (or `$CLAUDE_VOICE_DIR`). Nothing goes in this repo.
- The messages you typed to Claude Code are read from Claude Code's own local chat history (`~/.claude/projects`). Claude Code deletes those after 30 days by default. Set `cleanupPeriodDays` in settings to keep more.
- When Claude writes something for you, your samples and rewrites go to the model as context, like anything else you paste into a chat.
- The pushback check keeps a log at `~/.claude-voice/pushback.log` (last 500 lines). Each entry includes the first 200 characters of your prompt and the start of Claude's reply. Delete it any time.
- The hooks call no other model and no network.

## Turning things off

- `touch ~/.claude-voice/voice-off` stops the rewrite learning and the writing prompts.
- `touch ~/.claude-voice/pushback-off` stops the pushback check.
- `/output-style` switches the reply style back to default.

## Limits

- The pushback check runs after the reply is already on screen (that's how Claude Code's Stop hook works), so it shows up as a short second message. The Plain style also asks Claude to put the counterpoint in the first reply, so the second message is a backstop.
- A rewrite is only recognised when it's at least about 30% similar to a recent draft. A full rewrite from scratch won't be caught unless you say you sent it.
- A rewrite is only recognised for drafts Claude showed in a code block or quote, or saved to the drafts folder. A draft in plain paragraphs won't be matched unless you say you sent it.
- It needs real samples. With only a handful of chat messages, posts and emails will still drift towards Claude's default voice.

## Why it works this way

- Examples beat descriptions. Anthropic's docs call examples [one of the most reliable ways to steer tone](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) (see also the [prompt engineering overview](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview)).
- Negative instructions can backfire. A model told "don't mention X" can end up more likely to mention it: [Don't Think of the White Bear](https://arxiv.org/abs/2511.12381) (arXiv 2511.12381).
- Your edits are the most direct signal there is: the gap between what Claude wrote and what you changed it to is your style.
- Don't expect miracles: [a study of style imitation](https://arxiv.org/abs/2509.14543) found models approximate personal style from a few samples in structured formats like email, but struggle with informal writing.

MIT licence. Built on macOS. It should run on Linux too, apart from the clipboard shortcut in `save_edit.py -` and `/polish`.
