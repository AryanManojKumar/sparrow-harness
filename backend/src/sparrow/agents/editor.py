"""Pointed edits: change the thing the user clicked, leave the rest.

Separate from Builder (which designs a section from a blueprint) and from
Fixer/Repairer (which answer a named defect or a compile error). A pointed
edit has a human instruction and a selected element; the job is the smallest
change that does what they asked.
"""

from __future__ import annotations

import re

from sparrow.agents.base import FIDELITY_LINE, Agent, stable_system
from sparrow.agents.builder import BuildOutput
from sparrow.blackboard.schema import Blackboard, Section
from sparrow.providers import Tier

_CODE = re.compile(r"```(?:tsx|typescript|ts|jsx)?\s*\n(.*?)```", re.DOTALL)

SYSTEM = """You are editing ONE section file in a Next.js 16 project because a
human pointed at an element in the live preview and said what to change.

Change as little as possible. Do the instruction to the selected element, and
do not redesign, restyle, or restructure anything they did not name. If the
same string appears more than once, change the one that matches the selector
and the surrounding markup — not every occurrence.

The token vocabulary is not yours. Do not invent colours, type, spacing or
motion the design system does not already have.

{fidelity}

Output format — exactly this, nothing else:

```tsx
<the complete corrected file>
```"""


class Editor(Agent):
    name = "editor"
    tier = Tier.TOP
    max_tokens = 16000

    def edit(self, bb: Blackboard, section: Section, code: str,
             instruction: str, element: dict) -> BuildOutput:
        user = "\n\n".join([
            f"<section>\nid: {section.id}\nfile: {section.target_path}\n</section>",
            _element_block(element),
            f"<instruction>\n{instruction.strip()}\n</instruction>",
            f'<file path="{section.target_path}">\n{code}\n</file>',
        ])
        res = self.call(
            system=stable_system(SYSTEM.format(fidelity=FIDELITY_LINE), bb),
            user=user,
        )
        m = _CODE.search(res.text)
        if not m:
            raise ValueError(f"editor returned no code block for {section.id}")
        return BuildOutput(m.group(1).strip(), None, res)


def _element_block(element: dict) -> str:
    lines = [
        f"tag: {element.get('tag') or '?'}",
        f"text: {element.get('text') or ''}",
        f"selector: {element.get('selector') or ''}",
        f"aria-label: {element.get('aria_label') or element.get('ariaLabel') or ''}",
        f"section_id: {element.get('section_id') or element.get('sectionId') or ''}",
        f"file_hint: {element.get('file_hint') or element.get('fileHint') or ''}",
    ]
    return "<selected_element>\n" + "\n".join(lines) + "\n</selected_element>"
