"""The workshop: where model-written code runs, kept apart from the office.

The office (`sparrow.api`) holds everything worth stealing — provider keys,
the blackboards, the harness code itself. The workshop holds the generated
websites and nothing else, and it is the only place the editing agent and
`next build` ever run. If the agent escapes its jail it finds other websites,
not keys.

Two boundaries, because one is a promise and the other is a wall:

  * Machine. In production the workshop is a separate host that can reach the
    office on one port — the LLM gateway — and is reachable only from the
    office. In development it is a second process on the same machine, talking
    over localhost through the same HTTP contract, so moving it is a config
    change and not a rewrite.
  * Jail. Every agent session and every build runs inside bubblewrap with a
    view of one project's workspace, read-only system directories, and a
    private /tmp. DeepSeek Harness confines writes on its own; reads and
    environment are what the jail adds (measured in the spike: without it the
    agent read files outside its workspace freely).

The workshop never holds a provider key. The agent reaches a model through the
office's gateway with a short-lived per-project token (`sparrow.gateway`).
"""
