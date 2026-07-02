# Default `thinking.display="summarized"` for Anthropic adaptive thinking (chat completion path)

## Goal

On the `litellm.completion` (chat/completions) path, when the OpenAI-style
`reasoning_effort` parameter is mapped to Anthropic **adaptive** thinking
(`thinking: {type: "adaptive"}` + `output_config: {effort: ...}`), also default
`thinking.display` to `"summarized"` so that thinking summaries are returned
(instead of Anthropic's `"omitted"` default on newer models like
`claude-opus-4-7/4-8`, `claude-sonnet-5`).

Keep the existing `reasoning_effort` -> `output_config.effort` mapping exactly as
it is today. This change only adds the `display` field to the adaptive thinking
param.

## Precedence rules (must hold)

For the adaptive branch only:

1. **Explicit `thinking.display`** supplied by the caller wins (e.g. caller passes
   `thinking={"type": "adaptive", "display": "omitted"}` alongside
   `reasoning_effort`). Preserve whatever the caller set.
2. Else if **`reasoning_auto_summary` is enabled** (`litellm.reasoning_auto_summary`
   flag OR `LITELLM_REASONING_AUTO_SUMMARY=true` env var), default to
   `display="summarized"`.
3. Else **leave `display` unset** (Anthropic model default applies).

Non-adaptive (legacy `budget_tokens`) results are unaffected — no `display` field.

## Affected code

- `litellm/llms/anthropic/chat/transformation.py`
  - `map_openai_params`, the `elif param == "reasoning_effort":` branch
    (currently ~lines 1521-1554). This is where the adaptive `thinking` +
    `output_config` are assembled.
  - Optionally also `_map_reasoning_effort` (~lines 1195-1248) — but per the
    decided scope, apply the display logic in the `reasoning_effort` branch of
    `map_openai_params`, NOT unconditionally inside `_map_reasoning_effort`, so
    the `thinking` passthrough branch (`elif param == "thinking"`) and legacy
    models are untouched.
- `litellm/types/llms/anthropic.py`
  - `AnthropicThinkingParam` (line 686) needs a `display` field.
- `litellm/llms/anthropic/experimental_pass_through/utils.py`
  - Reuse existing `is_reasoning_auto_summary_enabled()` (line 8). Import it into
    `chat/transformation.py`.

## Tasks (ordered)

1. **Extend the type.** In `litellm/types/llms/anthropic.py`, add to
   `AnthropicThinkingParam` (line 686-688):
   ```python
   display: Literal["summarized", "omitted"]
   ```
   (`TypedDict` is `total=False`, so it stays optional. Confirm `Literal` is
   already imported in that module.)

2. **Import the gate.** In `litellm/llms/anthropic/chat/transformation.py`, import
   `is_reasoning_auto_summary_enabled` from
   `..experimental_pass_through.utils`. Verify this does not create a circular
   import; if it does, do a lazy import inside the branch instead.

3. **Apply the display default in the `reasoning_effort` branch.** In
   `map_openai_params`, inside the `else:` block that currently sets
   `optional_params["thinking"] = mapped_thinking` for the adaptive model
   (~lines 1542-1554), after setting `output_config`, compute the effective
   display and attach it only when `mapped_thinking["type"] == "adaptive"`:

   - Read any explicit caller-provided display from BOTH:
     - `optional_params.get("thinking")` (if the `thinking` branch already ran
       this pass), and
     - `non_default_params.get("thinking")` (in case the `thinking` branch runs
       after `reasoning_effort` for this iteration order).
     Use the first dict that has a `"display"` key.
   - If an explicit display exists -> set `mapped_thinking["display"] = <explicit>`.
   - Else if `is_reasoning_auto_summary_enabled()` -> set
     `mapped_thinking["display"] = "summarized"`.
   - Else -> leave unset.

   Assign the (possibly updated) `mapped_thinking` back to
   `optional_params["thinking"]`.

   Note: today the `reasoning_effort` branch overwrites `optional_params["thinking"]`
   wholesale, which is why the explicit-display value must be read out and
   re-applied rather than merged blindly.

4. **Guard the `none`/legacy paths.** Ensure:
   - `reasoning_effort` in (`None`, `"none"`) still strips `thinking`/`output_config`
     (unchanged behavior, no display added).
   - Non-adaptive models (legacy `budget_tokens`) never receive a `display` key.

## Validation

- `pytest tests/test_litellm/llms/anthropic/chat/test_anthropic_chat_transformation.py`
- Add unit tests (same file / new file) asserting, for an adaptive model such as
  `claude-opus-4-8`:
  1. `reasoning_auto_summary` disabled + `reasoning_effort="high"` ->
     `thinking == {"type": "adaptive"}` (NO `display`), `output_config == {"effort": "high"}`.
  2. `litellm.reasoning_auto_summary = True` + `reasoning_effort="high"` ->
     `thinking == {"type": "adaptive", "display": "summarized"}`.
  3. `LITELLM_REASONING_AUTO_SUMMARY=true` env var + `reasoning_effort="medium"` ->
     `display == "summarized"`.
  4. Flag enabled + explicit `thinking={"type": "adaptive", "display": "omitted"}`
     passed alongside `reasoning_effort` -> `display == "omitted"` (explicit wins).
  5. Legacy/non-adaptive model + `reasoning_effort="high"` -> `thinking` uses
     `budget_tokens`, NO `display` key.
  6. `reasoning_effort="none"` -> `thinking`/`output_config` removed regardless of flag.
- Remember to save/restore `litellm.reasoning_auto_summary` and the env var in
  tests (follow the pattern in
  `tests/test_litellm/llms/anthropic/experimental_pass_through/messages/test_reasoning_auto_summary_messages.py`).

## Risks / notes

- **Iteration order** of `non_default_params` means the `thinking` branch and the
  `reasoning_effort` branch can run in either order. Reading explicit display from
  both `optional_params` and `non_default_params` handles both orders. Add a test
  that passes `thinking` + `reasoning_effort` together to lock this in.
- **Circular import**: `chat/transformation.py` importing from
  `experimental_pass_through/utils.py`. If problematic, use a local import inside
  the branch. `utils.py` only imports `litellm` + `os`, so a top-level import is
  likely fine.
- **Billing**: `display="summarized"` does not change thinking token billing; it
  only makes summaries visible. No cost regression, but note in PR description.

## Out of scope (not in this change)

- Bedrock (`litellm/llms/bedrock/chat/converse_transformation.py`) and Databricks
  (`litellm/llms/databricks/chat/transformation.py`) Claude paths. They reuse
  `REASONING_EFFORT_TO_OUTPUT_CONFIG_EFFORT` but build thinking params separately;
  applying the same display default there can be a follow-up.
- The native `anthropic_messages` (`/v1/messages`) handler already sets
  `display="summarized"` when `reasoning_auto_summary` is enabled
  (`experimental_pass_through/messages/handler.py:494`); no change needed there.
- Changing the global default of `litellm.reasoning_auto_summary` (stays `False`).
