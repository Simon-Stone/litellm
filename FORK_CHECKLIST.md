# Fork Verification Checklist

The ledger of fork patches carried on top of upstream BerriAI/litellm. Each rebase re-decides every row
(see `.claude/skills/rebase-upstream/SKILL.md`)

**Last rebase: `v1.108.3` (2026-11-08), from `v1.105.1`.** `main` = `v1.108.3` + 9 patches (plus the
checklist-update commit that carries this text), in order:
`63221b256d9` -> `4a9fcffda1e` -> `84ef73db14e` -> `6cf271dda47` -> `7eed90f8f59` -> `e3fa3229a60` ->
`d97a66359d4` -> `f590937736d` -> `a68437eb3f3`.
Pre-rebase `main` is kept as the branch `litellm_main_before_v1.108.3` (tip `49bf96ecbbc`)

The previous header named `v1.105.0`, but `main` had since been moved onto `v1.105.1` (an upstream
stable-branch release whose backports, all present in `v1.108.3` by PR number, rode along as part of the
old base). Five patches made after that move were missing from this ledger and are recorded below

Oracle method: a clean `v1.108.3` worktree with its own `uv sync --frozen --all-extras`, with the fork's
test files copied in and only the fork's regression tests run. Red there plus green on the branch is the
evidence pair for every fork-maintained row

## Disposition table

### Decided at the v1.108.3 rebase

| Old SHA (v1.105.1 base) | New SHA | Patch | Disposition and evidence |
|---|---|---|---|
| `398815b36b9` | `63221b256d9` | fix: don't increase end user spend when team key is used | **fork-maintained** (divergence). Oracle red, 5/5 virtual-key tests in `test_end_user_spend_virtual_key.py` and `test_proxy_track_cost_callback.py`. Writer hunk auto-merged; it now binds a `Final` `attributed_end_user_id` instead of rebinding the `end_user_id` parameter. Callback hunk re-implemented because upstream rewrote `_PROXY_track_cost_callback`: `end_user_id` is computed once, as a `Final`, inside `if response_cost is not None` (its only reader). New-site hunt: upstream added a failure-path writer `_write_failure_spend_rows`, which goes through `update_database` and is covered by the writer hunk; `_update_database_and_spend_counters`, `increment_spend_counters` and `update_cache` all take the callback's `end_user_id`. Test conflict: concatenated, and fork tests moved to the public `ProxyDBLogger` alias; the test file's `sys.path.insert` was dropped (TQ003) |
| `5f53cf09137` | `4a9fcffda1e` | doc: add Dartmouth fork context to AGENTS.md | **fork-maintained**. Check: absent in `v1.108.3`. Conflict only because upstream reworded the preceding paragraph; upstream's text kept, section appended |
| `039dc140d85` | `84ef73db14e` | doc: fork verification checklist (+ `.kilo/kilo.jsonc`) | **fork-maintained, reshaped**: only the `.kilo/kilo.jsonc` half is carried, as `chore: add kilo config disabling snapshots`. The checklist half is superseded by this file |
| `e91d726e86d` | `6cf271dda47` | feat(proxy): report cache read and write token costs in /model_group/info | **fork-maintained**. Oracle red: `ModelGroupInfo` has no `cache_read_input_token_cost` (AttributeError) and the route omits it (KeyError). Clean pick, then the two new `db_model_info.get(...)` reads were routed through `_DEPLOYMENT_MODEL_INFO_ADAPTER` + `_model_info_cost` for the type gate; the router test followed upstream's move from `tests/router_unit_tests/` to `tests/unit/test_router/test_router_helper_utils.py` via rename detection |
| `ec2b6c8bbc3` | (none) | fix(docker): pin OpenSSL 3 for pgbouncer build | **upstream-closed** (user-confirmed). Oracle: `docker build --target pgbouncer-builder` of the `v1.108.3` Dockerfile builds pgbouncer 1.26.0 against `openssl-4.0-dev-4.0.3-r8`, and the binary runs in the `v1.108.3` runtime base (`tls: OpenSSL 4.0.3`). The pin was written for pgbouncer 1.25.2; upstream itself pinned then reverted openssl-3.6-dev (#44991, #44997) |
| `d4f6461cb3b` | `7eed90f8f59` | chore(deps): bump pyjwt | **fork-maintained**. Check: `v1.108.3` still allows `PyJWT>=2.13.0`, and 2.13.0 is inside the affected range of over a dozen PyJWT advisories patched in 2.14.0 (e.g. GHSA-hxm8-2xgr-2p9m, GHSA-p4g4-x82p-q773). Re-run on the target lock with `uvx --from uv==0.11.7 uv lock --upgrade-package pyjwt`; the lock delta is the pyjwt 2.15.0 -> 2.15.1 entry plus uv's rolling `exclude-newer` timestamp |
| `04164f24a69` | (none) | doc: update fork verification checklist for the v1.105.0 rebase | **superseded** by this ledger commit |
| `4b7dd695874` | `e3fa3229a60` | fix: keep end user derived fields per request, not per key | **fork-maintained, extended** (user decision). Oracle red, 2/2. Upstream renamed the cache copier to the public `copy_user_api_key_auth_for_cache` (the `_` alias remains); the hunk auto-merged onto it. Extension: `end_user_object_permission` is now also stripped before caching and cleared when the end user changes. It was only overwritten when the new end user had a DB row, so end user A's MCP or vector-store permissions could carry onto end user B on a shared key. The extended assertions were red before the fix and green after. The cleared-field list is now one constant, `END_USER_DERIVED_FIELDS` in `auth_checks.py`, shared by the cache copier and `update_valid_token_with_end_user_params` so the two paths cannot drift again; the latter no longer mutates its argument (every caller already rebinds the result). Regression tests: `test_end_user_fields_cleared_before_caching`, `test_a_different_end_user_cannot_inherit_the_previous_users_budget` |
| `398a8d02384` | (none) | fix(realtime): only inject response.create when the proxy disabled VAD auto-response | **upstream-closed** (user-confirmed; was missing from the ledger). Upstream #43791 (refined by #44843) gates both transcription-completed injection sites, in `_handle_raw_backend_message` and `_handle_provider_config_message`, on `_should_disable_vad_auto_response()`, the fork's predicate. Oracle: the fork test hung in upstream's `tests/unit/conftest.py` teardown (`_flush_completed_test_logging` waits on a bare `MagicMock` logging object); ported to upstream's `_mock_logging()` helper with the fork's assertions unchanged, it is green on `v1.108.3` |
| `f408fd9fe05` | `d97a66359d4` | fix: skip end user budget enforcement for virtual key requests | **fork-maintained** (divergence). Oracle red, 5/5 behavior tests (the `TestIsVirtualKeyRequest` tests import the fork-only helper, so they cannot run upstream). Master-key enforcement green on both sides. Conflicts were renames from upstream #45170 (`_check_end_user_budget` -> `check_end_user_budget`, `_get_request_ip_address` -> `get_request_ip_address`, `_run_centralized_common_checks` -> `run_centralized_common_checks`); the same three gated sites remain. New-site hunt: no new end-user budget enforcement site since v1.105.1 |
| `de6bd14f6b0` | `f590937736d` | fix(gemini-realtime): non-user context items no longer trigger a reply | **fork-maintained** (was missing from the ledger). Oracle red: `test_gemini_realtime_non_user_item_does_not_complete_turn[system,assistant]`; upstream still sends `turnComplete: True` for every item. Clean pick; the role read now goes through `_REALTIME_ITEM_ADAPTER` for the type gate |
| `6ab82a2a138` | (none) | fix(deps): bump certifi to 2026.10.23 for GHSA-6q48-6c7w-9gw2 | **upstream-closed** (user-confirmed; was missing from the ledger). The advisory's first patched version is 2026.10.18 and `v1.108.3` locks certifi 2026.10.19 (upstream #47969, #48139 removed the emSign/eMudhra roots across bundled CA files) |
| `4f19ffa102e` | (none) | fix(deps): pin ca-certificates-bundle>=20260909-r3 for CVE-2026-91403 | **upstream-closed (evolved)** (user-confirmed; was missing from the ledger). Upstream #48279 moved `Dockerfile`, `docker/Dockerfile.database` and `docker/Dockerfile.non_root` to wolfi-base `sha256:360896ef...`, which ships `ca-certificates-bundle-20260909-r3` (verified with `apk info` in that base). What the fork loses: the explicit `>=` floor. A future digest bump is only guarded by review |
| `49bf96ecbbc` | `a68437eb3f3` | docs(skill): add rebase-upstream skill | **fork-maintained** (was missing from the ledger). Clean pick |

Known interactions of the `f408fd9fe05` divergence, both predating this rebase and kept as-is by user
decision: per-model end-user budgets (`end_user_model_max_budget`, checked in `_is_within_every_model_budget`
and the Anthropic pass-through caller checks) are still enforced on virtual keys, and a key's
`end_user_budget_id` metadata only grafts a budget that the skip then ignores on virtual keys

### History (decided at earlier rebases)

| Fork commit | Description | Disposition |
|--------|-------------|-------------|
| `23869b7082` | fix: move zero-cost model check before all other budget checks | **upstream-closed**: `_is_model_cost_zero` + `_get_router_zero_cost_cache` gate all budget checks behind `skip_all_budget_checks`. Oracle `test_zero_cost_model_budget_bypass.py` 17/17 on v1.101.0 |
| `3e932d52db` | fix: custom pricing in Responses API path | **upstream-closed (evolved)** at v1.104.2: `_select_model_name_for_cost_calc(router_model_id=...)` |
| `7ffa0b96cc` | fix: custom pricing for image generation models | **upstream-closed (evolved)** at v1.104.2, same mechanism as `3e932d52db` |
| `c95857692d` | fix: don't increase end user spend when team key is used | **fork-maintained**, carried as `398815b36b9` -> `63221b256d9` (row above) |
| `5859a4012c` | doc: add context to agents docs | **fork-maintained**, carried as `5f53cf09137` -> `4a9fcffda1e` |
| `bc9bd4063b` | fix: don't send 'id' on FunctionCall/FunctionResponse for Vertex AI | **upstream-closed**: PR #34603, `VertexGeminiConfig._forward_gemini_function_call_id` |
| `b1b597e087` | fix: bump dependencies to close vuln CVE-2026-48710 | **upstream-closed**: v1.101.0 lock has tornado 6.5.8 and uvicorn 0.51.0 |
| `a58e1a4fa5` | fix: cache end user derived fields per request, not per key | **fork-maintained**, carried as `4b7dd695874` -> `e3fa3229a60`. A false closure at v1.101.0 (judged by upstream's suite, which never had the fork's tests) let the bug return until it was re-applied |
| `ab795fff94` | fix: apply symmetric logic from spend writing to preflight reservation checks | **fork-maintained**, carried as `f408fd9fe05` -> `d97a66359d4` |
| `7c2809bd57` | fix: bump deps + zero-cost skip in centralized fetch | **upstream-closed**: lock obsolete; `get_end_user_object` is a pure fetch |
| `187ccb5ba8` | fix: default thinking display to summarized | **upstream-closed (evolved)**: upstream always sends `display="summarized"` for adaptive models; the fork's caller-display precedence edge is not carried |
| `5a4ed8276c` | log: add spend debug logging | **dropped** (user decision, debug-only aid) |
| `2d71626710b` | feat(proxy): report cache read and write token costs in /model_group/info | **fork-maintained**, carried as `e91d726e86d` -> `6cf271dda47` |
| `ef7b78afd73` | fix(docker): pin OpenSSL 3 for pgbouncer build | carried as `ec2b6c8bbc3`, **upstream-closed** at v1.108.3 (row above) |
| `1770a3ba93b` | chore(deps): bump pyjwt | **fork-maintained**, carried as `d4f6461cb3b` -> `7eed90f8f59` |
| `a318607592` | fix: handle budget checks for zero-cost model and non-master key requests | **orphaned**, superseded by `23869b7082` / `7c2809bd57` |

## Verification results (v1.108.3 rebase)

Fork regression set on the branch: 2841 passed, 1 failed. The failure,
`test_async_log_success_event_hands_the_sidecar_a_compact_event_and_skips_the_pipeline`, fails identically on
clean `v1.108.3` (`OSError: AF_UNIX path too long` from this machine's deep tmp dir), so it is pre-existing
and environmental

All four budget gates pass against `--base v1.108.3` with upstream's stock values (no budget file touched).
The first run failed three of them on fork code, fixed at the root rather than suppressed:
TQ003 (a `sys.path.insert` in `test_end_user_spend_virtual_key.py`, removed); LIT011 (+7, the end-user-fields
patch mutated its `valid_token` parameter field by field; `update_valid_token_with_end_user_params` now returns
`model_copy(update=...)`, which also removed upstream's own in-place writes there); basedpyright
`reportUnknownArgumentType` +2 / `reportUnknownVariableType` +3 (untyped `dict` reads in the cache-costs,
end-user-fields and Gemini patches, now validated through module-level `TypeAdapter(dict[str, object])`
instances at the call site). Net effect on the touched source files: 6 fewer `reportUnknownMemberType` than
`v1.108.3`

End-to-end scenarios: **not run**. `.env` holds no provider API keys (only `DATABASE_URL`,
`LITELLM_MASTER_KEY` and proxy settings), so no scenario could reach a real provider

## End-to-End Test Cases (fork-maintained rows)

### 1. End-user spend with team keys: `63221b256d9`
```bash
# team key + end_user: end-user spend must stay 0, team/key spend must grow
curl -X POST http://localhost:4000/chat/completions -H "Authorization: Bearer $TEAM_KEY" \
  -d '{"model": "<model>", "messages": [{"role": "user", "content": "test"}], "user": "alice"}'
curl "http://localhost:4000/customer/info?end_user_id=alice" -H "Authorization: Bearer $LITELLM_MASTER_KEY"  # spend 0

# master key + end_user: end-user spend must be tracked
curl -X POST http://localhost:4000/chat/completions -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -d '{"model": "<model>", "messages": [{"role": "user", "content": "test"}], "user": "bob"}'
curl "http://localhost:4000/customer/info?end_user_id=bob" -H "Authorization: Bearer $LITELLM_MASTER_KEY"    # spend > 0
```

### 2. Cache token costs in /model_group/info: `6cf271dda47`
Configure a deployment with `model_info.cache_read_input_token_cost` / `cache_creation_input_token_cost`,
then `curl http://localhost:4000/model_group/info -H "Authorization: Bearer $LITELLM_MASTER_KEY"` and expect
both fields on the group (highest value across the group's deployments)

### 3. End-user fields per request: `e3fa3229a60`
On one virtual key, send a request with `"user": "a"` where customer `a` has a low `max_budget` and object
permissions, then one with `"user": "b"` (no row). The second request must not hit `a`'s budget error or
`a`'s MCP/vector-store restrictions

### 4. End-user budget skipped on virtual keys: `d97a66359d4`
Create customer `c` with `max_budget: 0.0000001`, spend past it with the master key (expect a budget error
on the next master-key request), then send `"user": "c"` with a virtual key (expect 200)

### 5. Gemini realtime non-user items: `f590937736d`
Open `/v1/realtime?model=<gemini live model>`, send `conversation.item.create` with `role: "system"`.
Expect no model reply until a `role: "user"` item arrives

## Quick Validation Commands

```bash
# Fork regression set (v1.108.3 result: 2841 passed / 1 failed, the AF_UNIX failure above)
uv run --no-sync pytest -q --timeout=300 \
  tests/unit/proxy/db/test_end_user_spend_virtual_key.py tests/unit/proxy/hooks/test_proxy_track_cost_callback.py \
  tests/unit/proxy/db/test_db_spend_update_writer.py \
  tests/unit/test_router/test_router_helper_utils.py tests/unit/proxy/proxy_server/test_routes_model_info.py \
  tests/unit/proxy/auth/test_auth_utils.py tests/unit/proxy/auth/test_auth_checks_object_access_and_lookup.py \
  tests/unit/proxy/auth/test_custom_auth_end_user_budget.py tests/unit/proxy/auth/test_user_api_key_auth_request_flow.py \
  tests/unit/proxy/spend_tracking/test_budget_reservation.py \
  tests/unit/llms/gemini/realtime/test_gemini_realtime_transformation.py tests/unit/litellm_core_utils/test_realtime_streaming.py \
  tests/unit/test_cost_calculator.py tests/unit/proxy/image_endpoints/test_endpoints.py \
  tests/unit/responses/test_responses_api_request_body.py

# Budget gates against the new upstream base
uv run --no-sync python scripts/ruff_strict_gate.py --base v1.108.3
uv run --no-sync python scripts/type_discipline_gate.py --base v1.108.3
uv run --no-sync python scripts/test_quality_gate.py --base v1.108.3
uv run --no-sync python scripts/type_check_gate.py --base v1.108.3

# Non-test checks
grep -c 'Dartmouth Fork' AGENTS.md          # 1
grep -c 'PyJWT>=2.14.0' pyproject.toml      # 1
git log --oneline v1.108.3..HEAD            # the 9 patches above plus this checklist commit
```

## Rebase Hygiene Notes

- **Record the base in this header whenever `main` moves.** `main` was moved from `v1.105.0` to `v1.105.1`
  without updating this file, so its SHAs and patch list were stale at the next rebase. `git describe --tags
  --abbrev=0 --exclude='*hotfix*' main` is the source of truth
- **uv lock format**: uv 0.12 rewrites the lock format (drops redundant markers, rewrites `exclude-newer`),
  which turns a one-package bump into a ~400-line diff. Re-lock with the uv that upstream's Dockerfile pins
  (`UV_IMAGE`, 0.11.7 at `v1.108.3`): `uvx --from uv==0.11.7 uv lock --upgrade-package <pkg>`. Older uv
  (< 0.10.9) cannot parse the relative `exclude-newer` at all
- **conflict-marker search**: `git grep -l -E '^(<<<<<<<|>>>>>>>) ' HEAD` was clean at `v1.108.3`
- **rust toolchain**: `rust-toolchain.toml` pins 1.98.0 but is ignored without rustup; Homebrew rustc 1.99
  builds the editable install fine (upstream needs >= 1.94)
- **stray `litellm/proxy/.venv`**: inflates whole-tree LIT counts in the type-discipline gate.
  `rm -rf litellm/proxy/.venv` before trusting a gate result
- **budget gates on a rebased main**: run each with `--base <new-upstream-tag>`; `make lint` resolves the base
  as `origin/main`, which points at the pre-rebase history until the force-push lands
- **upstream test harness**: `tests/unit/conftest.py` flushes queued logging after every test and hangs
  forever on a bare `MagicMock` logging object. Realtime tests must use the file's `_mock_logging()` helper.
  Run oracle tests with `--timeout=60` so a hang shows up as a stack instead of a stall
- **private-to-public renames (#45170)**: many `_name` proxy helpers became `name`, some keeping `_name`
  aliases (`_check_end_user_budget`, `_copy_user_api_key_auth_for_cache`) and some not
  (`_run_centralized_common_checks`, `_get_request_ip_address`). Expect NameErrors in fork tests and textual
  conflicts in fork hunks next to renamed calls
- **test moves**: `tests/router_unit_tests/test_router_helper_utils.py` is now
  `tests/unit/test_router/test_router_helper_utils.py`
- **Docker patches**: judge them with an oracle build, e.g. `git show <tag>:Dockerfile > <scratch>/Dockerfile`
  then `docker build --target pgbouncer-builder`, and `apk info -v` inside the pinned base digest
- **budget gates before landing**: run all four before the ledger commit. This rebase's replay passed every unit
  test yet breached three gates; per-file breakdowns come from running basedpyright with
  `--pythonpath .venv-typecheck/bin/python` on the changed `litellm/` files in both the branch and the oracle
- **folding fixups without `rebase -i`**: replay onto a fresh branch with `git cherry-pick <patch>` then
  `git cherry-pick -n <fixup>` + `git commit --amend --no-edit`, and compare `HEAD^{tree}` with the old tip
- **don't `git stash` mid cherry-pick**: it clears `CHERRY_PICK_HEAD`, so the pick has to be finished with a
  manual `git commit --author=... --date=...`
- **e2e**: this machine's `.env` has no provider keys; add one before the next rebase to run the e2e cases

## Environment Setup

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/litellm_test"
python litellm/proxy/proxy_cli.py --config litellm/proxy/dev_config.yaml --detailed_debug --use_v2_migration_resolver
```
