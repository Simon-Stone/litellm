# Fork Verification Checklist

This checklist verifies all changes made by Simon Stone on top of upstream BerriAI/litellm.

**Last rebase: `v1.105.0` (2026-10-12).** `main` = `v1.105.0` + 6 patches (plus the checklist-update commit that carries this text):
`3191c97bc4b` -> `08b189ce574` -> `f04be364d32` -> `abe24dff15e` -> `b6acc5e55e5` -> `176d35ddac9`.
A post-rebase fix commit re-applies the end-user field caching fix from `a58e1a4fa5` (see its row below).
Unit validation (targeted suites, mapped to the new `tests/unit/` layout after upstream renamed
`tests/test_litellm/`): 603 passed / 1 failed (`test_async_log_success_event_hands_the_sidecar_a_compact_event_and_skips_the_pipeline`,
the known `AF_UNIX path too long` from this machine's deep tmp dir, unrelated to any code change).
`tests/router_unit_tests/test_router_helper_utils.py`: 146 passed / 4 failed, with all 4 failures
reproduced identically on a clean `v1.105.0` worktree, so they are pre-existing upstream. All four
budget gates (ruff-strict, type-discipline, test-quality, basedpyright) pass against a
`v1.105.0` base with upstream's stock budget values, so this rebase needed no budget rebaseline.

This rebase dropped the v1.104.2-era `chore(lint): rebaseline budget ceilings` commit: the only
genuine new violations came from the `cache_pricing = cast(...)` line in the cache-cost patch, and
removing that cast (the neighboring `input_cost_per_token` lines already pass `.get()` results to
`_cost_value_as_float` uncast) cleared LIT006 and LIT013 at the root. The fixup is folded into
`abe24dff15e`.

## Summary of Simon Stone's Commits (v1.88.0 era → disposition)

| Fork commit | Description | Disposition |
|--------|-------------|-------------|
| `23869b7082` | fix: move zero-cost model check before all other budget checks | **upstream-closed**: `_is_model_cost_zero` + `_get_router_zero_cost_cache` (auth_checks.py) gate **all** budget checks (incl. `_check_end_user_budget`) behind `skip_all_budget_checks`; custom-auth path also skips (`_run_post_custom_auth_checks`). Oracle: `test_zero_cost_model_budget_bypass.py` 17/17 PASS on clean v1.101.0. |
| `3e932d52db` | fix: custom pricing in Responses API path | **upstream-closed (evolved)**: dropped at the v1.104.2 rebase. v1.105.0 threads custom-pricing model selection into the logging path: `get_model_cost_information` now calls `_select_model_name_for_cost_calc(model=base_model if custom_pricing else None, ...)`, and `_select_model_name_for_cost_calc` takes an explicit `router_model_id` (cost_calculator.py:821). |
| `7ffa0b96cc` | fix: custom pricing for image generation models | **upstream-closed (evolved)**: dropped at the v1.104.2 rebase alongside `3e932d52db`; the same `_select_model_name_for_cost_calc` / `router_model_id` selection covers deployment custom pricing for image cost calculation in v1.105.0. |
| `c95857692d` | fix: don't increase end user spend when team key is used | **fork-maintained**: re-applied at v1.101.0 as `b9f52b3a57`, at v1.103.2 as `70401bef67d`, now at v1.105.0 as `3191c97bc4b` (test-file conflict only: upstream appended its autonomous-agent tests at the same anchor and renamed `tests/test_litellm/` to `tests/unit/`, so both sides' tests were concatenated under `tests/unit/`; the two source hunks auto-merged). Upstream v1.105.0 still attributes end-user spend unconditionally in `update_database` / `update_cache` / `increment_spend_counters`. |
| `5859a4012c` | doc: add context to agents docs | **fork-maintained**: re-applied at v1.101.0 as `fc6dbfe774`, at v1.103.2 as `6c1dbc0a6bc`, now at v1.105.0 as `08b189ce574` (clean cherry-pick onto the unchanged tail of `AGENTS.md`). |
| `bc9bd4063b` | fix: don't send 'id' on FunctionCall/FunctionResponse for Vertex AI | **upstream-closed**: PR #34603 (merge `9f9d72b50f`) + `acd414f186`. Upstream threads `forward_function_call_id` through `transform_request`, gated by `VertexGeminiConfig._forward_gemini_function_call_id` (Gemini 3+ on Vertex AI and Google AI alike — stronger than the fork's vertex-only omission). Regression test upstream: `test_forward_gemini_function_call_id_is_gated_on_model_version_only`. |
| `b1b597e087` | fix: bump dependencies to close vuln CVE-2026-48710 | **upstream-closed**: v1.101.0 lock has tornado **6.5.8** (≥ our 6.5.6) and uvicorn **0.51.0** (≥ our 0.49.0). |
| `a58e1a4fa5` | fix: cache end user derived fields per request, not per key | **fork-maintained**: the v1.101.0 "upstream-closed" verdict was wrong — upstream never carried an equivalent (verified against the `v1.101.0` tag: `_copy_user_api_key_auth_for_cache` and `update_valid_token_with_end_user_params` had the pre-fix shapes, and the oracle ran upstream's suite, which never contained the fork's regression tests). The bug re-emerged after the drop: one end user's cached `end_user_max_budget` was enforced against the next end user on a shared key. Re-applied at v1.105.0 adapted to the current code: `_copy_user_api_key_auth_for_cache` strips all end-user fields (incl. the new `end_user_tpd_limit`), and `update_valid_token_with_end_user_params` clears end-user fields when `end_user_id` changes (same-user turns keep the only-overwrite-when-set policy so custom-auth caps survive; `end_user_max_budget` stays owned by the fill-when-None in `_lookup_end_user_and_apply_budget`). Regression tests: `test_end_user_fields_cleared_before_caching`, `test_a_different_end_user_cannot_inherit_the_previous_users_budget`. |
| `ab795fff94` | fix: apply symmetric logic from spend writing to preflight reservation checks | **dropped** (user decision, 2026-10-15): not re-applied. The v1.101.0 "upstream-closed" verdict was also wrong (upstream's reservation pipeline has no virtual-key end-user skip), but the policy it encoded — suppressing end-user budget enforcement for virtual-key requests — is a semantics change, not a bug fix. With `a58e1a4fa5` re-applied the cached values are per-end-user correct, so end-user budgets enforce with the right numbers; re-apply only if per-key-only budget scoping is wanted again. |
| `7c2809bd57` | fix: bump dependencies to close vuln CVE-2026-48710 (+ zero-cost skip in centralized fetch) | **upstream-closed**: uv.lock part obsolete (tornado 6.5.8 / uvicorn 0.51.0). Code part obsolete: upstream's `get_end_user_object` is a pure fetch (never calls `_check_end_user_budget`, swallows exceptions), so the centralized second end-user lookup cannot raise `BudgetExceededError`; zero-cost is covered by the `common_checks` gate and the reservation pipeline honors `_should_skip_budget_checks`. Team-key suppression restored via `b9f52b3a57`. |
| `187ccb5ba8` | fix: default thinking display to summarized | **upstream-closed (evolved)**: upstream's `_map_reasoning_effort` returns `AnthropicThinkingParam(type="adaptive", display="summarized")` unconditionally for adaptive models — always-on, vs the fork's opt-in `is_reasoning_auto_summary_enabled()` gate. Re-applying the fork's gate would regress upstream's always-on behavior. The fork's explicit-caller-display precedence edge is not carried; a caller can pass `thinking` directly (without `reasoning_effort`) to control display. |
| `5a4ed8276c` | log: add spend debug logging | **dropped** (user decision — debug-only aid). |
| `2d71626710b` | feat(proxy): report cache read and write token costs in /model_group/info | **fork-maintained**: now at v1.105.0 as `abe24dff15e`. Upstream's `ModelGroupInfo` still lacks `cache_read_input_token_cost` / `cache_creation_input_token_cost`. This rebase dropped the patch's `cache_pricing = cast(...)` in favor of passing `db_model_info.get(...)` straight to `_cost_value_as_float` (mirroring the neighboring input/output cost lines), which keeps LIT006/LIT013 at upstream's stock ceilings. |
| `ef7b78afd73` | fix(docker): pin OpenSSL 3 for pgbouncer build | **fork-maintained**: now at v1.105.0 as `b6acc5e55e5` (clean cherry-pick). Upstream still builds pgbouncer 1.26.0 against the Chainguard repo's `openssl-dev`, which now resolves to OpenSSL 4. |
| `1770a3ba93b` | chore(deps): bump pyjwt | **fork-maintained**: now at v1.105.0 as `176d35ddac9` (clean cherry-pick, uv.lock delta is the pyjwt 2.15.0 -> 2.15.1 entry only). Upstream v1.105.0 still pins `PyJWT>=2.13.0,<3.0` with 2.15.0 in the lock. |
| `a318607592` | fix: handle budget checks for zero-cost model and non-master key requests | **orphaned — removed from this checklist**: no branch contains it; superseded by `23869b7082`/`7c2809bd57`, both upstream-closed. |

## End-to-End Test Cases

Scenarios marked **fork-maintained** are the ones that still need e2e validation after a rebase (the
upstream-closed behaviors are covered by upstream's own tests). The v1.105.0 rebase validated the
unit layer only; e2e with DB was **not run** in this environment (no local postgres/DATABASE_URL).

### 1. Zero-Cost Model Budget Bypass — `23869b7082` (**upstream-closed**)
Covered by `pytest tests/proxy_unit_tests/test_zero_cost_model_budget_bypass.py` (17/17 on v1.101.0).
Optional e2e: over-budget user + zero-cost `on-prem-model` (ollama/llama2) → 200 OK; paid model → blocked.

### 2. End User Spend Tracking with Team Keys — `c95857692d` -> `3191c97bc4b` (**fork-maintained**)
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
Unit: `pytest tests/unit/proxy/db/test_end_user_spend_virtual_key.py tests/unit/proxy/hooks/test_proxy_track_cost_callback.py -q`.

### 3. Custom Pricing for Image Generation Models — `7ffa0b96cc` (**upstream-closed**)
```bash
# image model with custom pricing in the router deployment (model_info.id registered)
curl -X POST http://localhost:4000/images/generations \
  -H "Authorization: Bearer sk-master-key" \
  -d '{"model": "gpt-image-1", "prompt": "a sunset over mountains", "n": 1, "size": "1024x1024"}'
# Expected: spend log cost matches the deployment's custom pricing (not the base gpt-image-1 rate)
```
Covered by the full cost-calculator suite in `tests/unit/test_cost_calculator.py` (upstream tests, since the fork patch was dropped).

### 4. Custom Pricing in Responses API — `3e932d52db` (**upstream-closed**)
```bash
curl -X POST http://localhost:4000/v1/responses \
  -H "Authorization: Bearer sk-master-key" \
  -d '{"model": "gpt-4", "input": "Hello", "temperature": 0.7}'
# Expected: response cost reflects the deployment's custom pricing
#           (litellm_params carries input_cost_per_token/output_cost_per_token → use_custom_pricing_for_model() True)
```
Covered by the full cost-calculator suite in `tests/unit/test_cost_calculator.py` (upstream tests, since the fork patch was dropped).

### 5. Symmetric Budget Reservation Logic — `ab795fff94` (**dropped**)
Not re-applied (user decision, 2026-10-15); see the disposition table. End-user budgets remain
enforced for virtual-key requests, now with per-end-user correct values from the `a58e1a4fa5` re-apply.

### 6. End User Derived Fields Caching — `a58e1a4fa5` (**fork-maintained**)
Unit: `pytest tests/unit/proxy/auth/test_custom_auth_end_user_budget.py tests/unit/proxy/auth/test_auth_checks_object_access_and_lookup.py -q`
(regression tests `test_a_different_end_user_cannot_inherit_the_previous_users_budget` and
`test_end_user_fields_cleared_before_caching`).

### 7. Vertex AI FunctionCall 'id' Field Fix — `bc9bd4063b` (**upstream-closed**)
Covered by `pytest tests/unit/llms/vertex_ai/gemini/test_vertex_and_google_ai_studio_gemini.py`
(`test_forward_gemini_function_call_id_is_gated_on_model_version_only`).

### 8. Dependency Security Update — `b1b597e087`, `7c2809bd57` (**upstream-closed**)
v1.101.0 `uv.lock`: tornado 6.5.8, uvicorn 0.51.0, aiohttp 3.14.3, cryptography 50.0.0.

### 9. Spend Debug Logging — `5a4ed8276c` (**dropped**)

### 10. Documentation Updates — `5859a4012c` -> `08b189ce574` (**fork-maintained**)
`grep "Dartmouth Fork" AGENTS.md` -> present.

## Quick Validation Commands

```bash
# Full fork regression set (2026-10-12 result, v1.105.0 rebase: 603 passed / 1 failed,
# the AF_UNIX pre-existing failure — see note at top of this file)
uv run --no-sync pytest tests/unit/proxy/image_endpoints/test_endpoints.py \
  tests/unit/test_cost_calculator.py \
  tests/unit/proxy/hooks/test_proxy_track_cost_callback.py \
  tests/unit/proxy/db/test_end_user_spend_virtual_key.py \
  tests/unit/proxy/db/test_db_spend_update_writer.py \
  tests/unit/responses/test_responses_api_request_body.py \
  tests/unit/proxy/proxy_server/test_routes_model_info.py -q

# Budget gates against the new upstream base (all four passed with stock v1.105.0 values)
uv run --no-sync python scripts/ruff_strict_gate.py --base v1.105.0
uv run --no-sync python scripts/type_discipline_gate.py --base v1.105.0
uv run --no-sync python scripts/test_quality_gate.py --base v1.105.0
uv run --no-sync python scripts/type_check_gate.py --base v1.105.0

# Check that the branch carries the expected fork commits
git log --oneline v1.105.0..HEAD
# Expected: 6 patch commits (3191c97bc4b, 08b189ce574, f04be364d32, abe24dff15e, b6acc5e55e5,
# 176d35ddac9) plus the checklist-update doc commit on top
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
- **stray `litellm/proxy/.venv`**: the type-discipline checker walks `litellm/` on disk, so an
  untracked leftover venv there silently inflates whole-tree LIT counts (this rebase saw +6 phantom
  LIT003 from a uv 0.5.14-era empty scaffold). `rm -rf litellm/proxy/.venv` before trusting a gate
  result.
- **budget gates on a rebased main**: run each gate with `--base <new-upstream-tag>`. `make lint`
  resolves the base as `origin/main`, which still points at the pre-rebase history until the
  force-push lands, so it would blame all of upstream's drift on the rebase.
- **`tests/test_litellm/` is now `tests/unit/`**: upstream renamed the directory between v1.104.2
  and v1.105.0; new fork test files and the unit commands above use the `tests/unit/` paths.

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
