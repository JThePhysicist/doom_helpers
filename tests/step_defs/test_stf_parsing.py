from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from hudface.parser import FaceState, parse_stf_filename

scenarios("stf_parsing.feature")


@pytest.fixture
def parse_result() -> dict[str, object]:
    return {}


@when(parsers.parse('I parse the STF filename "{filename}"'), target_fixture="parse_result")
def _parse_valid_filename(filename: str) -> dict[str, object]:
    return {"state": parse_stf_filename(filename)}


@when(
    parsers.parse('I try to parse the invalid STF filename "{filename}"'),
    target_fixture="parse_result",
)
def _parse_invalid_filename(filename: str) -> dict[str, object]:
    try:
        parse_stf_filename(filename)
    except ValueError as exc:
        return {"error": exc}
    raise AssertionError(f"Expected ValueError parsing {filename!r}")


@then(parsers.parse('the expression should be "{expression}"'))
def _check_expression(parse_result: dict[str, object], expression: str) -> None:
    state = parse_result["state"]
    assert isinstance(state, FaceState)
    assert state.expression == expression


@then(parsers.parse("the health tier should be {tier:d}"))
def _check_health_tier(parse_result: dict[str, object], tier: int) -> None:
    state = parse_result["state"]
    assert isinstance(state, FaceState)
    assert state.health_tier == tier


@then(parsers.parse("the gaze direction should be {gaze:d}"))
def _check_gaze_direction(parse_result: dict[str, object], gaze: int) -> None:
    state = parse_result["state"]
    assert isinstance(state, FaceState)
    assert state.gaze_direction == gaze


@then("parsing should raise a ValueError")
def _check_value_error(parse_result: dict[str, object]) -> None:
    assert isinstance(parse_result.get("error"), ValueError)
