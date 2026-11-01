"""Projects on the workshop's disk: import, export, checkpoints.

    <root>/<pid>/workspace/        the website (what the jail sees read-write)
    <root>/<pid>/dsh-home/         the agent's sessions
    <root>/<pid>/checkpoints.git/  history of the workspace
    <root>/<pid>/launcher.sh       the jailed `dsh` the SDK execs

Checkpoints are git, with the git directory OUTSIDE the workspace. Inside it,
the agent could rewrite or delete its own history with one bash call, and undo
is the user's safety net against exactly the turns that went wrong. Outside,
the jail cannot see it at all.

A project id becomes a path, so it is validated before it touches the disk.
Uploaded archives are extracted with tarfile's `data` filter, which refuses
absolute paths, `..`, links leaving the destination and device files — the
office is trusted, but an archive is still bytes that name paths.
"""

from __future__ import annotations

import io
import re
import shutil
import subprocess
import tarfile
from html.parser import HTMLParser
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

_PID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

# Never shipped in either direction. node_modules is mounted from the shared
# install; .next and out are build products the workshop makes itself.
EXCLUDE = ("node_modules", ".next", "out")

MAX_ARCHIVE = 200_000_000


class StoreError(ValueError):
    pass


def valid_pid(pid: str) -> str:
    if not _PID.match(pid):
        raise StoreError(f"invalid project id {pid!r}")
    return pid


@dataclass(frozen=True)
class Project:
    pid: str
    dir: Path

    @property
    def workspace(self) -> Path:
        return self.dir / "workspace"

    @property
    def home(self) -> Path:
        return self.dir / "dsh-home"

    @property
    def git_dir(self) -> Path:
        return self.dir / "checkpoints.git"

    @property
    def launcher(self) -> Path:
        return self.dir / "launcher.sh"

    @property
    def dossier(self) -> Path:
        return self.workspace / "AGENTS.md"

    @property
    def export(self) -> Path:
        return self.workspace / "out"

    def exists(self) -> bool:
        return self.workspace.is_dir() and self.git_dir.is_dir()


def project(root: Path, pid: str) -> Project:
    return Project(valid_pid(pid), root / pid)


def _excluded(name: str) -> bool:
    parts = [p for p in PurePosixPath(name).parts if p != "."]
    return bool(parts) and (parts[0] in EXCLUDE or parts[0] == ".git")


def routes(export: Path) -> list[str]:
    """The pages of a built export, as URL paths: ["/", "/pricing/", …].

    Next's own error pages are not pages an owner made.
    """
    if not export.is_dir():
        return []
    out = []
    for html in export.rglob("index.html"):
        rel = html.parent.relative_to(export).as_posix()
        if rel.startswith(("_next", "_not-found", "404", "assets")):
            continue
        out.append("/" if rel == "." else f"/{rel}/")
    return sorted(out, key=lambda r: (r != "/", r))


_ASSET = re.compile(r"^[a-z0-9][a-z0-9-]{0,60}\.(png|jpg|jpeg|webp|gif|mp4|webm)$")
MAX_ASSET = 80_000_000


def save_asset(proj: Project, name: str, data: bytes) -> str:
    """Write a generated file into public/assets/. Returns its workspace path.

    The name is a whole filename checked against a strict pattern — it comes
    from the agent through the gateway, and it is about to become a path.
    An existing file is never overwritten: the agent may be wrong about which
    image it is replacing, and the owner's own photos live in this folder too.
    """
    if not _ASSET.match(name):
        raise StoreError(f"invalid asset name {name!r}")
    if not data or len(data) > MAX_ASSET:
        raise StoreError("asset empty or too large")
    folder = proj.workspace / "public" / "assets"
    folder.mkdir(parents=True, exist_ok=True)
    stem, ext = name.rsplit(".", 1)
    target, n = folder / name, 2
    while target.exists():
        target, n = folder / f"{stem}-{n}.{ext}", n + 1
    target.write_bytes(data)
    return target.relative_to(proj.workspace).as_posix()


class _Links(HTMLParser):
    """Anchors (href + visible text) and element ids from one exported page."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.ids: set[str] = set()
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a":
            self._href, self._text = a.get("href") or "", []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None


def broken_links(export: Path, base: str) -> list[dict]:
    """Links on the built site that go nowhere: [{text, href, page, problem}].

    Three ways a generated link is dead, all seen on real builds: a `#`
    placeholder, a page that was never made, and an in-page anchor whose
    target never got the `id` (the generator's sections carry none). External,
    mail and phone links are not checked.
    """
    pages = routes(export)
    parsed: dict[str, _Links] = {}
    for route in pages:
        html = export / route.strip("/") / "index.html" if route != "/" else export / "index.html"
        p = _Links()
        p.feed(html.read_text(errors="replace"))
        parsed[route] = p
    base = base.rstrip("/")
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for route, p in parsed.items():
        for href, text in p.links:
            if href.startswith(("http://", "https://", "mailto:", "tel:", "//")):
                continue
            problem = ""
            if href in ("", "#"):
                problem = "goes nowhere"
            else:
                path, _, anchor = href.partition("#")
                if path.startswith(base):
                    path = path[len(base):]
                target = route if not path else ("/" + path.strip("/") + "/").replace("//", "/")
                if target not in parsed:
                    problem = f"page {target} does not exist"
                elif anchor and anchor not in parsed[target].ids:
                    problem = f"nothing on {target} has id \"{anchor}\""
            key = (text, href)
            if problem and key not in seen:
                seen.add(key)
                out.append({"text": text or "(no text)", "href": href, "page": route,
                            "problem": problem})
    return out


def pack(workspace: Path) -> bytes:
    """A gzipped tar of the workspace without dependencies or build output."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for p in sorted(workspace.iterdir()):
            if p.name in EXCLUDE or p.name == ".git":
                continue
            tar.add(p, arcname=p.name)
    return buf.getvalue()


def import_workspace(proj: Project, archive: bytes) -> None:
    """Replace the project's workspace with the archive, then checkpoint it."""
    if len(archive) > MAX_ARCHIVE:
        raise StoreError("archive too large")
    proj.dir.mkdir(parents=True, exist_ok=True)
    staging = proj.dir / "workspace.incoming"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            members = [m for m in tar.getmembers() if not _excluded(m.name)]
            tar.extractall(staging, members=members, filter="data")
    except (tarfile.TarError, OSError) as e:
        shutil.rmtree(staging, ignore_errors=True)
        raise StoreError(f"bad archive: {e}") from e
    shutil.rmtree(proj.workspace, ignore_errors=True)
    staging.rename(proj.workspace)
    # The mount point for the shared node_modules. Empty on disk; the jail
    # binds the real one over it.
    (proj.workspace / "node_modules").mkdir(exist_ok=True)
    proj.home.mkdir(exist_ok=True)
    if not proj.git_dir.is_dir():
        _git(proj, "init", "-q")
    _write_exclude(proj)
    checkpoint(proj, "Imported the generated site")


def _write_exclude(proj: Project) -> None:
    # AGENTS.md is the office's to write, not part of the site: undoing a turn
    # must not roll back what the agent is told about the site.
    exclude = proj.git_dir / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text("".join(f"/{x}\n" for x in (*EXCLUDE, "AGENTS.md")))


def write_dossier(proj: Project, text: str) -> None:
    """Put the office's dossier at the workspace root, plus the studio's history.

    The history is the workshop's own knowledge — what was changed here and
    when — so it is appended here rather than sent by the office.
    """
    _write_exclude(proj)
    rows = [c for c in checkpoints(proj) if c["message"] != "Imported the generated site"]
    if rows:
        text += ("\n## Changes already made in the studio (newest first)\n\n"
                 + "\n".join(f"- {c['message']}" for c in rows[:30]) + "\n")
    proj.dossier.write_text(text)


# ── checkpoints ─────────────────────────────────────────────────────────────

def _git(proj: Project, *args: str) -> str:
    r = subprocess.run(
        ["git", f"--git-dir={proj.git_dir}", f"--work-tree={proj.workspace}",
         "-c", "user.name=workshop", "-c", "user.email=workshop@localhost",
         "-c", "commit.gpgsign=false", *args],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise StoreError(f"git {args[0]}: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout


def changed_files(proj: Project) -> list[str]:
    """Paths that differ from the last checkpoint, including new files."""
    _git(proj, "add", "-A")
    out = _git(proj, "diff", "--cached", "--name-only")
    return [line for line in out.splitlines() if line]


def files_since(proj: Project, base: str) -> list[str]:
    """Paths that differ between checkpoint `base` and the working tree."""
    _git(proj, "add", "-A")
    out = _git(proj, "diff", "--cached", "--name-only", base)
    return [line for line in out.splitlines() if line]


def checkpoint(proj: Project, message: str) -> str | None:
    """Commit the workspace if anything changed. Returns the new id, or None."""
    _git(proj, "add", "-A")
    has_head = subprocess.run(
        ["git", f"--git-dir={proj.git_dir}", "rev-parse", "--verify", "-q", "HEAD"],
        capture_output=True).returncode == 0
    if has_head and not _git(proj, "diff", "--cached", "--name-only").strip():
        return None
    _git(proj, "commit", "-q", "-m", message[:200])
    return _git(proj, "rev-parse", "--short", "HEAD").strip()


def checkpoints(proj: Project, limit: int = 50) -> list[dict]:
    out = _git(proj, "log", f"-{limit}", "--format=%h%x09%ct%x09%s")
    rows = []
    for line in out.splitlines():
        cid, ts, msg = line.split("\t", 2)
        rows.append({"id": cid, "at": int(ts), "message": msg})
    return rows


def restore(proj: Project, cid: str, message: str) -> str | None:
    """Make the workspace match checkpoint `cid`, recorded as a NEW checkpoint.

    Forward-only: undo is itself undoable, and nothing the user saw is lost.
    """
    if not re.fullmatch(r"[0-9a-f]{4,40}", cid):
        raise StoreError(f"invalid checkpoint id {cid!r}")
    _git(proj, "rev-parse", "--verify", "-q", f"{cid}^{{commit}}")
    # Drop anything untracked first so files the turn created disappear too.
    _git(proj, "clean", "-fdq")
    _git(proj, "read-tree", "-u", "--reset", cid)
    return checkpoint(proj, message)


def head(proj: Project) -> str:
    return _git(proj, "rev-parse", "HEAD").strip()


def reset_to(proj: Project, cid: str) -> None:
    """Make the workspace match `cid` WITHOUT recording anything.

    For throwing away a turn that never became a checkpoint: a change that
    broke the build was never shown to the user, so there is nothing to undo.
    """
    _git(proj, "clean", "-fdq")
    _git(proj, "read-tree", "-u", "--reset", cid)


def squash_since(proj: Project, base: str, message: str) -> str | None:
    """Fold everything after `base`, plus the working tree, into one checkpoint.

    A turn makes intermediate commits while it builds and fixes; the user asked
    for one thing and gets one step in the history, undoable as one.
    """
    _git(proj, "reset", "-q", "--soft", base)
    return checkpoint(proj, message)


def undo(proj: Project) -> str | None:
    """Restore the checkpoint before the latest one."""
    rows = checkpoints(proj, limit=2)
    if len(rows) < 2:
        raise StoreError("nothing to undo")
    return restore(proj, rows[1]["id"], f"Undid: {rows[0]['message']}")
