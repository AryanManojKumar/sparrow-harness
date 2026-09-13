# prominence-01 — two unstated things, stated

Two defects from the ide-01 full rerun, both the same class as the section-ground and
motion bugs: something the pipeline never said, so the builder chose, and chose badly.

## 1. Asset prominence

`imagery_treatment` says how to FRAME an image — chrome, bleed, shadow. It says nothing
about SIZE. So four generated captures rendered at roughly quarter width, where the code,
hunk headers and commit hashes that make them convincing are invisible. The most expensive
asset in the pipeline was being used as texture.

`Asset.prominence` — `dominant` / `supporting` / `thumbnail` — assigned by curator (a lone
asset carries its section; several share the load), stated as a requirement in the builder
prompt with concrete numbers: dominant means at least 60% of section height and full
container width or bleeding past an edge.

| hero image | before | after |
|---|---|---|
| share of container width | ~50% | **84%** |
| share of section height | ~30% | **55%** |

The capture is now legible: task table with agent names, branches, statuses and
timestamps, and a real diff with syntax colouring.

## 2. Entrance animations with no guaranteed end state

Ten elements shipped at `opacity: 0`. All ten sat in sections built before the fix, using
`whileInView` where the observer never fired for a headless capture. The rebuilt hero,
which animates on mount, has none.

Now a requirement: an element that starts invisible and waits for a trigger you cannot
guarantee is a defect, not a pattern. Prefer animate-on-mount for the first screenful.

## 3. My own check was too crude

The inspector flagged 14 "still transparent" elements. Breaking that down: **10 at exactly
0.00** and **7 at 0.80/0.96** — deliberate dimming counted as a defect. A threshold of 0.9
buries the signal in noise.

Tightened to `<= 0.05`, and the report now carries each element's y-position and first
words so a defect can be located rather than just counted.

## Cost

One hero rebuild, $0.131.
