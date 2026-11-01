"""The workshop boundary: jail shape, safe import, checkpoints, gateway, auth.

No model, no browser, no bwrap. What is tested is everything the boundary is
made of that can be wrong without anything crashing: a jail that binds one
directory too many, an archive that writes outside its project, an undo that
leaves the turn's new files behind, a gateway that forwards the studio token
instead of swapping it.
"""

from __future__ import annotations

import io
import json
import tarfile
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from sparrow import gateway
from sparrow.workshop import store
from sparrow.workshop.app import create_app
from sparrow.workshop.config import WorkshopConfig
from sparrow.workshop.jail import JailMounts, jail_argv, launcher_script
from sparrow.workshop.studio import Translator


# ── jail ────────────────────────────────────────────────────────────────────

def _mounts(tmp: Path) -> JailMounts:
    return JailMounts(workspace=tmp / "p" / "workspace", home=tmp / "p" / "dsh-home",
                      node=tmp / "node", node_modules=tmp / "deps" / "node_modules",
                      readonly=(tmp / "runtime",))


def _binds(argv: list[str], flag: str) -> list[tuple[str, str]]:
    return [(argv[i + 1], argv[i + 2]) for i, a in enumerate(argv) if a == flag]


def test_jail_writes_only_workspace_and_home(tmp_path):
    m = _mounts(tmp_path)
    argv = jail_argv(m, ["next", "build"], {})
    assert _binds(argv, "--bind") == [(str(m.workspace), str(m.workspace)),
                                      (str(m.home), str(m.home))]
    ro = dict(_binds(argv, "--ro-bind"))
    assert ro[str(m.node_modules)] == str(m.workspace / "node_modules")
    assert str(tmp_path / "runtime") in ro
    # Nothing of the host's /home or the harness tree is visible.
    assert not any(src in ("/", "/home") for src, _ in _binds(argv, "--ro-bind"))


def test_jail_node_modules_mounts_over_workspace(tmp_path):
    m = _mounts(tmp_path)
    argv = jail_argv(m, ["x"], {})
    ws_bind = argv.index(str(m.workspace))
    nm_bind = argv.index(str(m.node_modules))
    assert nm_bind > ws_bind, "node_modules must be bound after the workspace or it is hidden"


def test_jail_clears_environment_and_runs_command_last(tmp_path):
    m = _mounts(tmp_path)
    argv = jail_argv(m, ["next", "build"], {"EXTRA": "1"})
    assert "--clearenv" in argv
    envs = dict(_binds(argv, "--setenv"))
    assert envs["HOME"] == str(m.home) and envs["EXTRA"] == "1"
    assert argv.index("--clearenv") < argv.index("--setenv")
    assert argv[-3:] == ["--", "next", "build"]
    assert "--unshare-all" in argv


def test_readonly_overlays_land_after_the_writable_mounts(tmp_path):
    m = _mounts(tmp_path)
    profiles = m.home / "profiles"
    argv = jail_argv(JailMounts(**{**m.__dict__, "readonly_over": (profiles,)}), ["x"], {})
    assert (str(profiles), str(profiles)) in _binds(argv, "--ro-bind")
    assert argv.index(str(profiles)) > argv.index(str(m.home)), \
        "an overlay bound before the home mount would be hidden by it"


def test_launcher_never_contains_the_token(tmp_path):
    script = launcher_script(_mounts(tmp_path), tmp_path / "dsh", ("STUDIO_LLM_TOKEN",))
    assert '"${STUDIO_LLM_TOKEN:?}"' in script
    assert '"${DSH_HOME:?}"' in script
    assert script.rstrip().endswith('"$@"')


# ── store ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("bad", ["../x", "A", "", "a/b", ".hidden", "x" * 65])
def test_pid_validation(bad):
    with pytest.raises(store.StoreError):
        store.valid_pid(bad)


def _site(root: Path) -> Path:
    ws = root / "src-ws"
    (ws / "src" / "app").mkdir(parents=True)
    (ws / "src" / "app" / "page.tsx").write_text("export default 1\n")
    (ws / "package.json").write_text('{"dependencies": {}}')
    (ws / "node_modules" / "big").mkdir(parents=True)
    (ws / "out").mkdir()
    (ws / "out" / "index.html").write_text("old build")
    return ws


def test_pack_import_roundtrip_excludes_dependencies(tmp_path):
    proj = store.project(tmp_path / "root", "site-1")
    store.import_workspace(proj, store.pack(_site(tmp_path)))
    assert (proj.workspace / "src/app/page.tsx").read_text() == "export default 1\n"
    assert list((proj.workspace / "node_modules").iterdir()) == []  # mount point only
    assert not (proj.workspace / "out").exists()
    assert [c["message"] for c in store.checkpoints(proj)] == ["Imported the generated site"]


def test_import_refuses_paths_outside_the_project(tmp_path):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = b"pwned"
        info = tarfile.TarInfo("../escape.txt")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    proj = store.project(tmp_path / "root", "site-1")
    with pytest.raises(store.StoreError):
        store.import_workspace(proj, buf.getvalue())
    assert not (tmp_path / "root" / "escape.txt").exists()


def test_undo_removes_files_the_turn_created(tmp_path):
    proj = store.project(tmp_path / "root", "site-1")
    store.import_workspace(proj, store.pack(_site(tmp_path)))
    (proj.workspace / "src/app/pricing").mkdir()
    (proj.workspace / "src/app/pricing/page.tsx").write_text("pricing")
    (proj.workspace / "src/app/page.tsx").write_text("edited")
    assert sorted(store.changed_files(proj)) == ["src/app/page.tsx", "src/app/pricing/page.tsx"]
    assert store.checkpoint(proj, "Add a pricing page")
    store.undo(proj)
    assert not (proj.workspace / "src/app/pricing").exists()
    assert (proj.workspace / "src/app/page.tsx").read_text() == "export default 1\n"
    # Undo is a new checkpoint, so it is itself undoable.
    assert [c["message"] for c in store.checkpoints(proj)][0] == "Undid: Add a pricing page"
    store.undo(proj)
    assert (proj.workspace / "src/app/pricing/page.tsx").read_text() == "pricing"


def test_checkpoint_history_lives_outside_the_workspace(tmp_path):
    proj = store.project(tmp_path / "root", "site-1")
    store.import_workspace(proj, store.pack(_site(tmp_path)))
    assert not (proj.workspace / ".git").exists()
    assert proj.git_dir.is_dir() and not proj.git_dir.is_relative_to(proj.workspace)


def test_no_checkpoint_when_nothing_changed(tmp_path):
    proj = store.project(tmp_path / "root", "site-1")
    store.import_workspace(proj, store.pack(_site(tmp_path)))
    assert store.checkpoint(proj, "nothing") is None


# ── studio events ───────────────────────────────────────────────────────────

def test_translator_reports_calls_results_and_plans_without_server_paths(tmp_path):
    ws = tmp_path / "workspace"
    t = Translator(ws)
    call = t({"event": {"type": "tool/call", "data": {
        "callId": "c1", "name": "edit", "arguments": json.dumps({
            "file_path": f"{ws}/src/components/sections/Nav.tsx",
            "old_string": "a", "new_string": "a\nb\nc"})}}})
    assert call == {"kind": "tool", "id": "c1", "tool": "edit",
                    "target": "src/components/sections/Nav.tsx", "detail": "+3 −1"}
    t({"event": {"type": "tool/call", "data": {"callId": "c2", "name": "read",
                                                "arguments": json.dumps({"file_path": f"{ws}/x.tsx"})}}})
    read = t({"event": {"type": "tool/result", "data": {"message": {
        "toolCallId": "c2", "isError": False,
        "content": [{"type": "text", "text": f"<path>{ws}/x.tsx</path>\n1: a\n2: b\n3: c"}]}}}})
    assert read == {"kind": "tool_result", "id": "c2", "ok": True, "summary": "3 lines"}
    t({"event": {"type": "tool/call", "data": {"callId": "c3", "name": "bash",
                                                "arguments": json.dumps({"command": "next build"})}}})
    bad = t({"event": {"type": "tool/result", "data": {"message": {
        "toolCallId": "c3", "isError": True,
        "content": [{"type": "text", "text": f"Error: cannot read {ws}/../secret"}]}}}})
    assert bad["ok"] is False and str(ws) not in bad["summary"]
    todos = t({"event": {"type": "todo/write", "data": {"todos": [
        {"content": "Add pricing", "status": "in_progress"}]}}})
    assert todos == {"kind": "todos", "items": [{"content": "Add pricing", "status": "in_progress"}]}


def test_translator_hides_bookkeeping_and_keeps_final_text_for_the_reply(tmp_path):
    t = Translator(tmp_path)
    assert t({"event": {"type": "tool/call", "data": {"callId": "q", "name": "todo_write",
                                                       "arguments": "{}"}}}) is None
    assert t({"event": {"type": "tool/result", "data": {"message": {
        "toolCallId": "q", "content": []}}}}) is None
    final = {"event": {"type": "assistant/message", "data": {"message": {
        "content": [{"type": "text", "text": "Done."}]}}}}
    assert t(final) is None
    narration = {"event": {"type": "assistant/message", "data": {"message": {"content": [
        {"type": "text", "text": "Checking the nav first."},
        {"type": "tool-call", "name": "read"}]}}}}
    assert t(narration) == {"kind": "note", "text": "Checking the nav first."}
    assert t({"event": {"type": "step/start"}}) is None


# ── gateway ─────────────────────────────────────────────────────────────────

@pytest.fixture
def secret(monkeypatch):
    monkeypatch.setenv("GATEWAY_SECRET", "s" * 40)


def test_tokens_are_signed_bound_to_one_project_and_expire(secret, monkeypatch):
    t = gateway.Tokens()
    a = t.issue("alpha")
    assert t.issue("alpha") == a, "a live token is reused so a warm runtime keeps working"
    assert gateway.Tokens.check(a) == "alpha"
    b = t.issue("beta")
    assert b != a and gateway.Tokens.check(b) == "beta"
    # Re-binding a token to another project breaks the signature.
    forged = a.replace(".alpha.", ".beta.")
    assert gateway.Tokens.check(forged) is None
    assert gateway.Tokens.check("stu.alpha.99999999999.iv.AAAA") is None
    # The capability set is signed too: an image-only token cannot be widened.
    img = t.issue("gamma", caps="i")
    assert gateway.Tokens.claims(img) == ("gamma", "i")
    assert gateway.Tokens.check(img.replace(".i.", ".iv.")) is None
    # A different secret (another office) cannot vouch for it.
    monkeypatch.setenv("GATEWAY_SECRET", "x" * 40)
    assert gateway.Tokens.check(a) is None
    monkeypatch.setenv("GATEWAY_SECRET", "s" * 40)
    real = time.time
    monkeypatch.setattr(gateway.time, "time", lambda: real() + gateway.TOKEN_TTL + 1)
    assert gateway.Tokens.check(b) is None


def test_tokens_near_expiry_are_replaced(secret, monkeypatch):
    t = gateway.Tokens()
    a = t.issue("alpha")
    real = time.time
    monkeypatch.setattr(gateway.time, "time",
                        lambda: real() + gateway.TOKEN_TTL - gateway.REUSE_MARGIN + 1)
    assert t.issue("alpha") != a


def test_office_api_does_not_expose_the_gateway():
    """The workshop can reach the gateway's port; it must not reach the office's."""
    from sparrow.api import app as office
    assert not [r for r in office.routes if getattr(r, "path", "").startswith("/llm")]


@pytest.fixture
def gw(monkeypatch, secret):
    monkeypatch.setenv("SPARROW_PROVIDER", "azure")
    monkeypatch.setenv("AZURE_APIM_KEY", "real-azure-key")
    monkeypatch.setenv("AZURE_APIM_BASE_URL", "https://apim.example/openai/v1")
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        # A streamed body, as the real upstream sends; a pre-read one cannot be relayed.
        return httpx.Response(200, headers={"content-type": "application/json"},
                              stream=httpx.ByteStream(b'{"choices": []}'))

    monkeypatch.setattr(gateway, "_client", httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(gateway, "TOKENS", gateway.Tokens())
    return TestClient(gateway.app), seen


def test_gateway_swaps_token_for_real_key_and_model(gw):
    client, seen = gw
    tok = gateway.TOKENS.issue("site-1")
    r = client.post("/llm/v1/chat/completions", headers={"authorization": f"Bearer {tok}"},
                    json={"model": "studio", "messages": [], "max_tokens": 900, "temperature": 0.2})
    assert r.status_code == 200
    (req,) = seen
    assert str(req.url) == "https://apim.example/openai/v1/chat/completions"
    assert req.headers["api-key"] == "real-azure-key"
    assert tok not in json.dumps(dict(req.headers)), "the studio token must not travel upstream"
    body = json.loads(req.content)
    assert body["model"] == gateway.MODELS["azure"][gateway.Tier.TOP]
    assert body["max_completion_tokens"] == 900 and "max_tokens" not in body
    assert "temperature" not in body


def test_gateway_refuses_bad_tokens_and_other_models(gw):
    client, seen = gw
    r = client.post("/llm/v1/chat/completions", headers={"authorization": "Bearer stu.site-1.9999999999.iv.nope"},
                    json={"model": "studio", "messages": []})
    assert r.status_code == 401
    tok = gateway.TOKENS.issue("site-1")
    r = client.post("/llm/v1/chat/completions", headers={"authorization": f"Bearer {tok}"},
                    json={"model": "gpt-5.6-sol", "messages": []})
    assert r.status_code == 400
    assert seen == []


# ── workshop api ────────────────────────────────────────────────────────────

class _FakeStudio:
    def busy(self, pid):
        return False


@pytest.fixture
def shop(tmp_path):
    cfg = WorkshopConfig(root=tmp_path / "root", token="t" * 32, deps=tmp_path,
                         node=tmp_path, llm_url="http://office/llm/v1")
    return TestClient(create_app(cfg, studio=_FakeStudio())), {"authorization": "Bearer " + "t" * 32}


def test_workshop_requires_the_office_token(shop):
    client, auth = shop
    assert client.get("/health").status_code == 200
    assert client.get("/projects/site-1").status_code == 401
    assert client.get("/projects/site-1", headers={"authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/projects/site-1", headers=auth).json()["exists"] is False


def test_workshop_import_then_history_and_preview_guard(shop, tmp_path):
    client, auth = shop
    r = client.put("/projects/site-1/workspace", headers=auth, content=store.pack(_site(tmp_path)))
    assert r.status_code == 200
    assert client.get("/projects/site-1", headers=auth).json()["exists"] is True
    assert len(client.get("/projects/site-1/checkpoints", headers=auth).json()) == 1
    # The client may normalize the dots away; refused either way.
    assert client.get("/projects/site-1/preview/../../workshop.env",
                      headers=auth).status_code in (400, 403, 404)
    assert client.get("/projects/site-1/preview/%2e%2e/%2e%2e/workshop.env",
                      headers=auth).status_code in (400, 403, 404)
    assert client.get("/projects/BAD..ID/checkpoints", headers=auth).status_code in (400, 404)


def test_routes_lists_owner_pages_only(tmp_path):
    out = tmp_path / "out"
    for rel in ["", "pricing", "blog/first", "_not-found", "404", "_next/static"]:
        (out / rel).mkdir(parents=True, exist_ok=True)
        (out / rel / "index.html").write_text("x")
    assert store.routes(out) == ["/", "/blog/first/", "/pricing/"]
    assert store.routes(tmp_path / "missing") == []


def test_broken_links_finds_placeholders_missing_pages_and_missing_anchors(tmp_path):
    out, base = tmp_path / "out", "/projects/p/preview"
    (out / "pricing").mkdir(parents=True)
    (out / "index.html").write_text(
        f'<nav><a href="#">Careers</a><a href="#features">Features</a>'
        f'<a href="{base}/pricing/">Pricing</a><a href="{base}/about/">About</a>'
        f'<a href="https://x.com">X</a><a href="mailto:a@b.c">Mail</a></nav>'
        f'<section id="hero"><a href="#hero">Top</a></section>')
    (out / "pricing" / "index.html").write_text(f'<a href="{base}/#hero">Home hero</a>')
    found = {(b["text"], b["problem"]) for b in store.broken_links(out, base)}
    assert found == {("Careers", "goes nowhere"),
                     ("Features", 'nothing on / has id "features"'),
                     ("About", "page /about/ does not exist")}


# ── assets over MCP ─────────────────────────────────────────────────────────

def _mcp(client, token, method, params=None, rid=1):
    return client.post("/mcp", headers={"authorization": f"Bearer {token}"},
                       json={"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})


def test_mcp_offers_only_the_kinds_the_token_allows(secret):
    client = TestClient(gateway.app)
    t = gateway.Tokens()
    init = _mcp(client, t.issue("site-1"), "initialize", {"protocolVersion": "2025-06-18"}).json()
    assert init["result"]["protocolVersion"] == "2025-06-18"
    full = _mcp(client, t.issue("site-1", caps="iv"), "tools/list").json()["result"]["tools"]
    assert full[0]["inputSchema"]["properties"]["kind"]["enum"] == ["image", "video"]
    img = _mcp(client, t.issue("site-2", caps="i"), "tools/list").json()["result"]["tools"]
    assert img[0]["inputSchema"]["properties"]["kind"]["enum"] == ["image"]
    none = _mcp(client, t.issue("site-3", caps="-"), "tools/list").json()["result"]["tools"]
    assert none == []
    assert client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).status_code == 401


def test_generate_asset_refuses_kinds_outside_the_caps_without_calling_the_provider(monkeypatch):
    from sparrow import eleven
    monkeypatch.setattr(eleven, "motion", lambda *a, **k: pytest.fail("provider was called"))
    text, err = gateway.generate_asset("site-1", "i", {"kind": "video", "prompt": "a calm office at dusk",
                                                       "shape": "wide", "filename": "x"})
    assert err and "not allowed" in text


def test_generate_asset_saves_through_the_workshop(monkeypatch):
    from sparrow import eleven
    from sparrow.workshop import client as wclient
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    monkeypatch.setattr(eleven, "generate", lambda prompt, shape: png)
    saved = {}

    class FakeWorkshop:
        def put_asset(self, pid, name, data):
            saved.update(pid=pid, name=name, data=data)
            return {"path": f"public/assets/{name}", "src": f"/projects/{pid}/preview/assets/{name}"}

    monkeypatch.setattr(wclient, "Workshop", FakeWorkshop)
    text, err = gateway.generate_asset("site-1", "iv", {
        "kind": "image", "prompt": "a sunlit desk with a notebook", "shape": "wide",
        "filename": "Pricing Hero!"})
    assert not err
    assert saved == {"pid": "site-1", "name": "pricing-hero.png", "data": png}
    assert 'src="/projects/site-1/preview/assets/pricing-hero.png"' in text


def test_save_asset_never_overwrites_and_rejects_bad_names(tmp_path):
    proj = store.project(tmp_path / "root", "site-1")
    store.import_workspace(proj, store.pack(_site(tmp_path)))
    assert store.save_asset(proj, "hero.png", b"a") == "public/assets/hero.png"
    assert store.save_asset(proj, "hero.png", b"b") == "public/assets/hero-2.png"
    assert (proj.workspace / "public/assets/hero.png").read_bytes() == b"a"
    for bad in ["../x.png", "x.exe", "X.png", "a/b.png", ".png"]:
        with pytest.raises(store.StoreError):
            store.save_asset(proj, bad, b"a")
