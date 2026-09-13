---
description: Export the finished site and walk the user through putting it online
argument-hint: "[project-id]"
---

Run `bin/site export $ARGUMENTS`.

Tell the user where the folder is and what it is: plain HTML, CSS and JavaScript,
no build step and no server, which drops onto any host as-is.

Then ask where they want it. If they don't know, recommend Netlify Drop — it is
drag-and-drop and takes about a minute — and offer the alternatives (Vercel,
Cloudflare Pages, GitHub Pages, or their existing host) if they have a preference.

Assume they have never deployed anything. Walk them through it one step at a time
and wait for them at each step. Do not paste a wall of CLI commands.
