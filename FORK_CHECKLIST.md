# Fork Verification Checklist

This checklist verifies all changes made by Simon Stone on top of upstream BerriAI/litellm.

**Last rebase: `v1.103.2` (2026-10-02).** `main` = `v1.103.2` + 4 commits:
`cae07e2e646` → `496042213dc` → `70401bef67d` → `6c1dbc0a6bc`. Unit validation (targeted suites — image
endpoints, cost calculator, proxy hooks/db): 373 passed / 0 failed (plus 5 pre-existing failures
unrelated to the rebase: 4 tests depend on the live upstream `main` cost map, which has since dropped
`claude-4-sonnet-20250514`/`gemini-2.0-flash`/`gpt-4o-realtime-preview`; 1 fails on `AF_UNIX path too
long` from this machine's deep tmp dir, unrelated to any code change).

This rebase also picked up upstream's own fix for the `/v1/images/edits` `image[]`/`mask[]` form-field
leak (PR #39512, merged into `v1.103.2`), which this fork had been carrying unpatched since `v1.101.0`.

## Summary of Simon Stone's Commits (v1.88.0 era → disposition)

| Fork commit | Description | Disposition |
|--------|-------------|-------------|
| `23869b7082` | fix: move zero-cost model check before all other budget checks | **upstream-closed**: `_is_model_cost_zero` + `_get_router_zero_cost_cache` (auth_checks.py) gate **all** budget checks (incl. `_check_end_user_budget`) behind `skip_all_budget_checks`; custom-auth path also skips (`_run_post_custom_auth_checks`). Oracle: `test_zero_cost_model_budget_bypass.py` 17/17 PASS on clean v1.101.0. |
| `3e932d52db` | fix: custom pricing in Responses API path | **fork-maintained**: re-applied at v1.101.0 as `afa6e01352`, now at v1.103.2 as `496042213dc` (import conflict only: upstream added `all_litellm_params` to the same import line — kept both). Upstream still lacks custom-pricing field propagation in `responses()`/`compact_responses()` and `router_model_id` threading into `get_model_cost_information` (upstream's `_select_model_name_for_cost_calc` and `_response_cost_calculator` handle it; the logging-payload path did not). |
| `7ffa0b96cc` | fix: custom pricing for image generation models | **fork-maintained**: re-applied at v1.101.0 as `218311b9ab`, now at v1.103.2 as `cae07e2e646` (clean cherry-pick, no conflicts), adapted to upstream's rewritten image calculator (`generic_cost_per_token` / `calculate_image_response_cost_from_usage`). The pricing-model guard requires the UUID entry to carry actual pricing (same rule as upstream's `_select_model_name_for_cost_calc`), so the Router's no-pricing UUID entry never shadows the model name. |
| `c95857692d` | fix: don't increase end user spend when team key is used | **fork-maintained**: re-applied at v1.101.0 as `b9f52b3a57`, now at v1.103.2 as `70401bef67d` (test-file-only conflict: both sides had added distinct new tests after the same line — concatenated). Upstream attributes end-user spend unconditionally in `update_database` / `update_cache` / `increment_spend_counters`; oracle showed the exact missing behavior (payload `end_user` + `_update_user_db(end_user_id=)` not cleared for virtual keys). Adapted to upstream's `_update_database_and_spend_counters` structure; end_user_id made non-Final in the callback. |
| `5859a4012c` | doc: add context to agents docs | **fork-maintained**: re-applied at v1.101.0 as `fc6dbfe774`, now at v1.103.2 as `6c1dbc0a6bc`. Upstream deleted `CLAUDE.md` (consolidated into `AGENTS.md`, commit `bf7d1c0733`) between v1.101.0 and v1.103.2, so this rebase re-applied the Dartmouth Fork section onto `AGENTS.md` instead of cherry-picking the original diff. |
| `bc9bd4063b` | fix: don't send 'id' on FunctionCall/FunctionResponse for Vertex AI | **upstream-closed**: PR #34603 (merge `9f9d72b50f`) + `acd414f186`. Upstream threads `forward_function_call_id` through `transform_request`, gated by `VertexGeminiConfig._forward_gemini_function_call_id` (Gemini 3+ on Vertex AI and Google AI alike — stronger than the fork's vertex-only omission). Regression test upstream: `test_forward_gemini_function_call_id_is_gated_on_model_version_only`. |
| `b1b597e087` | fix: bump dependencies to close vuln CVE-2026-48710 | **upstream-closed**: v1.101.0 lock has tornado **6.5.8** (≥ our 6.5.6) and uvicorn **0.51.0** (≥ our 0.49.0). |
| `a58e1a4fa5` | fix: cache end user derived fields per request, not per key | **upstream-closed**: upstream per-request `Principal` projection / in-request metadata in the auth flow. Oracle: `test_user_api_key_auth.py` 163/163 PASS on clean v1.101.0. |
| `ab795fff94` | fix: apply symmetric logic from spend writing to preflight reservation checks | **upstream-closed**: `_reserve_budget_after_common_checks` + release/invalidate on failure (`_update_database_and_spend_counters`). Oracle: `test_budget_reservation.py` 71/71 PASS (incl. second-end-user shrink, release-on-failure, invalidate-on-spend-failure). |
| `7c2809bd57` | fix: bump dependencies to close vuln CVE-2026-48710 (+ zero-cost skip in centralized fetch) | **upstream-closed**: uv.lock part obsolete (tornado 6.5.8 / uvicorn 0.51.0). Code part obsolete: upstream's `get_end_user_object` is a pure fetch (never calls `_check_end_user_budget`, swallows exceptions), so the centralized second end-user lookup cannot raise `BudgetExceededError`; zero-cost is covered by the `common_checks` gate and the reservation pipeline honors `_should_skip_budget_checks`. Team-key suppression restored via `b9f52b3a57`. |
| `187ccb5ba8` | fix: default thinking display to summarized | **upstream-closed (evolved)**: upstream's `_map_reasoning_effort` returns `AnthropicThinkingParam(type="adaptive", display="summarized")` unconditionally for adaptive models — always-on, vs the fork's opt-in `is_reasoning_auto_summary_enabled()` gate. Re-applying the fork's gate would regress upstream's always-on behavior. The fork's explicit-caller-display precedence edge is not carried; a caller can pass `thinking` directly (without `reasoning_effort`) to control display. |
| `5a4ed8276c` | log: add spend debug logging | **dropped** (user decision — debug-only aid). |
| `a318607592` | fix: handle budget checks for zero-cost model and non-master key requests | **orphaned — removed from this checklist**: no branch contains it; superseded by `23869b7082`/`7c2809bd57`, both upstream-closed. |

## End-to-End Test Cases

Scenarios marked **fork-maintained** are the ones that still need e2e validation after a rebase (the
upstream-closed behaviors are covered by upstream's own tests). The 2026-09-17 rebase validated the
unit layer (971 passed); e2e with DB was **not run** in that environment (no local postgres/DATABASE_URL).

### 1. Zero-Cost Model Budget Bypass — `23869b7082` (**upstream-closed**)
Covered by `pytest tests/proxy_unit_tests/test_zero_cost_model_budget_bypass.py` (17/17 on v1.101.0).
Optional e2e: over-budget user + zero-cost `on-prem-model` (ollama/llama2) → 200 OK; paid model → blocked.

### 2. End User Spend Tracking with Team Keys — `c95857692d` → `b9f52b3a57` (**fork-maintained**)
```bash
# team key + end_user: end-user spend must stay 0, team/key spend must grow
curl -X POST http://localhost:4000/chat/completions \
  -H "Authorization: Bearer sk-team-key" \
  -d '{"model": "gpt-4", "messages": [{"role": "user", "content": "test"}], "end_user": "alice"}'
curl -X GET "http://localhost:4000/end_user/spend?end_user_id=alice" -H "Authorization: Bearer sk-master-key"   # expect 0
curl -X GET "http://localhost:4000/team/info?team_id=test-team"   -H "Authorization: Bearer sk-master-key"      # expect team_spend > 0

# master key + end_user: end-user spend must be tracked
curl -X POST http://localhost:4000/chat/completions \
  -H "Authorization: Bearer sk-master-key" \
  -d '{"model": "gpt-4", "messages": [{"role": "user", "content": "test"}], "end_user": "bob"}'
curl -X GET "http://localhost:4000/end_user/spend?end_user_id=bob" -H "Authorization: Bearer sk-master-key"     # expect > 0
```
Unit: `pytest tests/test_litellm/proxy/db/test_end_user_spend_virtual_key.py tests/test_litellm/proxy/hooks/test_proxy_track_cost_callback.py -q` (78 passed).

### 3. Custom Pricing for Image Generation Models — `7ffa0b96cc` → `218311b9ab` (**fork-maintained**)
```bash
# image model with custom pricing in the router deployment (model_info.id registered)
curl -X POST http://localhost:4000/images/generations \
  -H "Authorization: Bearer sk-master-key" \
  -d '{"model": "gpt-image-1", "prompt": "a sunset over mountains", "n": 1, "size": "1024x1024"}'
# Expected: spend log cost matches the deployment's custom pricing (not the base gpt-image-1 rate)
```
Unit: `pytest tests/test_litellm/test_cost_calculator.py -k "image or pricing" -q` (25 passed).

### 4. Custom Pricing in Responses API — `3e932d52db` → `afa6e01352` (**fork-maintained**)
```bash
curl -X POST http://localhost:4000/v1/responses \
  -H "Authorization: Bearer sk-master-key" \
  -d '{"model": "gpt-4", "input": "Hello", "temperature": 0.7}'
# Expected: response cost reflects the deployment's custom pricing
#           (litellm_params carries input_cost_per_token/output_cost_per_token → use_custom_pricing_for_model() True)
```
Unit: `pytest tests/test_litellm/test_cost_calculator.py -k "responses or pricing" -q`.

### 5. Symmetric Budget Reservation Logic — `ab795fff94` (**upstream-closed**)
Covered by `pytest tests/test_litellm/proxy/test_budget_reservation.py` (71/71 on v1.101.0) and
`tests/test_litellm/proxy/auth/test_user_api_key_auth.py` (163/163).

### 6. End User Derived Fields Caching — `a58e1a4fa5` (**upstream-closed**)
Covered by the auth suite; upstream's per-request principal projection keeps derived fields per request.

### 7. Vertex AI FunctionCall 'id' Field Fix — `bc9bd4063b` (**upstream-closed**)
Covered by `pytest tests/test_litellm/llms/vertex_ai/gemini/test_vertex_and_google_ai_studio_gemini.py`
(`test_forward_gemini_function_call_id_is_gated_on_model_version_only`).

### 8. Dependency Security Update — `b1b597e087`, `7c2809bd57` (**upstream-closed**)
v1.101.0 `uv.lock`: tornado 6.5.8, uvicorn 0.51.0, aiohttp 3.14.3, cryptography 50.0.0.

### 9. Spend Debug Logging — `5a4ed8276c` (**dropped**)

### 10. Documentation Updates — `5859a4012c` → `fc6dbfe774` (**fork-maintained**)
`grep "Dartmouth Fork" CLAUDE.md` → present.

## Quick Validation Commands

```bash
# Full fork regression set (2026-10-02 result, v1.103.2 rebase: 373 passed / 0 failed,
# + 5 pre-existing failures unrelated to this rebase — see note at top of this file)
uv run --no-sync pytest tests/test_litellm/proxy/image_endpoints/test_endpoints.py \
  tests/test_litellm/test_cost_calculator.py \
  tests/test_litellm/proxy/hooks/test_proxy_track_cost_callback.py \
  tests/test_litellm/proxy/db/test_end_user_spend_virtual_key.py \
  tests/test_litellm/proxy/db/test_db_spend_update_writer.py \
  tests/test_litellm/responses/test_responses_api_request_body.py -q

# Check that the branch carries the expected fork commits
git log --oneline v1.103.2..HEAD
# Expected: 4 commits (cae07e2e646, 496042213dc, 70401bef67d, 6c1dbc0a6bc)
```

## Rebase Hygiene Notes

- **uv.lock conflict markers**: the last rebase committed markers into `uv.lock` (cleaned by
  `7c2809bd57`). This rebase greps `<<<<<<<`/`>>>>>>>` across the tree — only unmodified upstream
  fixtures match (`duck.png`, tokenizer JSON, a JS chunk). Keep this check.
- **uv version**: upstream `pyproject.toml` requires `uv >= 0.10.9` with `exclude-newer = "3 days"`
  (a relative cutoff). Older uv (0.9.7) cannot parse it: `uv sync` re-resolves and drifts `uv.lock`,
  and `uv lock --check` reports a false "lockfile needs updating". Use `uv sync --frozen` / pin
  `uv >= 0.10.9` before dependency work.
- **rust toolchain**: `rust-toolchain.toml` pins 1.98.0; upstream's `litellm-rust/Cargo.lock` needs
  rustc ≥ 1.94. A Homebrew rustc 1.85.1 without rustup cannot build the editable install —
  install rustup (toolchain 1.98.0) or upgrade rust before running a plain `uv sync`.

## Environment Setup

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/litellm_test"
prisma db push
litellm --config config.yaml --detailed_debug
```

## Config Requirements for Testing

```yaml
# config.yaml
model_list:
  - model_name: "on-prem-model"
    litellm_params:
      model: "ollama/llama2"
      api_base: "http://localhost:11434"
      input_cost_per_token: 0.0
      output_cost_per_token: 0.0
  - model_name: "gpt-4"
    litellm_params:
      model: "openai/gpt-4"
      api_key: "sk-..."
```
