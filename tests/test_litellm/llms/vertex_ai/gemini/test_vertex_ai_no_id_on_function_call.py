"""
Regression test: Vertex AI must NOT send `id` on FunctionCall / FunctionResponse.

The Google AI (gemini) API supports `id` on these proto messages, but the
Vertex AI v1 schema does not.  Sending `id` to Vertex AI causes:

    Unknown name "id" at 'contents[1].parts[1].function_call'

See: https://github.com/Simon-Stone/litellm/issues/XX
"""

import json
from typing import Optional

import pytest

from litellm.litellm_core_utils.prompt_templates.factory import (
    convert_to_gemini_tool_call_invoke,
    convert_to_gemini_tool_call_result,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_ASSISTANT_MSG_WITH_TOOL_CALLS = {
    "role": "assistant",
    "content": None,
    "tool_calls": [
        {
            "id": "call_abc123",
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": json.dumps({"location": "Boston"}),
            },
        }
    ],
}

_TOOL_RESULT_MSG = {
    "role": "tool",
    "tool_call_id": "call_abc123",
    "content": '{"temperature": 72}',
    "name": "get_weather",
}


# ---------------------------------------------------------------------------
# convert_to_gemini_tool_call_invoke
# ---------------------------------------------------------------------------


class TestToolCallInvokeIdForwarding:
    """Verify `id` on FunctionCall is provider-aware."""

    @pytest.mark.parametrize(
        "provider",
        ["vertex_ai", "vertex_ai_beta"],
    )
    def test_should_not_include_id_for_vertex_ai(self, provider: str):
        """Vertex AI does not accept `id` on FunctionCall."""
        parts = convert_to_gemini_tool_call_invoke(
            _ASSISTANT_MSG_WITH_TOOL_CALLS,  # type: ignore
            model="gemini-3.5-flash",
            custom_llm_provider=provider,
        )
        assert len(parts) == 1
        fc = parts[0]["function_call"]
        assert "id" not in fc

    def test_should_include_id_for_google_ai(self):
        """Google AI (gemini provider) supports `id` on FunctionCall."""
        parts = convert_to_gemini_tool_call_invoke(
            _ASSISTANT_MSG_WITH_TOOL_CALLS,  # type: ignore
            model="gemini-3.5-flash",
            custom_llm_provider="gemini",
        )
        assert len(parts) == 1
        fc = parts[0]["function_call"]
        assert fc.get("id") == "call_abc123"

    def test_should_not_include_id_when_provider_is_none(self):
        """Default (no provider) should not forward id."""
        parts = convert_to_gemini_tool_call_invoke(
            _ASSISTANT_MSG_WITH_TOOL_CALLS,  # type: ignore
            model="gemini-3.5-flash",
            custom_llm_provider=None,
        )
        assert len(parts) == 1
        fc = parts[0]["function_call"]
        assert "id" not in fc

    def test_should_not_include_id_for_non_gemini3_model(self):
        """Older models should never get `id`, even on Google AI."""
        parts = convert_to_gemini_tool_call_invoke(
            _ASSISTANT_MSG_WITH_TOOL_CALLS,  # type: ignore
            model="gemini-2.0-flash",
            custom_llm_provider="gemini",
        )
        assert len(parts) == 1
        fc = parts[0]["function_call"]
        assert "id" not in fc


# ---------------------------------------------------------------------------
# convert_to_gemini_tool_call_result
# ---------------------------------------------------------------------------


class TestToolCallResultIdForwarding:
    """Verify `id` on FunctionResponse is provider-aware."""

    @pytest.mark.parametrize(
        "provider",
        ["vertex_ai", "vertex_ai_beta"],
    )
    def test_should_not_include_id_for_vertex_ai(self, provider: str):
        """Vertex AI does not accept `id` on FunctionResponse."""
        result = convert_to_gemini_tool_call_result(
            _TOOL_RESULT_MSG,  # type: ignore
            last_message_with_tool_calls=_ASSISTANT_MSG_WITH_TOOL_CALLS,
            model="gemini-3.5-flash",
            custom_llm_provider=provider,
        )
        # result can be a single part or list of parts
        part = result[0] if isinstance(result, list) else result
        fr = part["function_response"]
        assert "id" not in fr

    def test_should_include_id_for_google_ai(self):
        """Google AI (gemini provider) supports `id` on FunctionResponse."""
        result = convert_to_gemini_tool_call_result(
            _TOOL_RESULT_MSG,  # type: ignore
            last_message_with_tool_calls=_ASSISTANT_MSG_WITH_TOOL_CALLS,
            model="gemini-3.5-flash",
            custom_llm_provider="gemini",
        )
        part = result[0] if isinstance(result, list) else result
        fr = part["function_response"]
        assert fr.get("id") == "call_abc123"

    def test_should_not_include_id_when_provider_is_none(self):
        """Default (no provider) should not forward id."""
        result = convert_to_gemini_tool_call_result(
            _TOOL_RESULT_MSG,  # type: ignore
            last_message_with_tool_calls=_ASSISTANT_MSG_WITH_TOOL_CALLS,
            model="gemini-3.5-flash",
            custom_llm_provider=None,
        )
        part = result[0] if isinstance(result, list) else result
        fr = part["function_response"]
        assert "id" not in fr
