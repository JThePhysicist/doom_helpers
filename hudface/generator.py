from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    import numpy as np
    from diffusers import StableDiffusionControlNetPipeline
    from transformers import Pipeline as HFPipeline

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

# health_tier: 0 = healthiest .. 4 = most wounded.
_HEALTH_TIER_SUFFIXES = {
    0: "",
    1: "light bruising, minor scrapes",
    2: "bruised and bloodied, cuts on face",
    3: "heavily wounded, blood streaks, swollen bruises",
    4: "severe bleeding, open wounds, covered in blood",
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


def build_prompt(health_tier: int, expression: str) -> str:
    """Deterministically build the SD prompt for a given health tier/expression."""
    if expression not in _EXPRESSION_PROMPTS:
        raise ValueError(f"Unknown expression: {expression!r}")
    if health_tier not in _HEALTH_TIER_SUFFIXES:
        raise ValueError(f"Unknown health tier: {health_tier!r}")

    parts = [_BASE_STYLE, _EXPRESSION_PROMPTS[expression]]
    suffix = _HEALTH_TIER_SUFFIXES[health_tier]
    if suffix:
        parts.append(suffix)
    return ", ".join(parts)


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
) -> Image.Image:
    """Apply Doom pixel-art style transfer + damage to an aligned face crop.

    `aligned_image` is the geometry-validated face crop (Phase 2 output),
    `reference_sprite` is the original Doom STF sprite for this target
    (used as the IP-Adapter style reference), and the prompt is built
    deterministically from `health_tier`/`expression`.
    """
    pipeline = _load_pipeline()
    depth_estimator = _load_depth_estimator()

    face_image = Image.fromarray(aligned_image)
    style_image = Image.fromarray(reference_sprite)
    control_image = depth_estimator(face_image)["depth"]

    pipeline.set_ip_adapter_scale(_IP_ADAPTER_SCALE)
    result = pipeline(
        prompt=build_prompt(health_tier, expression),
        negative_prompt=NEGATIVE_PROMPT,
        image=control_image,
        ip_adapter_image=style_image,
        num_inference_steps=_NUM_INFERENCE_STEPS,
    )
    generated: Image.Image = result.images[0]
    return generated
