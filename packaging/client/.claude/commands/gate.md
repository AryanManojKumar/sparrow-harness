---
description: Show the open gate and help the user answer it
argument-hint: "[project-id]"
---

Run `bin/site gate $ARGUMENTS` and put the question to the user **in their language**.

- **gate:brief** — ask for the business name as it should read in the browser tab.
- **gate:design** — run `bin/site specimens $ARGUMENTS`, open each PNG and actually
  look at it. Describe the three directions in one sentence each, the way you would
  describe them to someone across a desk. Then ask which. If none fit, ask what to
  change and send it back with `{"choice":"other","note":"…"}`.
- **gate:assets** — go through the images one at a time. Push for real uploads,
  especially for anything with text in it; generated screenshots come back with
  gibberish labels. Answer the content questions with the user's real facts, never
  your own invention.

Never answer a gate on the user's behalf without asking them first.
Once answered, continue with `bin/site advance $ARGUMENTS`.
