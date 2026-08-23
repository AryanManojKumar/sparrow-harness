# image-probe-02 — restyling a real screenshot

probe-01 tested the wrong thing. It generated product UI from a text brief, but CLAUDE.md
§7's actual claim is about the user's **own** imagery: *"restyle a raw screenshot to match
the winning source's presentation."* That is an image-editing job, not a generation job.

Input: a real capture of drata.com's feature-detail section, complete with the pollution
any real screenshot has — a cookie consent dialog covering the lower-left, and a chat
widget with a stock photo of a person covering the lower-right, truncating three
paragraphs of copy.

Asked for: remove both overlays, reconstruct what they covered, restyle to a named design
system, and preserve every word.

## It works, and better than expected

- **Cookie dialog removed**, interface reconstructed beneath it
- **Chat widget and the person's photo removed** — which also satisfies the constraint
  *"no stock photos of people"* without anyone asking
- **Restyled correctly**: condensed grotesque headline replacing the rounded geometric,
  hairline rules instead of filled cards, branch blue confined to the eyebrow and the
  three markers, pale blue-grey ground
- **Visible text preserved exactly.** Every word that was legible in the input is
  verbatim in the output

36 seconds, one call.

## The dangerous part

The chat widget had truncated three paragraphs. The model **reconstructed the missing
text by inventing it**:

    input:  "Scale compliance across multiple ▓▓▓ to hundreds of tools,
             and maintain ▓▓▓ teams with a platform designed to ▓▓▓"

    output: "Scale compliance across multiple frameworks, adapt to hundreds of
             tools, and maintain visibility across teams with a platform
             designed to grow with you."

"frameworks, adapt", "visibility across" and "grow with you" were never in the input.
They are plausible, they are well-written, and they are **fabricated copy attributed to
someone else's product**.

This is the failure mode that matters most, precisely because the output looks flawless.
Nothing about the image signals which words are real.

## What this changes about curator

**The vision diff must check text fidelity specifically, not general similarity.** OCR
both images, and treat any string present in the output but absent from the input as a
defect — not a stylistic difference. Occluded regions are the highest-risk area and the
easiest for a model to "helpfully" complete.

Three rules follow:

1. **Never ask the model to reconstruct occluded content.** Crop the occlusion out, or
   ask the user for a clean capture. Filling a hole is inventing.
2. **OCR-diff every restyle.** New words are a rejection, not a note.
3. **Provenance stays on the asset.** `user_supplied` versus `generated` versus
   `restyled` — because a restyled screenshot is a claim about a real product, and a
   generated one is a claim about a product that may not exist.

## Verdict

§7's regeneration claim holds. The mechanism works well enough to ship — with a text-
fidelity gate in front of it, which is now clearly not optional.
