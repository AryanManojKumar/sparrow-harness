"""Reading one JSON object out of a model's reply.

Every agent asked for "JSON only, no prose" and every agent then located it with
`re.compile(r"\\{.*\\}", re.DOTALL)`. That regex is greedy: it spans the FIRST
opening brace to the LAST closing one. While the reply holds exactly one object
this is the right answer and looks like a solved problem. The moment a model
emits a second object, or a sentence after the JSON that happens to contain a
brace, the captured span is `{...}...{...}` — and `json.loads` reports "Extra
data: line 1 column 1326", which names a column in a string nobody printed and
says nothing about a run that has just lost its content stage.

`raw_decode` is the fix and is in the standard library: it parses one complete
value from a position and reports where it stopped, so trailing anything is
simply not read.
"""

from __future__ import annotations

import json

_DECODER = json.JSONDecoder()


def first_object(text: str, *, what: str = "response") -> dict:
    """The first complete JSON object in `text`.

    Scans for a `{` that begins a decodable object rather than assuming the
    first one does: a reply that opens with prose containing a brace would
    otherwise fail on a character that was never meant to be JSON.
    """
    i = text.find("{")
    while i != -1:
        try:
            value, _ = _DECODER.raw_decode(text, i)
        except json.JSONDecodeError:
            i = text.find("{", i + 1)
            continue
        if isinstance(value, dict):
            return value
        i = text.find("{", i + 1)
    raise ValueError(f"no JSON object in {what}: {text[:200]!r}")
