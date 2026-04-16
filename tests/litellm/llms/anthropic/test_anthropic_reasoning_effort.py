"""
Tests for _map_reasoning_effort in AnthropicConfig.

Verifies that reasoning_effort=None returns None for all models,
including Claude Opus 4.6, and that Claude 4.7 models use adaptive
thinking with display='summarized' and no budget_tokens.
"""

import pytest

from litellm.llms.anthropic.chat.transformation import AnthropicConfig


class TestMapReasoningEffort:
    def test_none_returns_none_for_opus_4_6(self):
        """reasoning_effort=None should return None for Opus 4.6, not adaptive."""
        result = AnthropicConfig._map_reasoning_effort(
            reasoning_effort=None, model="claude-opus-4-6"
        )
        assert result is None

    def test_none_returns_none_for_other_models(self):
        """reasoning_effort=None should return None for non-Opus models."""
        result = AnthropicConfig._map_reasoning_effort(
            reasoning_effort=None, model="claude-4-sonnet-20250514"
        )
        assert result is None

    def test_opus_4_6_returns_adaptive_for_low(self):
        result = AnthropicConfig._map_reasoning_effort(
            reasoning_effort="low", model="claude-opus-4-6"
        )
        assert result["type"] == "adaptive"

    def test_opus_4_6_returns_adaptive_for_high(self):
        result = AnthropicConfig._map_reasoning_effort(
            reasoning_effort="high", model="claude-opus-4-6"
        )
        assert result["type"] == "adaptive"

    def test_other_model_low_returns_enabled_with_budget(self):
        result = AnthropicConfig._map_reasoning_effort(
            reasoning_effort="low", model="claude-4-sonnet-20250514"
        )
        assert result["type"] == "enabled"
        assert "budget_tokens" in result

    def test_other_model_high_returns_enabled_with_budget(self):
        result = AnthropicConfig._map_reasoning_effort(
            reasoning_effort="high", model="claude-4-sonnet-20250514"
        )
        assert result["type"] == "enabled"
        assert "budget_tokens" in result

    def test_none_string_returns_none_for_opus_4_6(self):
        """reasoning_effort='none' should return None for Opus 4.6."""
        result = AnthropicConfig._map_reasoning_effort(
            reasoning_effort="none", model="claude-opus-4-6"
        )
        assert result is None

    def test_none_string_returns_none_for_other_models(self):
        """reasoning_effort='none' should return None for non-Opus models."""
        result = AnthropicConfig._map_reasoning_effort(
            reasoning_effort="none", model="claude-4-sonnet-20250514"
        )
        assert result is None


class TestClaude47ModelDetection:
    """Tests for _is_claude_4_7_model static method."""

    @pytest.mark.parametrize(
        "model",
        [
            "claude-opus-4-7",
            "claude-opus-4.7",
            "claude-opus_4_7",
            "claude-opus_4.7",
            "anthropic/claude-opus-4-7",
            "claude-sonnet-4-7",
            "claude-sonnet-4.7",
            "claude-sonnet_4_7",
            "claude-sonnet_4.7",
        ],
    )
    def test_should_detect_claude_4_7_models(self, model):
        assert AnthropicConfig._is_claude_4_7_model(model) is True

    @pytest.mark.parametrize(
        "model",
        [
            "claude-opus-4-6",
            "claude-sonnet-4-6",
            "claude-4-sonnet-20250514",
            "claude-opus-4-5",
            "claude-sonnet-4-5",
        ],
    )
    def test_should_not_detect_non_4_7_models(self, model):
        assert AnthropicConfig._is_claude_4_7_model(model) is False

    def test_should_detect_4_7_as_4_6_plus(self):
        """_is_claude_4_6_model is a '4.6+' check that should also match 4.7."""
        assert AnthropicConfig._is_claude_4_6_model("claude-opus-4-7") is True
        assert AnthropicConfig._is_claude_4_6_model("claude-sonnet-4-7") is True


class TestClaude47ReasoningEffort:
    """Tests for Claude 4.7 breaking changes in _map_reasoning_effort."""

    def test_should_return_adaptive_with_display_summarized(self):
        """Claude 4.7 must use type='adaptive' with display='summarized'."""
        result = AnthropicConfig._map_reasoning_effort(
            reasoning_effort="high", model="claude-opus-4-7"
        )
        assert result is not None
        assert result["type"] == "adaptive"
        assert result.get("display") == "summarized"

    def test_should_not_include_budget_tokens(self):
        """Claude 4.7 must not include budget_tokens."""
        result = AnthropicConfig._map_reasoning_effort(
            reasoning_effort="high", model="claude-opus-4-7"
        )
        assert "budget_tokens" not in result

    @pytest.mark.parametrize("effort", ["low", "medium", "high"])
    def test_should_return_adaptive_for_all_effort_levels(self, effort):
        """All effort levels should produce adaptive thinking for 4.7."""
        result = AnthropicConfig._map_reasoning_effort(
            reasoning_effort=effort, model="claude-opus-4-7"
        )
        assert result["type"] == "adaptive"
        assert result.get("display") == "summarized"
        assert "budget_tokens" not in result

    def test_should_return_none_for_none_effort(self):
        """reasoning_effort=None should return None for 4.7 models."""
        result = AnthropicConfig._map_reasoning_effort(
            reasoning_effort=None, model="claude-opus-4-7"
        )
        assert result is None

    def test_should_return_none_for_none_string(self):
        """reasoning_effort='none' should return None for 4.7 models."""
        result = AnthropicConfig._map_reasoning_effort(
            reasoning_effort="none", model="claude-opus-4-7"
        )
        assert result is None

    def test_4_6_should_not_have_display(self):
        """Claude 4.6 should use adaptive but WITHOUT display field."""
        result = AnthropicConfig._map_reasoning_effort(
            reasoning_effort="high", model="claude-opus-4-6"
        )
        assert result["type"] == "adaptive"
        assert "display" not in result


class TestClaude47MapOpenaiParams:
    """Tests for Claude 4.7 breaking changes in map_openai_params."""

    def _get_config(self):
        return AnthropicConfig()

    def test_should_strip_temperature_for_4_7(self):
        """Claude 4.7 does not support temperature."""
        config = self._get_config()
        result = config.map_openai_params(
            non_default_params={"temperature": 0.7},
            optional_params={},
            model="claude-opus-4-7",
            drop_params=False,
        )
        assert "temperature" not in result

    def test_should_keep_temperature_for_4_6(self):
        """Claude 4.6 still supports temperature."""
        config = self._get_config()
        result = config.map_openai_params(
            non_default_params={"temperature": 0.7},
            optional_params={},
            model="claude-opus-4-6",
            drop_params=False,
        )
        assert result.get("temperature") == 0.7

    def test_should_strip_top_p_for_4_7(self):
        """Claude 4.7 does not support top_p."""
        config = self._get_config()
        result = config.map_openai_params(
            non_default_params={"top_p": 0.9},
            optional_params={},
            model="claude-opus-4-7",
            drop_params=False,
        )
        assert "top_p" not in result

    def test_should_set_output_config_effort_for_4_7(self):
        """Claude 4.7 should set output_config.effort when reasoning_effort is provided."""
        config = self._get_config()
        result = config.map_openai_params(
            non_default_params={"reasoning_effort": "high"},
            optional_params={},
            model="claude-opus-4-7",
            drop_params=False,
        )
        assert "output_config" in result
        assert result["output_config"]["effort"] == "high"

    def test_should_not_set_output_config_for_4_6(self):
        """Claude 4.6 should NOT set output_config."""
        config = self._get_config()
        result = config.map_openai_params(
            non_default_params={"reasoning_effort": "high"},
            optional_params={},
            model="claude-opus-4-6",
            drop_params=False,
        )
        assert "output_config" not in result

    @pytest.mark.parametrize(
        "effort_in,effort_out",
        [("low", "low"), ("medium", "medium"), ("high", "high"), ("minimal", "low")],
    )
    def test_should_map_effort_values_correctly(self, effort_in, effort_out):
        """Verify reasoning_effort → output_config.effort mapping."""
        config = self._get_config()
        result = config.map_openai_params(
            non_default_params={"reasoning_effort": effort_in},
            optional_params={},
            model="claude-opus-4-7",
            drop_params=False,
        )
        assert result["output_config"]["effort"] == effort_out
