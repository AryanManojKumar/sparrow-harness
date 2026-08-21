# Reference corpus

Leaked/open system prompts from comparable products, kept locally so the analysis in
`AGENT-RESEARCH.md` stays verifiable. Read-only — do not edit.

| Dir | Source | Why it's here |
|---|---|---|
| `orchids/` | Orchids.app | **#1 on UI-Bench** (30.12, 67.5% win rate). Router → design-system → coding-agent pipeline; the subagent delegation contract in AGENT-RESEARCH.md §2 |
| `emergent/` | Emergent | Closest analogue: main agent + 6 tool-subagents. Context-fade note, gradient 80/20 rule, subagent-verification warning |
| `lovable/` | Lovable | #3 on UI-Bench. Design-system-as-token-file enforcement; the v3 color-function bug Tailwind v4 removes |
| `v0/` | v0 (Vercel) | The design guidelines section — color/typography/icon ban list |
| `superdesign/` | superdesigndev/superdesign-skill | The design-agent SOP: design-system.md contract, fidelity enforcement, website extraction |

Upstream: [x1xhlol/system-prompts-and-models-of-ai-tools](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools),
[superdesigndev/superdesign-skill](https://github.com/superdesigndev/superdesign-skill)
