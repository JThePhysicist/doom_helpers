"""Phase 3: Generative Transfer.

Applies Doom pixel-art style, lighting and health-tier-driven damage to an
aligned headshot crop via Stable Diffusion 1.5 + ControlNet (structural
lock) + an IP-Adapter (style transfer from the original Doom reference
sprite). Prompt construction and control-image prep are pure functions so
they're unit-testable without the torch/diffusers/transformers stack
installed; only :class:`DoomFaceGenerator` (which actually runs the
diffusion pipeline) needs them, imported lazily.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from .parser import MAX_HEALTH_TIER, MIN_HEALTH_TIER

_BASE_PROMPT = (
    "pixel art doom status bar face portrait, 1993 retro FPS HUD sprite, "
    "id software house style, chunky shading"
)
_NEGATIVE_PROMPT = (
    "blurry, smooth gradient shading, photorealistic, 3d render, "
    "high resolution, anti-aliased, soft focus"
)

_TIER_DAMAGE_DESCRIPTORS: dict[int, str] = {
    0: "",
    1: "minor scuffs, light bruising",
    2: "bruised, dirty face, small cuts",
    3: "bloodied, cuts and gashes, sweat",
    4: "severe bleeding, open wounds, covered in blood",
}

# ControlNet model choice: the depth model needs a separate MiDaS
# depth-estimation pass. Canny locks facial structure just as well for this
# use case from a single deterministic cv2.Canny() call, so it's the
# default; the depth model id is kept below for anyone who wants to swap it.
CANNY_CONTROLNET_MODEL_ID = "lllyasviel/control_v11p_sd15_canny"
DEPTH_CONTROLNET_MODEL_ID = "lllyasviel/control_v11f1p_sd15_depth"


class InvalidHealthTierError(ValueError):
    """Raised when a health tier falls outside the Doom 0-4 range."""


class FaceStyleGenerator(Protocol):
    """Style-transfers an aligned headshot toward a Doom reference sprite's look."""

    def generate(
        self,
        aligned_image: NDArray[np.uint8],
        reference_sprite: NDArray[np.uint8],
        health_tier: int,
    ) -> Image.Image: ...


@dataclass(frozen=True, slots=True)
class GeneratorConfig:
    sd_model_id: str = "stable-diffusion-v1-5/stable-diffusion-v1-5"
    controlnet_model_id: str = CANNY_CONTROLNET_MODEL_ID
    ip_adapter_repo_id: str = "h94/IP-Adapter"
    ip_adapter_subfolder: str = "models"
    ip_adapter_weight_name: str = "ip-adapter_sd15.bin"
    ip_adapter_scale: float = 0.6
    controlnet_conditioning_scale: float = 0.8
    num_inference_steps: int = 30
    guidance_scale: float = 7.5
    canny_low_threshold: int = 100
    canny_high_threshold: int = 200
    seed: int | None = 0


def _validate_health_tier(health_tier: int) -> None:
    if not MIN_HEALTH_TIER <= health_tier <= MAX_HEALTH_TIER:
        raise InvalidHealthTierError(
            f"health_tier must be in [{MIN_HEALTH_TIER}, {MAX_HEALTH_TIER}], "
            f"got {health_tier}"
        )


def build_prompt(health_tier: int) -> str:
    """Build the SD1.5 text prompt for a given Doom health tier (0=healthy, 4=near death)."""
    _validate_health_tier(health_tier)
    descriptor = _TIER_DAMAGE_DESCRIPTORS[health_tier]
    if not descriptor:
        return _BASE_PROMPT
    return f"{_BASE_PROMPT}, {descriptor}"


def build_negative_prompt() -> str:
    return _NEGATIVE_PROMPT


def to_rgb_image(image: NDArray[np.uint8]) -> Image.Image:
    """Convert an RGB or RGBA numpy image array to a PIL RGB image."""
    return Image.fromarray(image).convert("RGB")


def build_control_image(
    aligned_image: NDArray[np.uint8],
    low_threshold: int = 100,
    high_threshold: int = 200,
) -> Image.Image:
    """Run Canny edge detection to build the ControlNet structural-lock image."""
    import cv2

    gray = cv2.cvtColor(aligned_image, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, low_threshold, high_threshold)
    return Image.fromarray(np.stack([edges] * 3, axis=-1))


class DoomFaceGenerator:
    """Stable Diffusion 1.5 + ControlNet + IP-Adapter style-transfer wrapper."""

    def __init__(self, config: GeneratorConfig | None = None) -> None:
        self._config = config or GeneratorConfig()
        self._pipeline: Any = None

    def _load_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline

        import torch
        from diffusers import ControlNetModel, StableDiffusionControlNetPipeline

        config = self._config
        controlnet = ControlNetModel.from_pretrained(
            config.controlnet_model_id, torch_dtype=torch.float16
        )
        pipeline = StableDiffusionControlNetPipeline.from_pretrained(
            config.sd_model_id,
            controlnet=controlnet,
            torch_dtype=torch.float16,
            safety_checker=None,
        )
        pipeline.load_ip_adapter(
            config.ip_adapter_repo_id,
            subfolder=config.ip_adapter_subfolder,
            weight_name=config.ip_adapter_weight_name,
        )
        pipeline.set_ip_adapter_scale(config.ip_adapter_scale)
        pipeline.enable_xformers_memory_efficient_attention()
        pipeline.enable_model_cpu_offload()

        self._pipeline = pipeline
        return pipeline

    def _make_generator(self) -> Any:
        if self._config.seed is None:
            return None
        import torch

        return torch.Generator().manual_seed(self._config.seed)

    def generate(
        self,
        aligned_image: NDArray[np.uint8],
        reference_sprite: NDArray[np.uint8],
        health_tier: int,
    ) -> Image.Image:
        """Style-transfer ``aligned_image`` toward ``reference_sprite``'s Doom look."""
        config = self._config
        prompt = build_prompt(health_tier)
        control_image = build_control_image(
            aligned_image, config.canny_low_threshold, config.canny_high_threshold
        )
        ip_adapter_image = to_rgb_image(reference_sprite)

        pipeline = self._load_pipeline()
        result = pipeline(
            prompt=prompt,
            negative_prompt=_NEGATIVE_PROMPT,
            image=control_image,
            ip_adapter_image=ip_adapter_image,
            num_inference_steps=config.num_inference_steps,
            guidance_scale=config.guidance_scale,
            controlnet_conditioning_scale=config.controlnet_conditioning_scale,
            generator=self._make_generator(),
        )
        image: Image.Image = result.images[0]
        return image
