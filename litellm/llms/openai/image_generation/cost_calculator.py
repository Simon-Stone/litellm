"""
OpenAI Image Generation Cost Calculator
"""

from typing import Any

import litellm
from litellm.types.utils import ImageResponse


def cost_calculator(
    model: str,
    image_response: ImageResponse,
) -> float:
    """
    OpenAI Image Generation Cost Calculator
    """
    _model_info = litellm.get_model_info(
        model=model,
        custom_llm_provider="openai",
    )

    input_cost_text: float = (
        _model_info.get("input_cost_per_token", 0.0)
        * image_response.usage.model_extra["input_tokens_details"]["text_tokens"]
    )

    input_cost_image: float = (
        _model_info.get("input_cost_per_image_token", 0.0)
        * image_response.usage.model_extra["input_tokens_details"]["image_tokens"]
    )

    input_cost = input_cost_text + input_cost_image

    output_cost: float = (
        _model_info.get("output_cost_per_token", 0.0)
        * image_response.usage.model_extra["output_tokens"]
    )

    return input_cost + output_cost
