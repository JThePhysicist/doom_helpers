import pytest

from hudface.generator import build_prompt


def test_healthy_tier_zero_has_no_damage_suffix():
    prompt = build_prompt(0, "ST")
    assert "bleeding" not in prompt
    assert "calm determined expression" in prompt


def test_tier_four_appends_severe_bleeding():
    prompt = build_prompt(4, "ST")
    assert "severe bleeding, open wounds, covered in blood" in prompt


def test_ouch_expression_included_in_prompt():
    prompt = build_prompt(2, "OUCH")
    assert "wincing in pain" in prompt
    assert "bruised and bloodied, cuts on face" in prompt


def test_every_known_expression_builds_without_error():
    for expression in ["ST", "OUCH", "EVL", "KILL", "GOD", "DEAD", "TL", "TR"]:
        for tier in range(5):
            assert build_prompt(tier, expression)


def test_unknown_expression_raises_value_error():
    with pytest.raises(ValueError):
        build_prompt(0, "NOPE")


def test_unknown_health_tier_raises_value_error():
    with pytest.raises(ValueError):
        build_prompt(9, "ST")
