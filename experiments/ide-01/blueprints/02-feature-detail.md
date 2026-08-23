# Blueprint: feature-detail
**File:** `src/components/sections/FeatureDetail.tsx`

Purpose: Show how the plugin architecture makes each coding-agent run inspectable and reviewable before changes enter the repository.

Slots: eyebrow · headline · body · mechanism_points[]

Assets:
- One product-interface capture showing the plugin or agent-run configuration that records a run against a shared repository plan.
- One product-interface capture showing the resulting trace alongside the proposed code diff and review checkpoint.

Structure: Use one compact feature-detail section led by the architectural principle “Everything is a plugin” and its consequence “Every run is traceable,” followed by explanatory copy of roughly the winner’s 258-word scale. Pair the copy with two concrete interface visuals: one for the plugin-based run mechanism and one for the traceable diff-review outcome, with mechanism_points[] explaining how the two connect. On mobile, stack the copy first and the visuals after it, preserving the architecture-to-review sequence without introducing numbered markers because this is an explanatory relationship rather than a user procedure. Do not include a CTA, testimonial, broad feature list, or generic product overview, since adjacent sections cover conversion, proof, and feature breadth.
