---
description: Write a longer piece with the user one paragraph at a time. They approve or rewrite each paragraph before the next one.
argument-hint: [what the piece is about]
---

Write this with the user one paragraph at a time: $ARGUMENTS

1. Follow the `my-voice` skill first (their take, then their samples).
2. Show a 3-6 line outline of the paragraphs. Wait for "ok" or their changes.
3. Write paragraph 1 only. They reply "ok", rewrites it, or says what to change. If they rewrite it, use their version word for word and save the pair with `save_edit.py`.
4. Repeat until done. Each new paragraph should follow on from the approved ones, in their wording.
5. At the end, show the full piece once as a copyable block and save it to `~/.claude-voice/drafts/`.
