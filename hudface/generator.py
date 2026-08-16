from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    import numpy as np
    from diffusers import StableDiffusionControlNetPipeline
    from transformers import Pipeline as HFPipeline

# Every knob below is a 0-4 dial, matching the STF grid's own 5-tier scale.
_LEVELS = range(5)

NEGATIVE_PROMPT = "blurry, photographic, realistic skin texture, smooth gradients, 3d render"

_BASE_STYLE = "pixel art doom status bar face, 1993 id software doom engine style, retro pixelated"

_EXPRESSION_PROMPTS = {
    "ST": "calm determined expression, forward-facing",
    "OUCH": "wincing in pain, mouth open in a grimace",
    "EVL": "sinister evil grin, picked up a powerful weapon",
    "KILL": "berserker rage, feral snarling scowl",
    "GOD": "glowing golden aura, invulnerable, serene expression",
    "DEAD": "lifeless expression, eyes rolled back",
    "TL": "glancing to the side",
    "TR": "glancing to the side",
}

# wound_intensity: 0 = unhurt .. 4 = most wounded. Defaults to health_tier
# (Doom's own tier for this frame) unless the caller overrides it.
_WOUND_INTENSITY_PHRASES = {
    0: "",
    1: "light bruising, minor scrapes",
    2: "bruised and bloodied, cuts on face",
    3: "heavily wounded, blood streaks, swollen bruises",
    4: "severe bleeding, open wounds, covered in blood",
}

# gore_level: how graphic the wound wording gets, independent of *how much*
# wound_intensity says is there. Only applied when there's a wound phrase.
_GORE_MODIFIERS = {
    0: "clean, tasteful,",
    1: "mild,",
    2: "",
    3: "graphic, visceral,",
    4: "extremely graphic, gruesome, dismemberment-level gore,",
}

# Extra negative-prompt suppression for the low end of gore_level, since the
# depth ControlNet + IP-Adapter conditioning can still push blood/gore even
# when the positive prompt doesn't ask for it.
_GORE_SUPPRESSION = {
    0: "blood, gore, wounds, graphic violence",
    1: "excessive gore, dismemberment",
}

# tiredness: 0 = fresh .. 4 = utterly exhausted. Independent of health_tier
# and applied uniformly across the whole sprite set.
_TIREDNESS_PHRASES = {
    0: "",
    1: "slightly tired",
    2: "exhausted, dark circles under eyes",
    3: "haggard, sunken eyes, sweat-drenched",
    4: "utterly exhausted, bloodshot eyes, gaunt haggard face",
}

_DEPTH_MODEL = "Intel/dpt-hybrid-midas"
_CONTROLNET_MODEL = "lllyasviel/control_v11f1p_sd15_depth"
_SD_MODEL = "runwayml/stable-diffusion-v1-5"
_IP_ADAPTER_REPO = "h94/IP-Adapter"
_IP_ADAPTER_WEIGHT = "ip-adapter_sd15.bin"
_IP_ADAPTER_SCALE = 0.6
_NUM_INFERENCE_STEPS = 30

_pipeline_singleton: "StableDiffusionControlNetPipeline | None" = None
_depth_estimator_singleton: "HFPipeline | None" = None


@dataclass(frozen=True)
class StyleKnobs:
    """User-facing dials for how wounded/tired/gory generated faces look.

    `wound_intensity` defaults to the frame's own `health_tier` (Doom's
    5-tier damage grid) when left as None; set it explicitly to decouple
    how bloody a frame looks from which health tier it actually is.
    `tiredness` and `gore_level` have no Doom-native equivalent and apply
    uniformly across a whole sprite-set run.
    """

    wound_intensity: int | None = None
    tiredness: int = 0
    gore_level: int = 2


def _validate_level(name: str, value: int) -> None:
    if value not in _LEVELS:
        raise ValueError(f"{name} must be 0-4, got {value!r}")


def _wound_phrase(health_tier: int, knobs: StyleKnobs) -> str:
    wound_intensity = knobs.wound_intensity if knobs.wound_intensity is not None else health_tier
    _validate_level("wound_intensity", wound_intensity)

    base = _WOUND_INTENSITY_PHRASES[wound_intensity]
    if not base:
        return ""
    gore_modifier = _GORE_MODIFIERS[knobs.gore_level]
    return f"{gore_modifier} {base}".strip() if gore_modifier else base


def build_prompt(health_tier: int, expression: str, knobs: StyleKnobs | None = None) -> str:
    """Deterministically build the SD prompt for a health tier/expression,
    modulated by `knobs` (wound_intensity/tiredness/gore_level)."""
    if expression not in _EXPRESSION_PROMPTS:
        raise ValueError(f"Unknown expression: {expression!r}")
    if health_tier not in _WOUND_INTENSITY_PHRASES:
        raise ValueError(f"Unknown health tier: {health_tier!r}")
    knobs = knobs or StyleKnobs()
    _validate_level("gore_level", knobs.gore_level)
    _validate_level("tiredness", knobs.tiredness)

    parts = [_BASE_STYLE, _EXPRESSION_PROMPTS[expression]]

    wound = _wound_phrase(health_tier, knobs)
    if wound:
        parts.append(wound)

    tiredness = _TIREDNESS_PHRASES[knobs.tiredness]
    if tiredness:
        parts.append(tiredness)

    return ", ".join(parts)


def build_negative_prompt(knobs: StyleKnobs | None = None) -> str:
    """Negative prompt, strengthened with extra gore suppression at the low
    end of gore_level (the model can still add blood without being asked)."""
    knobs = knobs or StyleKnobs()
    _validate_level("gore_level", knobs.gore_level)

    suppression = _GORE_SUPPRESSION.get(knobs.gore_level)
    if suppression:
        return f"{NEGATIVE_PROMPT}, {suppression}"
    return NEGATIVE_PROMPT


def _load_pipeline() -> "StableDiffusionControlNetPipeline":
    global _pipeline_singleton
    if _pipeline_singleton is not None:
        return _pipeline_singleton

    import torch
    from diffusers import ControlNetModel, StableDiffusionControlNetPipeline

    controlnet = ControlNetModel.from_pretrained(_CONTROLNET_MODEL, torch_dtype=torch.float16)
    pipeline = StableDiffusionControlNetPipeline.from_pretrained(
        _SD_MODEL, controlnet=controlnet, torch_dtype=torch.float16
    )
    pipeline.load_ip_adapter(_IP_ADAPTER_REPO, subfolder="models", weight_name=_IP_ADAPTER_WEIGHT)
    pipeline.enable_xformers_memory_efficient_attention()
    pipeline.enable_model_cpu_offload()

    _pipeline_singleton = pipeline
    return pipeline


def _load_depth_estimator() -> "HFPipeline":
    global _depth_estimator_singleton
    if _depth_estimator_singleton is not None:
        return _depth_estimator_singleton

    from transformers import pipeline as hf_pipeline

    _depth_estimator_singleton = hf_pipeline("depth-estimation", model=_DEPTH_MODEL)
    return _depth_estimator_singleton


def generate(
    aligned_image: "np.ndarray",
    reference_sprite: "np.ndarray",
    health_tier: int,
    expression: str,
    knobs: StyleKnobs | None = None,
) -> Image.Image:
    """Apply Doom pixel-art style transfer + damage to an aligned face crop.

    `aligned_image` is the geometry-validated face crop (Phase 2 output),
    `reference_sprite` is the original Doom STF sprite for this target
    (used as the IP-Adapter style reference), and the prompt is built
    deterministically from `health_tier`/`expression`/`knobs`.
    """
    pipeline = _load_pipeline()
    depth_estimator = _load_depth_estimator()

    face_image = Image.fromarray(aligned_image)
    style_image = Image.fromarray(reference_sprite)
    control_image = depth_estimator(face_image)["depth"]

    pipeline.set_ip_adapter_scale(_IP_ADAPTER_SCALE)
    result = pipeline(
        prompt=build_prompt(health_tier, expression, knobs),
        negative_prompt=build_negative_prompt(knobs),
        image=control_image,
        ip_adapter_image=style_image,
        num_inference_steps=_NUM_INFERENCE_STEPS,
    )
    generated: Image.Image = result.images[0]
    return generated
