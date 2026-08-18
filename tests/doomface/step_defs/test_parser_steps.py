from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from doomface.parser import GazeDirection, InvalidStfNameError, parse_stf_filename

FEATURE_FILE = Path(__file__).parent.parent / "features" / "parser.feature"
scenarios(str(FEATURE_FILE))


@pytest.fixture
def context() -> dict[str, Any]:
    return {}


@when(parsers.parse('I parse the filename "{filename}"'))
def parse_filename(context: dict[str, Any], filename: str) -> None:
    try:
        context["state"] = parse_stf_filename(filename)
    except InvalidStfNameError as exc:
        context["error"] = exc


@then(parsers.parse('the expression is "{expression}"'))
def check_expression(context: dict[str, Any], expression: str) -> None:
    assert context["state"].expression == expression


@then(parsers.parse("the health tier is {tier:d}"))
def check_health_tier(context: dict[str, Any], tier: int) -> None:
    assert context["state"].health_tier == tier


@then(parsers.parse('the gaze direction is "{gaze}"'))
def check_gaze_direction(context: dict[str, Any], gaze: str) -> None:
    assert context["state"].gaze_direction == GazeDirection[gaze]


@then("parsing raises an invalid name error")
def check_invalid_name_error(context: dict[str, Any]) -> None:
    assert isinstance(context.get("error"), InvalidStfNameError)
