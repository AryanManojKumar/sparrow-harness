---
description: Start a new website from a sentence about the business
argument-hint: "[what the business does, and any reference URLs]"
---

Start a new site. The user said: $ARGUMENTS

Work through this with them, one step at a time. Do not batch it and do not run
ahead — every step below has a point where they decide something.

1. If `$ARGUMENTS` is empty or vague, ask the two questions from CLAUDE.md and stop.
2. `bin/site up` if the engine is not already running.
3. `bin/site interview "<their description>"` — then show them the **assumptions**
   it made in plain sentences, not the JSON, and let them correct it. Edit the saved
   brief file with their corrections.
4. Agree on 2–3 reference URLs. If they have none, propose two from their category
   and say why you picked them.
5. `bin/site new <project-id> --brief <file> --url … --url …`
   Project id: lowercase, hyphenated, short.
6. `bin/site advance <id>` and then work the gate loop in CLAUDE.md.

Tell them once, up front, that a full run takes a few minutes of work and a few
dollars of API credit, and that it will stop three times to ask them something.
