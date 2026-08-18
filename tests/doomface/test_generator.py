from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from doomface.generator import (
    DoomFaceGenerator,
    GeneratorConfig,
    InvalidHealthTierError,
    build_control_image,
    build_negative_prompt,
    build_prompt,
    to_rgb_image,
)


def _solid_image(width: int = 40, height: int = 40, channels: int = 3) -> np.ndarray:
    shape = (height, width, channels)
    return np.full(shape, 128, dtype=np.uint8)


def test_build_prompt_healthy_tier_has_no_damage_descriptor() -> None:
    prompt = build_prompt(0)
    assert "doom" in prompt.lower()
    assert "blood" not in prompt.lower()


def test_build_prompt_worst_tier_mentions_severe_bleeding() -> None:
    prompt = build_prompt(4)
    assert "severe bleeding" in prompt
    assert "open wounds" in prompt
    assert "covered in blood" in prompt


@pytest.mark.parametrize("tier", [0, 1, 2, 3, 4])
def test_build_prompt_accepts_every_valid_tier(tier: int) -> None:
    assert build_prompt(tier)  # non-empty for every valid tier


@pytest.mark.parametrize("tier", [-1, 5, 100])
def test_build_prompt_rejects_out_of_range_tier(tier: int) -> None:
    with pytest.raises(InvalidHealthTierError):
        build_prompt(tier)


def test_build_negative_prompt_is_stable() -> None:
    assert build_negative_prompt() == build_negative_prompt()
    assert "blurry" in build_negative_prompt()


def test_to_rgb_image_from_rgb_array() -> None:
    image = to_rgb_image(_solid_image(channels=3))
    assert image.mode == "RGB"
    assert image.size == (40, 40)


def test_to_rgb_image_from_rgba_array_drops_alpha() -> None:
    image = to_rgb_image(_solid_image(channels=4))
    assert image.mode == "RGB"


def test_build_control_image_returns_three_channel_edge_map() -> None:
    source = _solid_image(width=32, height=24, channels=3)
    source[:, 16:] = 255  # a hard edge down the middle

    control = build_control_image(source)

    assert isinstance(control, Image.Image)
    assert control.size == (32, 24)
    assert control.mode == "RGB"


def test_generator_construction_does_not_require_torch() -> None:
    # torch/diffusers are not installed in this environment; constructing
    # the wrapper must stay lazy and not import them.
    generator = DoomFaceGenerator(GeneratorConfig(seed=42))
    assert generator._pipeline is None


def test_load_pipeline_raises_clearly_without_torch_installed() -> None:
    generator = DoomFaceGenerator()
    with pytest.raises(ModuleNotFoundError):
        generator._load_pipeline()
