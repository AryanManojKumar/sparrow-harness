#!/usr/bin/env bash
# Assemble the client deliverable: the engine, the scaffold, the console, and a
# .claude that turns a fresh Claude Code session into a site-building interview.
#
# What is deliberately NOT in it: the git history, past clients' builds under
# projects/, the run logs, the experiments, the competitor research, and the
# internal design document. The client gets a product, not a workshop.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="sparrow-site-builder"
OUT="$SRC/dist"
SECRETS=1
DESIGN_DOC=0

while [ $# -gt 0 ]; do
  case "$1" in
    --name)             NAME="$2"; shift 2 ;;
    --out)              OUT="$2"; shift 2 ;;
    --no-secrets)       SECRETS=0; shift ;;
    --with-design-doc)  DESIGN_DOC=1; shift ;;
    -h|--help)
      cat <<'HELP'
usage: packaging/make-client-zip.sh [options]

  --name <folder>      name of the folder inside the zip (default sparrow-site-builder)
  --out <dir>          where to write the zip (default dist/)
  --no-secrets         ship .env.example instead of the real keys
  --with-design-doc    include the internal design document as docs/HARNESS.md
HELP
      exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
done

command -v zip >/dev/null 2>&1 || { echo "zip is not installed (apt install zip)" >&2; exit 1; }

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
DEST="$STAGE/$NAME"
mkdir -p "$DEST"

say() { printf '  %s\n' "$*"; }
echo "assembling $NAME"

# ── the engine ────────────────────────────────────────────────────────────────
rsync -a \
  --exclude '.venv/' --exclude '__pycache__/' --exclude '*.py[cod]' \
  --exclude '.pytest_cache/' --exclude '.uv/' --exclude 'logs/' \
  --exclude 'README.md' --exclude 'kie-veo docs.md' \
  "$SRC/backend/" "$DEST/backend/"
say "backend/"

# ── the site scaffold every build starts from ────────────────────────────────
rsync -a \
  --exclude 'node_modules/' --exclude '.next/' --exclude 'out/' \
  --exclude '*.tsbuildinfo' \
  "$SRC/scaffold/" "$DEST/scaffold/"
say "scaffold/"

# ── the optional visual console ──────────────────────────────────────────────
rsync -a \
  --exclude 'node_modules/' --exclude '.next/' --exclude 'out/' \
  --exclude '*.tsbuildinfo' --exclude 'public/resume.html' \
  --exclude 'AGENTS.md' --exclude 'CLAUDE.md' \
  "$SRC/frontend/" "$DEST/frontend/"
say "frontend/"

# ── the client-facing overlay: CLAUDE.md, README, .claude, bin ───────────────
rsync -a "$SRC/packaging/client/" "$DEST/"
chmod +x "$DEST/bin/site" "$DEST/bin/_fmt.py" "$DEST/.claude/hooks/session-start.py"
say ".claude/ bin/ CLAUDE.md README.md"

# Their sites land here. Empty, so no other client's work travels with it.
mkdir -p "$DEST/projects"
: > "$DEST/projects/.keep"

if [ "$DESIGN_DOC" = 1 ]; then
  mkdir -p "$DEST/docs"
  cp "$SRC/CLAUDE.md" "$DEST/docs/HARNESS.md"
  say "docs/HARNESS.md (internal design document — you asked for it)"
fi

# ── keys ──────────────────────────────────────────────────────────────────────
if [ "$SECRETS" = 1 ]; then
  [ -f "$SRC/backend/.env" ] || { echo "backend/.env not found" >&2; exit 1; }
  cp "$SRC/backend/.env" "$DEST/backend/.env"
  printf 'NEXT_PUBLIC_API_URL=http://127.0.0.1:8000\n' > "$DEST/frontend/.env.local"
  say "backend/.env — REAL KEYS, live and spendable"
else
  rm -f "$DEST/backend/.env"
  printf 'NEXT_PUBLIC_API_URL=http://127.0.0.1:8000\n' > "$DEST/frontend/.env.local"
  say "backend/.env omitted — the client must fill in .env.example"
fi

# ── sanity: nothing that should not travel ───────────────────────────────────
for bad in .git logs experiments reference report logotemp .wrangler \
           AGENTS.md AGENT-RESEARCH.md; do
  if [ -e "$DEST/$bad" ]; then echo "refusing to ship $bad" >&2; exit 1; fi
done
if [ -n "$(find "$DEST/projects" -mindepth 1 -not -name '.keep' -print -quit)" ]; then
  echo "refusing to ship: projects/ is not empty" >&2; exit 1
fi

mkdir -p "$OUT"
ZIP="$OUT/$NAME.zip"
rm -f "$ZIP"
( cd "$STAGE" && zip -qr "$ZIP" "$NAME" )

echo
echo "  $ZIP"
echo "  $(du -h "$ZIP" | cut -f1)  ·  $(unzip -Z1 "$ZIP" | wc -l) files"
if [ "$SECRETS" = 1 ]; then
  echo "  contains live API keys — hand it over the way you would hand over a password"
fi
