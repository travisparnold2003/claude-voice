---
description: The user wrote it themselves. Fix only spelling, grammar and clear typos, keep every word choice, and show what changed.
argument-hint: [text, or leave empty to use the clipboard]
---

The user wrote this themselves. Your only job is to fix spelling, grammar and obvious typos.

Text: $ARGUMENTS
(If that is empty, read it with `pbpaste`.)

- Keep their words, their order, their slang and their tone. Don't rephrase, shorten, add or "improve" anything.
- Keep casual style that is clearly on purpose (lowercase product names, "..", "->").
- Return the corrected text as one block they can copy, then a short list of each change as `old -> new`. If nothing needed fixing, say so in one line.
- Copy the corrected text to the clipboard with `pbcopy`.
