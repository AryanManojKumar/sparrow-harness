"""Binding a project must survive a Context switch.

`Run.advance` is a generator and the API streams it, so the Context that starts
a run is not the Context that resumes or closes it. A ContextVar token may only
be reset where it was created, and a real run produced:

    Error: <Token var=<ContextVar name='sparrow_project' …>> was created in a
    different Context

twice over — once from the `with` inside `advance`, once from ASGI middleware
whose `with` had already exited before the StreamingResponse body ran.
"""
from __future__ import annotations

import contextvars

from sparrow import telemetry


def test_bind_survives_being_read_from_another_context():
    telemetry.bind("p1")
    assert contextvars.copy_context().run(telemetry._project.get) == "p1"


def test_bind_returns_a_stable_trace_id_and_reuses_one():
    first = telemetry.bind("p1")
    assert telemetry.bind("p1") == first


def test_a_generator_bound_per_yield_labels_every_event():
    """What `_emit` does: re-bind before each line rather than span the yields."""
    def gen():
        for i in range(3):
            telemetry.bind("p2", stage=f"s{i}")
            yield telemetry._stage.get()

    # Each next() in its own Context, the way a streaming consumer resumes one.
    it = gen()
    seen = [contextvars.copy_context().run(lambda: next(it)) for _ in range(3)]
    assert seen == ["s0", "s1", "s2"]


def test_trace_does_not_raise_when_unwound_in_a_foreign_context():
    """The middleware case. A bookkeeping error must not replace a real one."""
    cm = telemetry.trace("p3")
    contextvars.copy_context().run(cm.__enter__)
    # Exiting here, where the tokens do not belong, used to raise ValueError.
    cm.__exit__(None, None, None)


def test_trace_still_unwinds_normally_in_its_own_context():
    telemetry.bind("outer")
    with telemetry.trace("inner"):
        assert telemetry._project.get() == "inner"
    assert telemetry._project.get() == "outer"
