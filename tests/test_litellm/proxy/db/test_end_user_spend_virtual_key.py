"""
Unit tests for end-user spend tracking suppression when a virtual/team key is used.

When a virtual/team key (not the master key) is used, end-user spend should NOT
be incremented in LiteLLM_EndUserTable or LiteLLM_DailyEndUserSpend. Only the
key and team spend tables should be updated in that case.

When the master key is used, end-user spend tracking should work as before.

Regression tests for: https://github.com/BerriAI/litellm/issues/XXXX
"""

import os
import sys
from contextlib import ExitStack
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(
    0, os.path.abspath("../../../..")
)  # Adds the parent directory to the system path

from litellm.proxy.db.db_spend_update_writer import DBSpendUpdateWriter

# Stable test fixtures
MASTER_KEY_HASH = "hashed-master-key-abc123"
VIRTUAL_KEY_HASH = "hashed-virtual-key-xyz789"
END_USER_ID = "alice"

# A controlled payload that get_logging_payload would produce when end_user is set.
# We patch get_logging_payload to return this so we don't depend on its internals.
_BASE_PAYLOAD: dict = {
    "model": "gpt-4",
    "custom_llm_provider": "openai",
    "end_user": END_USER_ID,
    "user": "user-123",
    "team_id": "team-abc",
    "api_key": VIRTUAL_KEY_HASH,
    "spend": 0.0,
    "startTime": datetime.now().isoformat(),
    "endTime": datetime.now().isoformat(),
    "completionTokens": 10,
    "promptTokens": 5,
    "totalTokens": 15,
    "requestTags": "[]",
    "request_tags": [],
    "agent_id": None,
    "organization_id": None,
}


def _make_db_writer() -> DBSpendUpdateWriter:
    """
    Create a DBSpendUpdateWriter with all DB-touching internal methods replaced
    by AsyncMocks so no real database access is attempted.
    """
    writer = DBSpendUpdateWriter()
    writer._update_user_db = AsyncMock()
    writer._update_key_db = AsyncMock()
    writer._update_team_db = AsyncMock()
    writer._update_org_db = AsyncMock()
    writer._update_tag_db = AsyncMock()
    writer._insert_spend_log_to_db = AsyncMock()
    writer.add_spend_log_transaction_to_daily_user_transaction = AsyncMock()
    writer.add_spend_log_transaction_to_daily_end_user_transaction = AsyncMock()
    writer.add_spend_log_transaction_to_daily_agent_transaction = AsyncMock()
    writer.add_spend_log_transaction_to_daily_team_transaction = AsyncMock()
    writer.add_spend_log_transaction_to_daily_org_transaction = AsyncMock()
    writer.add_spend_log_transaction_to_daily_tag_transaction = AsyncMock()
    return writer


def _proxy_server_patches(master_key_hash: str = MASTER_KEY_HASH) -> list:
    """Return patch objects for proxy_server module-level globals."""
    return [
        patch("litellm.proxy.proxy_server.disable_spend_logs", False),
        patch("litellm.proxy.proxy_server.prisma_client", MagicMock()),
        patch("litellm.proxy.proxy_server.user_api_key_cache", MagicMock()),
        patch("litellm.proxy.proxy_server.litellm_proxy_budget_name", "test-budget"),
        patch("litellm.proxy.proxy_server.litellm_master_key_hash", master_key_hash),
    ]


async def _call_update_database(
    writer: DBSpendUpdateWriter,
    token: str,
    end_user_id: str = END_USER_ID,
    master_key_hash: str = MASTER_KEY_HASH,
) -> None:
    """Helper: call update_database under the standard patches."""
    # Patch get_logging_payload to return a controlled payload that already has
    # end_user set so we can verify whether the fix clears it.
    import copy

    payload_copy = copy.deepcopy(_BASE_PAYLOAD)

    with ExitStack() as stack:
        for p in _proxy_server_patches(master_key_hash=master_key_hash):
            stack.enter_context(p)
        stack.enter_context(
            patch(
                "litellm.proxy.spend_tracking.spend_tracking_utils.get_logging_payload",
                return_value=payload_copy,
            )
        )
        await writer.update_database(
            token=token,
            user_id="user-123",
            end_user_id=end_user_id,
            team_id="team-abc",
            org_id=None,
            kwargs={},
            completion_response=MagicMock(),
            start_time=datetime.now(),
            end_time=datetime.now(),
            response_cost=0.05,
        )


# ---------------------------------------------------------------------------
# Tests: end_user_id passed to _update_user_db (Path 1 → LiteLLM_EndUserTable)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_virtual_key_passes_none_end_user_id_to_update_user_db():
    """
    When a virtual/team key is used, _update_user_db should receive
    end_user_id=None so that LiteLLM_EndUserTable is not updated.
    """
    writer = _make_db_writer()
    await _call_update_database(writer, token=VIRTUAL_KEY_HASH)

    writer._update_user_db.assert_called_once()
    actual_end_user_id = writer._update_user_db.call_args.kwargs["end_user_id"]
    assert actual_end_user_id is None, (
        f"Expected end_user_id=None for a virtual key request, got {actual_end_user_id!r}"
    )


@pytest.mark.asyncio
async def test_master_key_preserves_end_user_id_in_update_user_db():
    """
    When the master key is used, _update_user_db should receive the original
    end_user_id so that LiteLLM_EndUserTable IS updated.
    """
    writer = _make_db_writer()
    await _call_update_database(
        writer, token=MASTER_KEY_HASH, master_key_hash=MASTER_KEY_HASH
    )

    writer._update_user_db.assert_called_once()
    actual_end_user_id = writer._update_user_db.call_args.kwargs["end_user_id"]
    assert actual_end_user_id == END_USER_ID, (
        f"Expected end_user_id={END_USER_ID!r} for a master key request, got {actual_end_user_id!r}"
    )


@pytest.mark.asyncio
async def test_master_key_alias_preserves_end_user_id_in_update_user_db():
    """
    When the token is the well-known master key alias 'litellm_proxy_master_key'
    (used when disable_adding_master_key_hash_to_db is True), end-user spend
    should still be tracked.
    """
    writer = _make_db_writer()
    # litellm_master_key_hash is set but the token is the alias, not the hash.
    await _call_update_database(
        writer,
        token="litellm_proxy_master_key",
        master_key_hash=MASTER_KEY_HASH,
    )

    writer._update_user_db.assert_called_once()
    actual_end_user_id = writer._update_user_db.call_args.kwargs["end_user_id"]
    assert actual_end_user_id == END_USER_ID, (
        f"Expected end_user_id={END_USER_ID!r} for master key alias, got {actual_end_user_id!r}"
    )


@pytest.mark.asyncio
async def test_no_token_preserves_end_user_id_in_update_user_db():
    """
    When no token is present (open proxy / no-auth setup), hashed_token is None
    and the virtual-key guard must not fire. End-user spend should still be tracked.
    """
    writer = _make_db_writer()
    await _call_update_database(writer, token=None)  # type: ignore[arg-type]

    writer._update_user_db.assert_called_once()
    actual_end_user_id = writer._update_user_db.call_args.kwargs["end_user_id"]
    assert actual_end_user_id == END_USER_ID, (
        f"Expected end_user_id={END_USER_ID!r} when no token present, got {actual_end_user_id!r}"
    )


# ---------------------------------------------------------------------------
# Tests: payload["end_user"] passed to daily transaction (Path 2 → LiteLLM_DailyEndUserSpend)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_virtual_key_clears_payload_end_user_for_daily_transaction():
    """
    When a virtual/team key is used, the spend log payload passed to
    add_spend_log_transaction_to_daily_end_user_transaction should have
    end_user="" so that LiteLLM_DailyEndUserSpend is not updated with the user.
    """
    writer = _make_db_writer()
    await _call_update_database(writer, token=VIRTUAL_KEY_HASH)

    writer.add_spend_log_transaction_to_daily_end_user_transaction.assert_called_once()
    payload = writer.add_spend_log_transaction_to_daily_end_user_transaction.call_args.kwargs[
        "payload"
    ]
    assert payload["end_user"] == "", (
        f"Expected payload['end_user']='' for a virtual key request, got {payload['end_user']!r}"
    )


@pytest.mark.asyncio
async def test_master_key_preserves_payload_end_user_for_daily_transaction():
    """
    When the master key is used, the spend log payload passed to
    add_spend_log_transaction_to_daily_end_user_transaction should keep the
    original end_user value so that LiteLLM_DailyEndUserSpend IS updated.
    """
    writer = _make_db_writer()
    await _call_update_database(
        writer, token=MASTER_KEY_HASH, master_key_hash=MASTER_KEY_HASH
    )

    writer.add_spend_log_transaction_to_daily_end_user_transaction.assert_called_once()
    payload = writer.add_spend_log_transaction_to_daily_end_user_transaction.call_args.kwargs[
        "payload"
    ]
    assert payload["end_user"] == END_USER_ID, (
        f"Expected payload['end_user']={END_USER_ID!r} for master key, got {payload['end_user']!r}"
    )


@pytest.mark.asyncio
async def test_no_token_preserves_payload_end_user_for_daily_transaction():
    """
    When no token is present (open proxy), the virtual-key guard must not fire.
    payload['end_user'] should remain as returned by get_logging_payload.
    """
    writer = _make_db_writer()
    await _call_update_database(writer, token=None)  # type: ignore[arg-type]

    writer.add_spend_log_transaction_to_daily_end_user_transaction.assert_called_once()
    payload = writer.add_spend_log_transaction_to_daily_end_user_transaction.call_args.kwargs[
        "payload"
    ]
    assert payload["end_user"] == END_USER_ID, (
        f"Expected payload['end_user']={END_USER_ID!r} when no token, got {payload['end_user']!r}"
    )


# ---------------------------------------------------------------------------
# Tests: key/team spend is always tracked regardless of virtual-key detection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_virtual_key_still_tracks_key_spend():
    """
    Suppressing end-user spend for a virtual key must not affect key-level spend
    tracking. _update_key_db should still be called.
    """
    writer = _make_db_writer()
    await _call_update_database(writer, token=VIRTUAL_KEY_HASH)
    writer._update_key_db.assert_called_once()


@pytest.mark.asyncio
async def test_virtual_key_still_tracks_team_spend():
    """
    Suppressing end-user spend for a virtual key must not affect team-level spend
    tracking. _update_team_db should still be called.
    """
    writer = _make_db_writer()
    await _call_update_database(writer, token=VIRTUAL_KEY_HASH)
    writer._update_team_db.assert_called_once()
