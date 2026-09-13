# Build your website

This folder builds a real website from a description of your business. You talk to
Claude; Claude drives the machine. You need to make about three decisions along the
way, and you end up with a finished site you can put online.

## Setup — once, about five minutes

You need four things installed. Check what you already have:

    bin/site doctor

Anything it marks MISSING, install:

| | macOS | Linux (Debian/Ubuntu) | Windows |
|---|---|---|---|
| **Node 20+** | `brew install node` | `sudo apt install nodejs` | [nodejs.org](https://nodejs.org) |
| **pnpm** | `npm install -g pnpm` | `npm install -g pnpm` | `npm install -g pnpm` |
| **uv** | `brew install uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| **Claude Code** | `npm install -g @anthropic-ai/claude-code` | same | same |

On Windows, run everything inside WSL. The build tools expect a Unix shell.

Then start the engine. The first run installs things and takes a couple of minutes:

    bin/site up

## Then just open Claude

    claude

It will say hello and ask what you want to build. Tell it in a sentence or two —
what your business does and who it's for — and paste a link to a website whose look
you like, if you have one.

From there it drives everything and stops to ask you when a decision is actually
yours to make. There are three of those:

1. **What is the business called?**
2. **Which of these three designs?** — it shows you three real rendered options.
3. **Where do the images come from?** — for each picture on the page, you either
   hand over a real one (your product, your logo, your photo) or let it invent one.

That third one is the one that matters most. A site with your real product
screenshots in it looks like a company. A site full of invented images looks like a
site full of invented images. Have your screenshots and your logo ready.

## Useful things to say to Claude

- **"show me the site"** — builds it and gives you a link
- **"make the hero bigger and the pricing section tighter"** — it just does it
- **"redo the pricing section completely"** — it rebuilds that section from scratch
- **"put it online"** — it exports the site and walks you through hosting it

There are shortcuts too, if you prefer typing commands: `/site`, `/gate`,
`/preview`, `/polish`, `/ship`, `/where`.

## Where your site lives

    projects/<your-project>/workspace/          the site, as source code
    projects/<your-project>/workspace/out/      the finished site, ready to host

The finished site is ordinary HTML, CSS and JavaScript. It works on any host and it
is yours — nothing in it phones home, and it does not depend on this folder once
it's built.

## If something goes wrong

    bin/site doctor            checks the setup
    bin/site status <project>  where the build got to
    bin/site up                restarts the engine

Or just tell Claude what you're seeing. It knows what the common failures mean.

## About cost

The build calls AI models, and that costs money against the API keys shipped in
this folder. A full site is a few dollars. Editing it afterwards is pennies.
`bin/site status <project>` shows the running total.
