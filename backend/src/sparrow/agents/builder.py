"""The builder.

Builds one section per call. Each call is independent and sees no other
section's code — that is the production condition, and experiments/drift-test-01
measured what survives it.

What the builder may change: layout, composition, density, rhythm, responsive
behaviour, interaction. What it may not: the token vocabulary. When a section
genuinely needs vocabulary that does not exist, it says so rather than taking it
silently (see `extension_request`).
"""

from __future__ import annotations

import re
from pathlib import Path

from sparrow.agents.base import FIDELITY_LINE, Agent, context_block, stable_system
from sparrow.blackboard.schema import Blackboard, Blueprint, Ground, Section
from sparrow.providers import Completion, Tier

SYSTEM = """You are the builder for a website harness. You build ONE section per call.

You are given the brief, the hard constraints, the design system, and one blueprint.
You do NOT see any other section. Another agent built those, to the same design system.
Do not attempt to reference, import from, or guess at them.

LAYOUT, COMPOSITION, DENSITY AND RHYTHM ARE YOURS. Make real design decisions.
THE TOKEN VOCABULARY IS NOT YOURS. It is fixed, and it is fixed for a reason: five
sections built independently have to read as one page.

{fidelity}

Output format — exactly this, nothing else:

```tsx
<the complete file contents>
```

If, and only if, the section cannot be built well without a token that does not exist
in the design system, add after the code block:

EXTENSION_REQUEST: <one line naming the token and why the section needs it>

Do not use an extension request to avoid a constraint. Do not use one for something the
existing vocabulary already covers."""

_CODE = re.compile(r"```(?:tsx|typescript|ts|jsx)?\s*\n(.*?)```", re.DOTALL)
_EXT = re.compile(r"^EXTENSION_REQUEST:\s*(.+)$", re.MULTILINE)


class BuildOutput:
    def __init__(self, code: str, extension_request: str | None, usage: Completion) -> None:
        self.code = code
        self.extension_request = extension_request
        self.usage = usage


class Builder(Agent):
    name = "builder"
    tier = Tier.TOP          # the builder is one of three agents that sets the ceiling
    max_tokens = 16000       # reasoning models spend tokens before they emit any

    def build(
        self,
        bb: Blackboard,
        section: Section,
        blueprint: Blueprint,
        *,
        stack: str,
        available_primitives: list[str],
    ) -> BuildOutput:
        # Stated as an instruction, not as context. Written as "this section sits
        # on X" it was read as background information and ignored by 4 of 5
        # sections — see experiments/drift-test-02.
        ground_class = "bg-background" if section.ground is Ground.PAGE else "bg-muted"

        system = stable_system(
            SYSTEM.format(fidelity=FIDELITY_LINE),
            bb,
            f"<stack>\n{stack.strip()}\n"
            f"shadcn primitives already present in src/components/ui/: "
            f"{', '.join(sorted(available_primitives))}\n</stack>\n\n"
            "<copy>\nWrite real copy for this specific product. No lorem ipsum, no "
            "placeholder brackets, no bracketed TODOs.\n</copy>",
        )

        user = "\n\n".join([
            f"<blueprint>\n"
            f"id: {blueprint.id}\n"
            f"purpose: {blueprint.purpose}\n"
            f"slots: {', '.join(blueprint.slots)}\n"
            f"structure: {blueprint.structure}\n"
            f"</blueprint>",
            f"<section>\n"
            f"file: {section.target_path}\n"
            f"component: {section.component_name} (default export)\n"
            f"REQUIRED: the root <section> element MUST carry the class "
            f"`{ground_class}`. Section ground alternates across the page and is "
            f"decided at page level — it is not yours to choose, and omitting it "
            f"flattens the page rhythm.\n"
            f"</section>",
        ])

        res = self.call(system=system, user=user)

        m = _CODE.search(res.text)
        if not m:
            raise ValueError(
                f"builder returned no code block for {section.id}:\n{res.text[:400]}"
            )
        ext = _EXT.search(res.text)
        return BuildOutput(m.group(1).strip(), ext.group(1).strip() if ext else None, res)


REPAIR_SYSTEM = """You are repairing ONE file in a Next.js 16 project. The build failed.

You are given the file, the build error, and the design system it must still obey.
Change as little as possible: fix the error and nothing else. Do not redesign, do not
restructure, do not "improve" anything the error did not name.

{fidelity}

Output format — exactly this, nothing else:

```tsx
<the complete corrected file>
```"""


class Repairer(Agent):
    """Fixes a section against a real build error.

    Separate from `Builder` because the job is different: the builder makes design
    decisions, the repairer makes the smallest change that clears a named error.
    Giving one agent both jobs invites it to redesign a section while "fixing" an
    import.
    """

    name = "repairer"
    tier = Tier.TOP
    max_tokens = 16000

    def repair(self, bb: Blackboard, section: Section, code: str, error: str) -> BuildOutput:
        user = "\n\n".join([
            f"<file path=\"{section.target_path}\">\n{code}\n</file>",
            f"<build_error>\n{error.strip()[:4000]}\n</build_error>",
        ])
        res = self.call(
            system=stable_system(REPAIR_SYSTEM.format(fidelity=FIDELITY_LINE), bb),
            user=user,
        )
        m = _CODE.search(res.text)
        if not m:
            raise ValueError(f"repairer returned no code block for {section.id}")
        return BuildOutput(m.group(1).strip(), None, res)


def write_section(workspace: Path, section: Section, code: str) -> Path:
    target = workspace / section.target_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(code if code.endswith("\n") else code + "\n")
    return target
