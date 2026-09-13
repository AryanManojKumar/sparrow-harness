#!/usr/bin/env python3
"""Formatting and payload helpers for bin/site.

A separate file rather than inline `python3 -c` strings: quoting JSON inside a
shell string inside an f-string is how these scripts break silently six months
later, and nothing here is worth that.
"""
from __future__ import annotations

import json
import sys


def _load() -> object:
    raw = sys.stdin.read()
    try:
        return json.loads(raw)
    except Exception:
        sys.stdout.write(raw)
        raise SystemExit(0)


def pp() -> None:
    print(json.dumps(_load(), indent=2))


def advance() -> None:
    """One readable line per server-sent event."""
    for line in sys.stdin:
        line = line.strip()
        if not line.startswith("data:"):
            continue
        try:
            e = json.loads(line[5:].strip())
        except Exception:
            continue
        if not e:
            continue
        cost = "  ${:.4f}".format(e["cost"]) if e.get("cost") else ""
        stage = e.get("stage", "")
        print("  {:<14} {}{}".format(stage, e.get("message", ""), cost), flush=True)


def gate() -> None:
    g = _load()
    if not g.get("awaiting"):
        print("no gate open — the run is either finished or still working.")
        return
    print("GATE  " + g["gate"])
    print("      " + g["question"] + "\n")
    for o in g.get("options", []):
        if "asset_id" in o:
            # The available choices differ per kind — a logo is not offered
            # "generate", so never assume the three image options.
            print("  IMAGE {:<16} [{}] {}".format(
                o["asset_id"], o.get("prominence", ""), (o.get("brief") or "")[:64]))
            print("        in section {} · options: {}".format(
                o.get("section_id", "?"),
                " | ".join(c["choice"] for c in o.get("choices", []))))
            if o.get("uploaded"):
                print("        a file has already been uploaded for this slot")
        elif "ask_id" in o:
            print("  FACT  {:<16} {}".format(
                o["ask_id"], (o.get("question") or "")[:64]))
            if o.get("draft"):
                print("        current draft: " + str(o["draft"])[:80])
            if o.get("source_example"):
                print("        a source site says: " + str(o["source_example"])[:70])
        else:
            key = o.get("index", o.get("choice"))
            print("  [{}] {}".format(key, o.get("signature") or o.get("label") or ""))
            if o.get("atmosphere"):
                print("      " + str(o["atmosphere"])[:110])
    print("\nanswer with:  bin/site answer <id> '<json>'   (see CLAUDE.md for the shape)")


def status() -> None:
    p = _load()
    print("project {}   stage {}   spent ${}".format(
        p["project_id"], p["stage"], p["spent"]))
    if p.get("awaiting_gate"):
        print("waiting at gate: " + p["awaiting_gate"])
    print()
    for e in p.get("log", [])[-25:]:
        print("  {:<14} {}".format(e["stage"], e["message"]))


def projects() -> None:
    for p in _load():
        print("  {:<34} {:<16} ${}".format(
            p.get("project_id", "?"), p.get("stage", "?"), p.get("spent", 0)))


def interview_body() -> None:
    print(json.dumps({"prompt": sys.argv[2]}))


def create_body() -> None:
    """brief file + project id + urls -> the POST /projects payload."""
    pid, path, *urls = sys.argv[2:]
    d = json.load(open(path))
    b = d.get("brief", d)
    missing = [k for k in ("category", "offering", "audience", "tone", "primary_action")
               if not b.get(k)]
    if missing:
        sys.exit("brief is missing: " + ", ".join(missing))
    print(json.dumps({
        "project_id": pid,
        "product_name": b.get("product_name") or "",
        "category": b["category"],
        "offering": b["offering"],
        "audience": b["audience"],
        "tone": b["tone"],
        "primary_action": b["primary_action"],
        "secondary_action": b.get("secondary_action"),
        "constraints": d.get("constraints", []),
        "urls": list(urls),
    }))


def rebuild_body() -> None:
    sections, stage = sys.argv[2], sys.argv[3]
    print(json.dumps({
        "sections": [s for s in sections.split(",") if s],
        "stage": stage,
    }))


if __name__ == "__main__":
    globals()[sys.argv[1].replace("-", "_")]()
