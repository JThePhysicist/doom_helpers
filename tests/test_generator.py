import pytest

from hudface.generator import NEGATIVE_PROMPT, StyleKnobs, build_negative_prompt, build_prompt


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


def test_wound_intensity_defaults_to_health_tier_when_not_overridden():
    # health_tier=0 with no knobs override -> no wound wording at all.
    assert build_prompt(0, "ST") == build_prompt(0, "ST", StyleKnobs())


def test_wound_intensity_override_decouples_from_health_tier():
    # A healthy (tier 0) frame explicitly dialed up to wound_intensity=4
    # should read as wounded even though its Doom health tier says fine.
    prompt = build_prompt(0, "ST", StyleKnobs(wound_intensity=4))
    assert "severe bleeding, open wounds, covered in blood" in prompt

    # And a badly hurt (tier 4) frame explicitly dialed down to 0 should
    # show no wound wording despite its Doom health tier.
    prompt = build_prompt(4, "ST", StyleKnobs(wound_intensity=0))
    assert "bleeding" not in prompt
    assert "wound" not in prompt


def test_gore_level_only_modifies_wording_when_there_is_a_wound():
    # No wound at all (tier 0, no override) -> gore_level has nothing to modify.
    low = build_prompt(0, "ST", StyleKnobs(gore_level=0))
    high = build_prompt(0, "ST", StyleKnobs(gore_level=4))
    assert low == high


def test_gore_level_scales_the_wound_wording_graphic_ness():
    clean = build_prompt(4, "ST", StyleKnobs(gore_level=0))
    moderate = build_prompt(4, "ST", StyleKnobs(gore_level=2))
    extreme = build_prompt(4, "ST", StyleKnobs(gore_level=4))

    assert "clean, tasteful" in clean
    assert "clean, tasteful" not in moderate
    assert "extremely graphic, gruesome, dismemberment-level gore" in extreme
    assert clean != moderate != extreme


def test_tiredness_is_independent_of_health_tier_and_wound_intensity():
    prompt = build_prompt(0, "ST", StyleKnobs(tiredness=4))
    assert "utterly exhausted" in prompt
    assert "bleeding" not in prompt  # unaffected by tiredness


def test_tiredness_zero_adds_no_wording():
    assert build_prompt(0, "ST", StyleKnobs(tiredness=0)) == build_prompt(0, "ST")


def test_out_of_range_gore_level_raises_value_error():
    with pytest.raises(ValueError):
        build_prompt(0, "ST", StyleKnobs(gore_level=5))


def test_out_of_range_tiredness_raises_value_error():
    with pytest.raises(ValueError):
        build_prompt(0, "ST", StyleKnobs(tiredness=-1))


def test_out_of_range_wound_intensity_override_raises_value_error():
    with pytest.raises(ValueError):
        build_prompt(0, "ST", StyleKnobs(wound_intensity=7))


def test_build_negative_prompt_default_is_the_base_negative_prompt():
    assert build_negative_prompt() == NEGATIVE_PROMPT
    assert build_negative_prompt(StyleKnobs()) == NEGATIVE_PROMPT


def test_build_negative_prompt_suppresses_gore_at_low_gore_levels():
    assert "blood, gore, wounds" in build_negative_prompt(StyleKnobs(gore_level=0))
    assert "excessive gore, dismemberment" in build_negative_prompt(StyleKnobs(gore_level=1))


def test_build_negative_prompt_unmodified_at_moderate_and_high_gore_levels():
    for level in (2, 3, 4):
        assert build_negative_prompt(StyleKnobs(gore_level=level)) == NEGATIVE_PROMPT


def test_build_negative_prompt_rejects_out_of_range_gore_level():
    with pytest.raises(ValueError):
        build_negative_prompt(StyleKnobs(gore_level=5))
