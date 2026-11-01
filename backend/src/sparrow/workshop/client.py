"""The office's side of the workshop contract.

Plain httpx against the workshop's HTTP API — the office never imports the
agent SDK and never touches a workspace the workshop holds. Configured by
WORKSHOP_URL and WORKSHOP_TOKEN in the office's environment.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterator

import httpx

from sparrow.workshop.store import pack


class WorkshopError(RuntimeError):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"workshop {status}: {detail}")
        self.status = status
        self.detail = detail


class Workshop:
    def __init__(self, url: str | None = None, token: str | None = None) -> None:
        self.url = (url or os.environ.get("WORKSHOP_URL") or "http://127.0.0.1:8100").rstrip("/")
        token = token or os.environ.get("WORKSHOP_TOKEN")
        if not token:
            raise WorkshopError(503, "WORKSHOP_TOKEN is not set in the office environment")
        self._headers = {"authorization": f"Bearer {token}"}

    def _client(self, timeout: float = 60) -> httpx.Client:
        return httpx.Client(base_url=self.url, headers=self._headers,
                            timeout=httpx.Timeout(timeout, connect=10))

    @staticmethod
    def _check(r: httpx.Response) -> httpx.Response:
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text
            raise WorkshopError(r.status_code, str(detail))
        return r

    def info(self, pid: str) -> dict:
        with self._client() as c:
            return self._check(c.get(f"/projects/{pid}")).json()

    def push(self, pid: str, workspace: Path) -> dict:
        with self._client(300) as c:
            return self._check(c.put(f"/projects/{pid}/workspace", content=pack(workspace),
                                     headers={"content-type": "application/gzip"})).json()

    def ensure(self, pid: str, workspace: Path) -> bool:
        """Hand the project to the workshop if it does not hold it yet.

        Once handed over the workshop's copy is the one that changes; pushing
        again would overwrite the user's studio edits with the generated site.
        Returns True if this call did the handover.
        """
        if self.info(pid)["exists"]:
            return False
        self.push(pid, workspace)
        return True

    def put_dossier(self, pid: str, text: str) -> dict:
        with self._client() as c:
            return self._check(c.put(f"/projects/{pid}/dossier", content=text.encode(),
                                     headers={"content-type": "text/markdown"})).json()

    def preview(self, pid: str, path: str) -> httpx.Response:
        """One file of the built export, as the workshop serves it (status kept)."""
        with self._client() as c:
            return c.get(f"/projects/{pid}/preview/{path}")

    def pull(self, pid: str) -> bytes:
        with self._client(300) as c:
            return self._check(c.get(f"/projects/{pid}/workspace")).content

    def build(self, pid: str) -> dict:
        with self._client(400) as c:
            return self._check(c.post(f"/projects/{pid}/build")).json()

    def put_asset(self, pid: str, name: str, data: bytes) -> dict:
        with self._client(120) as c:
            return self._check(c.put(f"/projects/{pid}/assets/{name}", content=data,
                                     headers={"content-type": "application/octet-stream"})).json()

    def pages(self, pid: str) -> list[str]:
        with self._client() as c:
            return self._check(c.get(f"/projects/{pid}/pages")).json()

    def links(self, pid: str) -> list[dict]:
        with self._client() as c:
            return self._check(c.get(f"/projects/{pid}/links")).json()

    def checkpoints(self, pid: str) -> list[dict]:
        with self._client() as c:
            return self._check(c.get(f"/projects/{pid}/checkpoints")).json()

    def undo(self, pid: str) -> dict:
        with self._client() as c:
            return self._check(c.post(f"/projects/{pid}/undo")).json()

    def restore(self, pid: str, cid: str) -> dict:
        with self._client() as c:
            return self._check(c.post(f"/projects/{pid}/restore/{cid}")).json()

    def turn(self, pid: str, message: str, llm_token: str) -> Iterator[dict]:
        """Stream one studio turn's events."""
        with self._client(None) as c:
            with c.stream("POST", f"/projects/{pid}/turns",
                          json={"message": message, "llm_token": llm_token}) as r:
                if r.status_code >= 400:
                    r.read()
                    self._check(r)
                for line in r.iter_lines():
                    if line.startswith("data: "):
                        yield json.loads(line[6:])
