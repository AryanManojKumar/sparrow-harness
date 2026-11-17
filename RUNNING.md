# Running Sparrow — setup, run, deploy

> How to get the whole harness running from a fresh checkout, on a Mac or on Linux, and how
> to put it on a server as a demo. Written from an actual setup on an Apple Silicon MacBook
> (2026-11-16), including every error hit along the way.
> For *what* the system is and *why* it is shaped this way, read `OVERVIEW.md` first, then
> `CLAUDE.md`. For the HTTP API, `backend/API.md`.

---

## 1. What actually runs

Four processes. Three are Python (FastAPI/uvicorn) in `backend/`, one is the Next.js console.

```
 browser ──► FRONTEND  :3000   Next.js console (frontend/)
                │
                ▼  NEXT_PUBLIC_API_URL
             OFFICE    :8000   sparrow.api — the pipeline, blackboards, provider keys
                │
                ▼  Bearer WORKSHOP_TOKEN
             WORKSHOP  :8100   sparrow.workshop.app — the ONLY place model-written code
                │                runs: the agent (DeepSeek Harness) and `next build`,
                │                each inside a bubblewrap (bwrap) jail
                ▼  per-project signed token
             GATEWAY   :8001   sparrow.gateway — swaps the agent's token for the real
                                 provider key; the workshop never holds a key
```

Why three backend processes instead of one: the office holds everything worth stealing
(keys, every project's blackboard). The workshop runs code a model wrote. If the agent
escapes its jail it should find other websites, not keys. The gateway is a separate
listener because, when it was mounted inside the office, an agent in the jail could read
every project with one `curl` (measured). Full reasoning: docstrings at the top of
`backend/src/sparrow/workshop/__init__.py`, `gateway.py`, `workshop/jail.py`.

| Process | Needs | Reads config from |
|---|---|---|
| office | Python, Playwright Chromium, Node + pnpm, ffmpeg | `backend/.env` |
| gateway | Python | `backend/.env` |
| workshop | Python + DeepSeek Harness SDK, Node, **bwrap (Linux only)** | `backend/workshop.env` — deliberately NOT `.env` |
| frontend | Node + pnpm | `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`) |

**The workshop only runs on Linux.** Every agent turn and every build starts with `bwrap`,
which does not exist on macOS, and there is no unjailed fallback (on purpose). On a Mac,
the backend runs inside a Linux VM — §4.

Since the default builder is the agent (`SPARROW_BUILDER=agent`), the BUILD stage runs in
the workshop too. **Without a working workshop, no new site gets built.** The older
section-by-section builder (`SPARROW_BUILDER=sections`) does not need it.

State is plain files, not a database: `projects/<id>/` (blackboard, uploads, logs, a real
Next.js workspace) and `workshop-data/<id>/` (the workshop's copy, agent sessions, git
checkpoints). Both are gitignored. `CLAUDE.md` mentions Postgres and Redis — the code
does not use either yet.

---

## 2. Configuration

### `backend/.env` — office and gateway

Copy `backend/.env.example` to `backend/.env`. Never commit it (it is gitignored).

| Variable | Required | What it is |
|---|---|---|
| `SPARROW_PROVIDER` | yes | `azure`, `openai` or `anthropic`. **The studio/agent path only supports `azure` and `openai`** — the gateway refuses anthropic |
| `OPENAI_API_KEY` | if provider is openai | |
| `AZURE_APIM_KEY`, `AZURE_APIM_BASE_URL` | if provider is azure | |
| `ANTHROPIC_API_KEY` | if provider is anthropic | |
| `KIE_API_KEY` | for generated images | plus `KIE_IMAGE_MODEL`, `KIE_EDIT_MODEL` |
| `ELEVENLABS_API_KEY` | for generated video | optional |
| `GATEWAY_SECRET` | **yes** | 32+ random chars. Office signs agent tokens with it, gateway checks them. Generate: `openssl rand -hex 32` |
| `WORKSHOP_TOKEN` | **yes** | 24+ random chars. Office sends it on every call to the workshop. Generate: `openssl rand -base64 32` |
| `WORKSHOP_URL` | no | default `http://127.0.0.1:8100` |
| `SPARROW_BUILDER` | no | `agent` (default) or `sections` |

The office reads `.env` **once at start**. `--reload` watches code, not `.env` — restart
the office after changing it.

### `backend/workshop.env` — workshop only

Create it by hand. It must contain **no provider keys**: a workshop that can read them has
defeated the point of being separate.

| Variable | Required | What it is |
|---|---|---|
| `WORKSHOP_TOKEN` | **yes** | the **same value** as in `.env` |
| `WORKSHOP_DEPS` | yes in practice | a folder whose `node_modules` holds the scaffold's dependencies **built on Linux**. Mounted read-only into every jail as the site's `node_modules`. Default `scaffold/` |
| `WORKSHOP_LLM_URL` | no | default `http://127.0.0.1:8001/llm/v1` (the gateway) |
| `WORKSHOP_NODE` | no | Node install prefix; default: found from `which node` |
| `WORKSHOP_ROOT` | no | default `workshop-data/` at the repo root |
| `WORKSHOP_IDLE_SECONDS` | no | how long an idle agent stays warm, default 900 |

Quick way to create it from `.env`:

```bash
cd backend
grep '^WORKSHOP_TOKEN=' .env > workshop.env
```

---

## 3. Running on Linux (a dev box or a server)

Tested on Ubuntu (arm64). x86_64 is the same — DeepSeek Harness ships wheels for both.

### 3.1 System packages

```bash
sudo apt update
sudo apt install -y bubblewrap ffmpeg curl git ca-certificates

# Node 22 — Ubuntu's own nodejs is too old for Next 16
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pnpm

# uv (Python manager; it installs the right Python itself)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.profile
```

### 3.2 Check the jail works

```bash
bwrap --ro-bind / / --unshare-all true && echo "JAIL OK"
```

If it prints `setting up uid map: Permission denied`, Ubuntu (24.04+) is blocking
unprivileged sandboxes. Allow them:

```bash
echo 'kernel.apparmor_restrict_unprivileged_userns=0' | sudo tee /etc/sysctl.d/99-bwrap.conf
sudo sysctl --system
```

### 3.3 Python dependencies

```bash
cd backend
uv sync --extra workshop                       # --extra workshop = the DeepSeek Harness SDK
uv run playwright install --with-deps chromium # the browser the office studies references with
```

### 3.4 The shared site dependencies (`WORKSHOP_DEPS`)

Every generated site is a copy of `scaffold/`. Rather than install `node_modules` per site,
the workshop mounts one shared install into every jail. It must be built on the machine
that runs the workshop (Linux binaries for Next's compiler, Tailwind, lightningcss).

```bash
mkdir -p ~/sparrow-deps
cp scaffold/package.json scaffold/pnpm-lock.yaml scaffold/pnpm-workspace.yaml ~/sparrow-deps/
cd ~/sparrow-deps
npx -y pnpm@11.22.0 install --frozen-lockfile   # the scaffold pins pnpm 11.22.0
```

Then add to `backend/workshop.env`:

```
WORKSHOP_DEPS=/home/<you>/sparrow-deps
```

(If the workshop runs from a plain Linux checkout, `cd scaffold && pnpm install` and the
default `WORKSHOP_DEPS=scaffold/` also works. The separate folder is what keeps a Mac
checkout and a Linux VM from overwriting each other's `node_modules` — §4.)

### 3.5 Frontend dependencies

```bash
cd frontend && pnpm install
```

### 3.6 Start — four terminals, in this order

```bash
# 1 — gateway
cd backend && uv run uvicorn sparrow.gateway:app --port 8001

# 2 — workshop
cd backend && uv run --extra workshop uvicorn --factory sparrow.workshop.app:create_app --port 8100

# 3 — office  (API docs at http://localhost:8000/docs)
cd backend && uv run sparrow serve --port 8000 --reload

# 4 — frontend
cd frontend && pnpm dev          # http://localhost:3000
```

Check: `curl http://localhost:8000/health` → `{"status":"ok"}`.

---

## 4. Running on a Mac (what we actually did)

The Mac cannot run the workshop (no `bwrap`). So: **frontend on the Mac, the three backend
processes in a small Ubuntu VM** via OrbStack. The VM sees the Mac's files at the same
path (`/Users/<you>/...`), so you edit code in your IDE as normal and `--reload` picks it
up inside the VM.

```
 Mac:  browser ─► localhost:3000 (frontend, pnpm dev)
                       │  localhost:8000 (OrbStack forwards VM ports to the Mac)
 VM:   office :8000 ─► workshop :8100 (bwrap works here) ─► gateway :8001 ─► provider
```

The one trap: the Mac and the VM share the repo folder but need **different builds** of
the same dependencies (macOS vs Linux). So the VM keeps its own Python environment and its
own `node_modules` **in the VM's home folder**, never inside the repo.

### 4.1 Install OrbStack and create the VM (Mac terminal)

```bash
cd ~
brew install --cask orbstack
open -a OrbStack                 # finish the first-run prompts
orb create ubuntu sparrow        # an Ubuntu VM named "sparrow"
```

(OrbStack's first run may also create a default machine called `ubuntu`; it is unused —
`orb delete ubuntu` if you like.)

### 4.2 Inside the VM

Open a shell in it with `orb -m sparrow`, then:

1. Run **§3.1** (system packages) and **§3.2** (jail check). On OrbStack the jail worked
   without the AppArmor fix.
2. Keep the VM's Python environment out of the repo — **in `~/.profile`, not `~/.bashrc`**
   (Ubuntu's `.bashrc` returns early for non-interactive shells, so `orb -m sparrow bash -lc
   '…'` would never see it, and uv would rebuild the Mac's `backend/.venv` as Linux):

   ```bash
   echo 'export UV_PROJECT_ENVIRONMENT=$HOME/.venvs/sparrow' >> ~/.profile
   source ~/.profile
   ```
3. `cd /Users/<you>/…/sparrow-harness` and run **§3.3** (Python deps) and **§3.4**
   (shared site deps in `~/sparrow-deps`, then `WORKSHOP_DEPS` in `workshop.env`).

Do **not** run `pnpm install` for `frontend/` inside the VM — the frontend stays on the Mac.

### 4.3 Start (three Mac terminal tabs + one for the frontend)

```bash
orb -m sparrow bash -lc 'cd /Users/<you>/…/sparrow-harness/backend && uv run uvicorn sparrow.gateway:app --port 8001'
orb -m sparrow bash -lc 'cd /Users/<you>/…/sparrow-harness/backend && uv run --extra workshop uvicorn --factory sparrow.workshop.app:create_app --port 8100'
orb -m sparrow bash -lc 'cd /Users/<you>/…/sparrow-harness/backend && uv run sparrow serve --host 0.0.0.0 --port 8000 --reload'

# on the Mac itself:
cd frontend && pnpm dev
```

The office uses `--host 0.0.0.0` so the Mac can reach it; the VM is on OrbStack's private
network, not your Wi-Fi. The gateway and workshop stay on `127.0.0.1` — they only talk to
each other inside the VM.

If `curl http://localhost:8000/health` does not answer from the Mac, point the frontend
at the VM by name: `NEXT_PUBLIC_API_URL=http://sparrow.orb.local:8000 pnpm dev`.

---

## 5. A first run, end to end (no UI needed)

What we used to test the harness: a fictional cat café, three real reference sites, eleven
real photos. Through the console UI it is the same flow with buttons.

```bash
API=http://localhost:8000

# 1. create — the brief, the reference sites, and (optionally) which one is primary
curl -X POST $API/projects -H 'content-type: application/json' -d '{
  "project_id": "tabby-hours",
  "product_name": "Tabby Hours",
  "category": "Local service: cat café with adoptable rescue cats",
  "offering": "A cat café in Pune where guests book a 60-minute session …",
  "audience": "Young professionals and students in Pune aged 20-35 …",
  "tone": "Warm, playful and calm. Never cutesy baby-talk.",
  "primary_action": "Book a session",
  "secondary_action": "Meet the adoptable cats",
  "constraints": ["Do not invent prices, cat counts or adoption statistics"],
  "urls": ["https://crumbsandwhiskers.com", "https://www.cattownoakland.org", "https://www.meowparlour.com"],
  "main_reference": "https://crumbsandwhiskers.com"
}'

# 2. run to the next gate (SSE stream). Stops at: design direction
curl -N -X POST $API/projects/tabby-hours/advance
curl $API/projects/tabby-hours/gate                  # three directions + specimen images
curl -X POST $API/projects/tabby-hours/gate -H 'content-type: application/json' -d '{"choice": 1}'

# 3. run on. Stops at: the material gate — per image slot, and per invented fact
curl -N -X POST $API/projects/tabby-hours/advance
curl $API/projects/tabby-hours/gate

# 4. upload your files FIRST, then answer the gate
curl -X POST $API/projects/tabby-hours/assets/hero-1 -F file=@photo.jpg
curl -X POST $API/projects/tabby-hours/owner-images -F file=@extra.jpg -F "caption=What is in the photo"
curl -X POST $API/projects/tabby-hours/gate -H 'content-type: application/json' -d '{
  "assets":  {"nav-logo": "wordmark", "hero-1": "upload", "owner-1": "upload", "…": "…"},
  "content": {"about-2": "a real fact that replaces a drafted one"}
}'

# 5. build + verify (30-45 min). Stops at: preview
curl -N -X POST $API/projects/tabby-hours/advance
open $API/projects/tabby-hours/preview/
```

Measured on that run: **$6.02** total (≈$1 references + design directions, ≈$5 agent build
+ one fix round), about 13 minutes of machine time from the material gate to the preview.

Rules the gates enforce (each is a `400` with a readable reason, not a silent default):

- every image slot must be answered; a **logo** is `upload` or `wordmark`, never `skip`
- `upload` needs the file posted first
- facts are saved **before** images are checked — if the image part fails, resend only
  `assets`, or the fact ids come back as "no such content ask" (known issue, §7)

---

## 6. Deploying a demo (one Linux server)

Enough to send someone a link. Not multi-user — see `OVERVIEW.md` "What it would take to
deploy" for that.

**Server:** Ubuntu, 4 vCPU / 8 GB RAM, ~40 GB disk (each project is 300–770 MB). Do §3.1
to §3.5 on it as a normal user, with the repo cloned to e.g. `/srv/sparrow`.

### 6.1 One origin, one login

The console calls the API from the browser, and site previews are served by the API under
`/projects/<id>/preview/` with that path baked in. The simplest safe layout is **one domain,
Caddy in front of everything, a password on the whole site**:

```
https://demo.example.com/            → frontend  127.0.0.1:3000
https://demo.example.com/projects/…  → office    127.0.0.1:8000
   (also /suggest, /interview, /health, /docs, /redoc, /openapi.json)
```

One origin means the browser sends the login with API calls too, and the office's open
CORS setting (`allow_origins=["*"]`) never matters. Do **not** put the API under a prefix
like `/api` — the previews are built for `/projects/<id>/preview` exactly.

`/etc/caddy/Caddyfile`:

```caddy
demo.example.com {
    basic_auth {
        # generate the hash with:  caddy hash-password
        reviewer $2a$14$REPLACE_WITH_HASH
    }

    @api path /projects* /suggest /interview /health /docs /redoc /openapi.json
    handle @api {
        reverse_proxy 127.0.0.1:8000 {
            flush_interval -1        # stream SSE progress immediately
        }
    }
    handle {
        reverse_proxy 127.0.0.1:3000
    }
}
```

Build the frontend against that origin (the URL is baked in at build time):

```bash
cd /srv/sparrow/frontend
NEXT_PUBLIC_API_URL=https://demo.example.com pnpm build
```

### 6.2 Run the four processes as services

`/etc/systemd/system/sparrow-gateway.service` (the other three follow the same shape):

```ini
[Unit]
Description=Sparrow gateway
After=network.target

[Service]
User=sparrow
WorkingDirectory=/srv/sparrow/backend
ExecStart=/home/sparrow/.local/bin/uv run uvicorn sparrow.gateway:app --host 127.0.0.1 --port 8001
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

| Service | `ExecStart` |
|---|---|
| `sparrow-gateway` | `uv run uvicorn sparrow.gateway:app --host 127.0.0.1 --port 8001` |
| `sparrow-workshop` | `uv run --extra workshop uvicorn --factory sparrow.workshop.app:create_app --host 127.0.0.1 --port 8100` |
| `sparrow-office` | `uv run sparrow serve --host 127.0.0.1 --port 8000` (no `--reload` in production) |
| `sparrow-frontend` | `WorkingDirectory=/srv/sparrow/frontend`, `ExecStart=/usr/bin/pnpm start -H 127.0.0.1 -p 3000` |

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sparrow-gateway sparrow-workshop sparrow-office sparrow-frontend caddy
journalctl -u sparrow-office -f          # logs
```

Everything binds to `127.0.0.1`; only Caddy faces the internet.

### 6.3 Firewall and money

```bash
sudo ufw allow 22 && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable
```

- Ports 8000, 8001, 8100 and 3000 must **not** be reachable from outside.
- **Set hard monthly budget caps in each provider's dashboard** (OpenAI / Azure / KIE). The
  code has no per-project spend cap yet; a full site is ~$6–13, so the provider cap is the
  real safety net. Use keys made for the demo, and rotate them afterwards.
- Leave `SPARROW_LOG_PROMPTS` empty, so prompts are not written to logs the API serves.

What this does **not** give you (deliberately deferred until the product is finished): user
accounts, JWT auth, rate limits, per-user spend caps. Basic auth in Caddy is the stand-in.

### 6.4 Before shipping a frontend change

Every commit that touches `frontend/` runs `pnpm check` (types, lint, format, tests)
through the git hook in `.githooks/pre-commit`. `pnpm install` in `frontend/` switches it
on for your clone; check with `git config core.hooksPath` (should print `.githooks`).

The console is also held to Lighthouse ≥ 98 (mobile and desktop) with zero layout shift,
and a first-load JavaScript budget. With the backend running:

```bash
cd frontend
pnpm perf          # ~4 min: production build, JS budget, Lighthouse medians; exit 1 on failure
```

`PERF_PROJECT=<id>` picks the project `/build` is measured on (default `tabby-hours`).
What it checks and why, and the mistakes that already cost points: `frontend/AGENTS.md`.

---

## 7. Troubleshooting — every error we actually hit

| Symptom | Cause | Fix |
|---|---|---|
| Studio message → `500`, office log `httpx.ConnectError: [Errno 61] Connection refused` in `_handover` | the workshop is not running | start it (§3.6) |
| Workshop won't start: `WORKSHOP_TOKEN must be set (24+ characters)` | no `backend/workshop.env` (the workshop never reads `.env`) | §2: copy the token line into `workshop.env` |
| Workshop won't start: `WORKSHOP_DEPS=… has no node_modules` | shared site deps not installed | §3.4 |
| Gateway → `503 GATEWAY_SECRET is not set` | missing from `.env` | add it, **restart the office too** |
| Studio / build → `500`, workshop log `FileNotFoundError: … 'bwrap'` | running the workshop on macOS | run the backend in the VM (§4) |
| `setting up uid map: Permission denied` | Ubuntu blocks unprivileged user namespaces | §3.2 sysctl |
| Gateway → `the studio gateway does not support provider 'anthropic'` | studio speaks OpenAI chat-completions only | `SPARROW_PROVIDER=openai` or `azure` |
| Changed `.env`, nothing changed | office reads `.env` only at start | restart the office |
| In the VM, uv starts rebuilding `backend/.venv` | `UV_PROJECT_ENVIRONMENT` not set for that shell | put it in `~/.profile` (§4.2) |
| Material gate: `no such content ask(s): about-2` after a failed answer | facts were already saved by the failed call; `GET /gate` still shows them (known bug) | resend only the `assets` part |
| Material gate: `nav-logo needs one of upload, wordmark` | a logo is never skipped or generated | answer `wordmark` if there is no logo |
| Grey/brown blocks over a person in a photo on the built site | the PII scrub replaced a face region — even a person seen from behind (known issue) | swap the image in the studio, or upload a photo without people |
