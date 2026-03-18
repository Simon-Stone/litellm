"""
Cost calculator for OpenAI image generation models (gpt-image family)

These models use token-based pricing instead of pixel-based pricing like DALL-E.
"""

from typing import Final

import litellm
from litellm import verbose_logger
from litellm.litellm_core_utils.llm_cost_calc.utils import (
    calculate_image_response_cost_from_usage,
    generic_cost_per_token,
)
from litellm.types.utils import ImageResponse, Usage


def _pricing_model(model: str, router_model_id: str | None) -> str:
    """
    The model whose cost-map entry prices this image response.

    A router deployment UUID registered in litellm.model_cost with actual
    pricing wins, so custom output_cost_per_image_token (and other overrides)
    are applied. A UUID entry without pricing (the Router registers one for
    every deployment) falls back to the regular model name.
    """
    if router_model_id is None or router_model_id == model:
        return model
    entry: Final = litellm.model_cost.get(router_model_id)
    if isinstance(entry, dict) and (
        entry.get("input_cost_per_token") is not None
        or entry.get("output_cost_per_token") is not None
        or entry.get("output_cost_per_image_token") is not None
        or entry.get("input_cost_per_second") is not None
        or entry.get("tiered_pricing") is not None
    ):
        return router_model_id
    return model


def cost_calculator(
    model: str,
    image_response: ImageResponse,
    custom_llm_provider: str | None = None,
    router_model_id: str | None = None,
) -> float:
    """Calculate cost for OpenAI gpt-image models (token-based pricing)."""
    usage: Final = getattr(image_response, "usage", None)
    if usage is None:
        verbose_logger.debug("No usage data available for %s, cannot calculate token-based cost", model)
        return 0.0

    provider: Final = custom_llm_provider or "openai"

    pricing_model: Final = _pricing_model(model=model, router_model_id=router_model_id)

    # A chat Usage with an explicit output breakdown: cost via generic_cost_per_token.
    if isinstance(usage, Usage) and usage.completion_tokens_details is not None:
        prompt_cost, completion_cost = generic_cost_per_token(
            model=pricing_model, usage=usage, custom_llm_provider=provider
        )
        return prompt_cost + completion_cost

    # ImageUsage / ResponseAPIUsage: reuse the shared helper (same path as
    # azure_ai/gemini/vertex_ai). It prices generated output tokens at
    # output_cost_per_image_token, classifying them as image tokens when the provider
    # does not itemize output and splitting text/image when it does.
    if getattr(usage, "input_tokens", None) is not None:
        token_based_cost: Final = calculate_image_response_cost_from_usage(
            model=pricing_model, image_response=image_response, custom_llm_provider=provider
        )
        if token_based_cost is not None:
            return token_based_cost

    # Fallback: a Usage with no output breakdown that the image helper can't read —
    # cost via generic_cost_per_token (text rate) instead of returning 0.0.
    if isinstance(usage, Usage):
        prompt_cost, completion_cost = generic_cost_per_token(
            model=pricing_model, usage=usage, custom_llm_provider=provider
        )
        return prompt_cost + completion_cost

    return 0.0
