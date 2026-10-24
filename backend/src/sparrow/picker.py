"""Inject a click-to-select runtime into a served preview.

The console and the preview are different origins (frontend :3000, API :8000),
so the parent cannot read the framed document. The picker has to live inside
the HTML we serve. It talks back with `postMessage`; it never writes the
export on disk — the same `out/` stays portable for a static host.
"""

from __future__ import annotations

MARKER = 'data-sparrow-picker-runtime="1"'
SCRIPT = f'<script {MARKER} src="/static/picker.js"></script>'


def file_hint(section_id: str) -> str:
    """The path `step_sources` would have written this section to.

    Same derivation as `conftest.component_name` — `feature-grid` → FeatureGrid.
    """
    name = "".join(part.capitalize() for part in section_id.replace("_", "-").split("-") if part)
    return f"src/components/sections/{name}.tsx"


def inject_picker(html: str) -> str:
    """Put the picker runtime in the page, once.

    Inserts before `</body>` so it runs after the markup it will inspect.
    A page with no body tag still gets the script appended: a missing close
    tag is not a reason to serve an un-selectable preview.
    """
    if MARKER in html:
        return html
    lower = html.lower()
    idx = lower.rfind("</body>")
    if idx == -1:
        return html + SCRIPT
    return html[:idx] + SCRIPT + html[idx:]
