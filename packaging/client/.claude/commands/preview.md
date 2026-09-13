---
description: Build the site and give the user a link to look at
argument-hint: "[project-id]"
---

Run `bin/site preview $ARGUMENTS` and give the user the URL on its own line.

Then ask one open question — "what do you want to change?" — and stop. Do not
volunteer a list of things you think are wrong with it. They are looking at their
own website; let them react to it first.

When they do react, fix it directly in
`projects/$ARGUMENTS/workspace/src/components/sections/`, then
`bin/site preview $ARGUMENTS --rebuild`.

After any batch of hand edits, run `bin/site audit $ARGUMENTS` to check you have
not introduced a colour or a spacing value that is not in the design system.
