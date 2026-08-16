from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

GAZE_CENTER = 0
GAZE_RIGHT = 1
GAZE_LEFT = 2

_HEALTH_TIERS = "01234"


@dataclass(frozen=True)
class FaceState:
    expression: str
    health_tier: int
    gaze_direction: int


def _look_to_gaze(look: int) -> int:
    if look == 0:
        return GAZE_CENTER
    return GAZE_RIGHT if look % 2 == 1 else GAZE_LEFT


def _main_grid_state(match: re.Match[str]) -> FaceState:
    return FaceState(
        expression="ST",
        health_tier=int(match.group("tier")),
        gaze_direction=_look_to_gaze(int(match.group("look"))),
    )


def _tiered_state(expression: str) -> Callable[[re.Match[str]], FaceState]:
    def build(match: re.Match[str]) -> FaceState:
        return FaceState(
            expression=expression, health_tier=int(match.group("tier")), gaze_direction=GAZE_CENTER
        )

    return build


def _fixed_state(expression: str, gaze_direction: int = GAZE_CENTER) -> Callable[[re.Match[str]], FaceState]:
    def build(_match: re.Match[str]) -> FaceState:
        return FaceState(expression=expression, health_tier=0, gaze_direction=gaze_direction)

    return build


# The 1993 Doom STF status-bar face lumps break down into a handful of
# fixed families, tried in order against the filename stem (the STF
# lump/filename without extension or the leading "STF"). Doom itself
# encodes 5 "look" values (0-4: straight x3, turned x2) per health tier for
# the main grid -- this pipeline only needs a 3-way gaze_direction, so look
# values collapse deterministically: 0 -> Center, odd looks (1, 3) ->
# Right, even non-zero looks (2, 4) -> Left.
_PATTERNS: list[tuple[re.Pattern[str], Callable[[re.Match[str]], FaceState]]] = [
    (re.compile(rf"^ST(?P<tier>[{_HEALTH_TIERS}])(?P<look>[0-4])$"), _main_grid_state),
    (re.compile(r"^TR00$"), _fixed_state("TR", GAZE_RIGHT)),
    (re.compile(r"^TL00$"), _fixed_state("TL", GAZE_LEFT)),
    (re.compile(rf"^OUCH(?P<tier>[{_HEALTH_TIERS}])$"), _tiered_state("OUCH")),
    (re.compile(rf"^EVL(?P<tier>[{_HEALTH_TIERS}])$"), _tiered_state("EVL")),
    (re.compile(rf"^KILL(?P<tier>[{_HEALTH_TIERS}])$"), _tiered_state("KILL")),
    (re.compile(r"^GOD0$"), _fixed_state("GOD")),
    (re.compile(r"^DEAD0$"), _fixed_state("DEAD")),
]


def parse_stf_filename(filename: str) -> FaceState:
    """Parse a Doom STF status-bar face filename (e.g. "STFST21.png").

    Deterministic table lookup over the fixed 44-lump 1993 naming
    convention. Raises ValueError for anything that isn't a real STF name.
    """
    stem = filename.rsplit("/", 1)[-1]
    if "." in stem:
        stem = stem.rsplit(".", 1)[0]

    if not stem.startswith("STF"):
        raise ValueError(f"Not a Doom STF face filename: {filename!r}")
    code = stem[3:]

    for pattern, build_state in _PATTERNS:
        match = pattern.match(code)
        if match:
            return build_state(match)

    raise ValueError(f"Not a Doom STF face filename: {filename!r}")
