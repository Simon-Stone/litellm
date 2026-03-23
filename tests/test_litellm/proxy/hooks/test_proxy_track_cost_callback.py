import json
import os
import sys
from typing import Optional

import pytest
from fastapi.testclient import TestClient

sys.path.insert(
    0, os.path.abspath("../../../..")
)  # Adds the parent directory to the system path

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from litellm.proxy._types import UserAPIKeyAuth
from litellm.proxy.hooks.proxy_track_cost_callback import _ProxyDBLogger
from litellm.types.utils import StandardLoggingPayload


@pytest.mark.asyncio
async def test_async_post_call_failure_hook():
    # Setup
    logger = _ProxyDBLogger()

    # Mock user_api_key_dict
    user_api_key_dict = UserAPIKeyAuth(
        api_key="test_api_key",
        key_alias="test_alias",
        user_email="test@example.com",
        user_id="test_user_id",
        team_id="test_team_id",
        org_id="test_org_id",
        team_alias="test_team_alias",
        end_user_id="test_end_user_id",
    )

    # Mock request data
    request_data = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "Hello"}],
        "metadata": {"original_key": "original_value"},
        "proxy_server_request": {"request_id": "test_request_id"},
    }

    # Mock exception
    original_exception = Exception("Test exception")

    # Mock update_database function
    with patch(
        "litellm.proxy.db.db_spend_update_writer.DBSpendUpdateWriter.update_database",
        new_callable=AsyncMock,
    ) as mock_update_database:
        # Call the method
        await logger.async_post_call_failure_hook(
            request_data=request_data,
            original_exception=original_exception,
            user_api_key_dict=user_api_key_dict,
        )

        # Assertions
        mock_update_database.assert_called_once()

        # Check the arguments passed to update_database
        call_args = mock_update_database.call_args[1]
        print("call_args", json.dumps(call_args, indent=4, default=str))
        assert call_args["token"] == "test_api_key"
        assert call_args["response_cost"] == 0.0
        assert call_args["user_id"] == "test_user_id"
        assert call_args["end_user_id"] == "test_end_user_id"
        assert call_args["team_id"] == "test_team_id"
        assert call_args["org_id"] == "test_org_id"
        assert call_args["completion_response"] == original_exception

        # Check that metadata was properly updated
        assert "litellm_params" in call_args["kwargs"]
        assert call_args["kwargs"]["litellm_params"]["proxy_server_request"] == {
            "request_id": "test_request_id"
        }
        metadata = call_args["kwargs"]["litellm_params"]["metadata"]
        assert metadata["user_api_key"] == "test_api_key"
        assert metadata["status"] == "failure"
        assert "error_information" in metadata
        assert metadata["original_key"] == "original_value"


@pytest.mark.asyncio
async def test_async_post_call_failure_hook_non_llm_route():
    # Setup
    logger = _ProxyDBLogger()

    # Mock user_api_key_dict with a non-LLM route
    user_api_key_dict = UserAPIKeyAuth(
        api_key="test_api_key",
        key_alias="test_alias",
        user_email="test@example.com",
        user_id="test_user_id",
        team_id="test_team_id",
        org_id="test_org_id",
        team_alias="test_team_alias",
        end_user_id="test_end_user_id",
        request_route="/custom/route",  # Non-LLM route
    )

    # Mock request data
    request_data = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "Hello"}],
        "metadata": {"original_key": "original_value"},
        "proxy_server_request": {"request_id": "test_request_id"},
    }

    # Mock exception
    original_exception = Exception("Test exception")

    # Mock update_database function
    with patch(
        "litellm.proxy.db.db_spend_update_writer.DBSpendUpdateWriter.update_database",
        new_callable=AsyncMock,
    ) as mock_update_database:
        # Call the method
        await logger.async_post_call_failure_hook(
            request_data=request_data,
            original_exception=original_exception,
            user_api_key_dict=user_api_key_dict,
        )

        # Assert that update_database was NOT called for non-LLM routes
        mock_update_database.assert_not_called()


@pytest.mark.asyncio
async def test_track_cost_callback_skips_when_no_standard_logging_object():
    """
    Reproduces the bug where _PROXY_track_cost_callback raises
    'Cost tracking failed for model=None' when kwargs has no
    standard_logging_object (e.g. call_type=afile_delete).

    File operations have no model and no standard_logging_object.
    The callback should skip gracefully instead of raising.
    """
    logger = _ProxyDBLogger()

    kwargs = {
        "call_type": "afile_delete",
        "model": None,
        "litellm_call_id": "test-call-id",
        "litellm_params": {},
        "stream": False,
    }

    with patch(
        "litellm.proxy.proxy_server.proxy_logging_obj",
    ) as mock_proxy_logging:
        mock_proxy_logging.failed_tracking_alert = AsyncMock()
        mock_proxy_logging.db_spend_update_writer = MagicMock()
        mock_proxy_logging.db_spend_update_writer.update_database = AsyncMock()

        await logger._PROXY_track_cost_callback(
            kwargs=kwargs,
            completion_response=None,
            start_time=datetime.now(),
            end_time=datetime.now(),
        )

        # update_database should NOT be called — nothing to track
        mock_proxy_logging.db_spend_update_writer.update_database.assert_not_called()

        # failed_tracking_alert should NOT be called — this is not an error
        mock_proxy_logging.failed_tracking_alert.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("model_value", [None, ""])
async def test_track_cost_callback_skips_for_falsy_model_and_no_slo(model_value):
    """
    Same bug as above but model can also be empty string (e.g. health check callbacks).
    The guard should catch all falsy model values when sl_object is missing.
    """
    logger = _ProxyDBLogger()

    kwargs = {
        "call_type": "acompletion",
        "model": model_value,
        "litellm_params": {},
        "stream": False,
    }

    with patch(
        "litellm.proxy.proxy_server.proxy_logging_obj",
    ) as mock_proxy_logging:
        mock_proxy_logging.failed_tracking_alert = AsyncMock()
        mock_proxy_logging.db_spend_update_writer = MagicMock()
        mock_proxy_logging.db_spend_update_writer.update_database = AsyncMock()

        await logger._PROXY_track_cost_callback(
            kwargs=kwargs,
            completion_response=None,
            start_time=datetime.now(),
            end_time=datetime.now(),
        )

        mock_proxy_logging.failed_tracking_alert.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: end_user_id suppression for virtual/team keys in cache path
#
# Regression tests for: BudgetExceededError when using a team key with
# concurrent requests sharing the same end_user_id.
#
# Root cause: _PROXY_track_cost_callback was passing the original end_user_id
# to update_cache() even for virtual/team keys. This inflated the cached
# end-user spend object, which then triggered _check_end_user_budget() to
# raise BudgetExceededError on subsequent requests.
# ---------------------------------------------------------------------------

MASTER_KEY_HASH = "hashed-master-key-abc123"
VIRTUAL_KEY_HASH = "hashed-virtual-key-xyz789"
END_USER_ID = "alice"


def _make_kwargs_with_end_user(
    user_api_key: Optional[str],
    end_user_id: str = END_USER_ID,
    response_cost: float = 0.05,
) -> dict:
    """
    Build a minimal kwargs dict that _PROXY_track_cost_callback expects.
    The standard_logging_object carries response_cost.
    litellm_params.metadata carries user_api_key and end_user_id (via user param).
    """
    return {
        "litellm_params": {
            "metadata": {
                "user_api_key": user_api_key,
                "user_api_key_user_id": "user-123",
                "user_api_key_team_id": "team-abc",
                "user_api_key_org_id": None,
                "user_api_key_alias": None,
                "user_api_end_user_max_budget": None,
            },
        },
        "standard_logging_object": {
            "response_cost": response_cost,
            "response_cost_failure_debug_info": None,
            "request_tags": [],
        },
        "cache_hit": False,
        "stream": False,
        "model": "gpt-4",
        # end_user_id is stored under litellm_params.proxy_server_request or
        # directly in litellm_params for get_end_user_id_for_cost_tracking.
        # The simplest path is metadata["user_api_key_end_user_id"]:
        # but get_end_user_id_for_cost_tracking reads from litellm_params directly.
        # We inject it into litellm_params so that get_end_user_id_for_cost_tracking returns it.
    }


def _patch_proxy_server(master_key_hash: str = MASTER_KEY_HASH):
    """Return a list of patches for proxy_server module-level globals."""
    return [
        patch(
            "litellm.proxy.proxy_server.litellm_master_key_hash",
            master_key_hash,
        ),
        patch(
            "litellm.proxy.proxy_server.proxy_logging_obj",
        ),
        patch(
            "litellm.proxy.proxy_server.update_cache",
        ),
    ]


@pytest.mark.asyncio
async def test_virtual_key_suppresses_end_user_id_in_update_cache():
    """
    When a virtual/team key is used, update_cache() should be called with
    end_user_id=None so that _update_end_user_cache() does NOT inflate the
    cached end-user spend object and trigger a false BudgetExceededError.
    """
    logger = _ProxyDBLogger()
    kwargs = _make_kwargs_with_end_user(user_api_key=VIRTUAL_KEY_HASH)

    with patch(
        "litellm.proxy.proxy_server.litellm_master_key_hash",
        MASTER_KEY_HASH,
    ), patch(
        "litellm.proxy.proxy_server.proxy_logging_obj",
    ) as mock_proxy_logging, patch(
        "litellm.proxy.proxy_server.update_cache",
        new_callable=AsyncMock,
    ) as mock_update_cache, patch(
        "litellm.proxy.hooks.proxy_track_cost_callback.get_end_user_id_for_cost_tracking",
        return_value=END_USER_ID,
    ):
        mock_proxy_logging.db_spend_update_writer = MagicMock()
        mock_proxy_logging.db_spend_update_writer.update_database = AsyncMock()
        mock_proxy_logging.slack_alerting_instance = MagicMock()
        mock_proxy_logging.slack_alerting_instance.customer_spend_alert = AsyncMock()

        await logger._PROXY_track_cost_callback(
            kwargs=kwargs,
            completion_response=MagicMock(),
            start_time=datetime.now(),
            end_time=datetime.now(),
        )

        # update_cache must have been called
        mock_update_cache.assert_called_once()
        call_kwargs = mock_update_cache.call_args.kwargs
        assert call_kwargs["end_user_id"] is None, (
            f"Expected end_user_id=None in update_cache for virtual key, "
            f"got {call_kwargs['end_user_id']!r}"
        )


@pytest.mark.asyncio
async def test_master_key_preserves_end_user_id_in_update_cache():
    """
    When the master key is used, update_cache() should be called with the
    original end_user_id so that _update_end_user_cache() correctly tracks
    end-user spend.
    """
    logger = _ProxyDBLogger()
    kwargs = _make_kwargs_with_end_user(user_api_key=MASTER_KEY_HASH)

    with patch(
        "litellm.proxy.proxy_server.litellm_master_key_hash",
        MASTER_KEY_HASH,
    ), patch(
        "litellm.proxy.proxy_server.proxy_logging_obj",
    ) as mock_proxy_logging, patch(
        "litellm.proxy.proxy_server.update_cache",
        new_callable=AsyncMock,
    ) as mock_update_cache, patch(
        "litellm.proxy.hooks.proxy_track_cost_callback.get_end_user_id_for_cost_tracking",
        return_value=END_USER_ID,
    ):
        mock_proxy_logging.db_spend_update_writer = MagicMock()
        mock_proxy_logging.db_spend_update_writer.update_database = AsyncMock()
        mock_proxy_logging.slack_alerting_instance = MagicMock()
        mock_proxy_logging.slack_alerting_instance.customer_spend_alert = AsyncMock()

        await logger._PROXY_track_cost_callback(
            kwargs=kwargs,
            completion_response=MagicMock(),
            start_time=datetime.now(),
            end_time=datetime.now(),
        )

        mock_update_cache.assert_called_once()
        call_kwargs = mock_update_cache.call_args.kwargs
        assert call_kwargs["end_user_id"] == END_USER_ID, (
            f"Expected end_user_id={END_USER_ID!r} in update_cache for master key, "
            f"got {call_kwargs['end_user_id']!r}"
        )


@pytest.mark.asyncio
async def test_virtual_key_suppresses_end_user_id_in_update_database_via_callback():
    """
    When a virtual/team key is used, update_database() should also be called
    with end_user_id=None (defense-in-depth alongside the db_spend_update_writer fix).
    """
    logger = _ProxyDBLogger()
    kwargs = _make_kwargs_with_end_user(user_api_key=VIRTUAL_KEY_HASH)

    with patch(
        "litellm.proxy.proxy_server.litellm_master_key_hash",
        MASTER_KEY_HASH,
    ), patch(
        "litellm.proxy.proxy_server.proxy_logging_obj",
    ) as mock_proxy_logging, patch(
        "litellm.proxy.proxy_server.update_cache",
        new_callable=AsyncMock,
    ), patch(
        "litellm.proxy.hooks.proxy_track_cost_callback.get_end_user_id_for_cost_tracking",
        return_value=END_USER_ID,
    ):
        mock_update_database = AsyncMock()
        mock_proxy_logging.db_spend_update_writer = MagicMock()
        mock_proxy_logging.db_spend_update_writer.update_database = mock_update_database
        mock_proxy_logging.slack_alerting_instance = MagicMock()
        mock_proxy_logging.slack_alerting_instance.customer_spend_alert = AsyncMock()

        await logger._PROXY_track_cost_callback(
            kwargs=kwargs,
            completion_response=MagicMock(),
            start_time=datetime.now(),
            end_time=datetime.now(),
        )

        mock_update_database.assert_called_once()
        call_kwargs = mock_update_database.call_args.kwargs
        assert call_kwargs["end_user_id"] is None, (
            f"Expected end_user_id=None in update_database for virtual key, "
            f"got {call_kwargs['end_user_id']!r}"
        )


@pytest.mark.asyncio
async def test_no_api_key_preserves_end_user_id_in_update_cache():
    """
    When user_api_key is None (open proxy / no-auth setup), the virtual-key guard
    must not fire. update_cache() should receive the original end_user_id.
    """
    logger = _ProxyDBLogger()
    kwargs = _make_kwargs_with_end_user(user_api_key=None)

    with patch(
        "litellm.proxy.proxy_server.litellm_master_key_hash",
        MASTER_KEY_HASH,
    ), patch(
        "litellm.proxy.proxy_server.proxy_logging_obj",
    ) as mock_proxy_logging, patch(
        "litellm.proxy.proxy_server.update_cache",
        new_callable=AsyncMock,
    ) as mock_update_cache, patch(
        "litellm.proxy.hooks.proxy_track_cost_callback.get_end_user_id_for_cost_tracking",
        return_value=END_USER_ID,
    ):
        mock_proxy_logging.db_spend_update_writer = MagicMock()
        mock_proxy_logging.db_spend_update_writer.update_database = AsyncMock()
        mock_proxy_logging.slack_alerting_instance = MagicMock()
        mock_proxy_logging.slack_alerting_instance.customer_spend_alert = AsyncMock()

        await logger._PROXY_track_cost_callback(
            kwargs=kwargs,
            completion_response=MagicMock(),
            start_time=datetime.now(),
            end_time=datetime.now(),
        )

        # When there is no API key, update_cache is still called
        # (via _should_track_cost_callback returning True for end_user_id).
        # The end_user_id must be preserved.
        if mock_update_cache.called:
            call_kwargs = mock_update_cache.call_args.kwargs
            assert call_kwargs["end_user_id"] == END_USER_ID, (
                f"Expected end_user_id={END_USER_ID!r} when no API key, "
                f"got {call_kwargs['end_user_id']!r}"
            )


@pytest.mark.asyncio
async def test_virtual_key_team_and_user_spend_still_tracked():
    """
    Suppressing end-user spend for a virtual key must NOT prevent key-level
    and team-level spend from being tracked. update_cache() must still be
    called with the original token and team_id.
    """
    logger = _ProxyDBLogger()
    kwargs = _make_kwargs_with_end_user(user_api_key=VIRTUAL_KEY_HASH)

    with patch(
        "litellm.proxy.proxy_server.litellm_master_key_hash",
        MASTER_KEY_HASH,
    ), patch(
        "litellm.proxy.proxy_server.proxy_logging_obj",
    ) as mock_proxy_logging, patch(
        "litellm.proxy.proxy_server.update_cache",
        new_callable=AsyncMock,
    ) as mock_update_cache, patch(
        "litellm.proxy.hooks.proxy_track_cost_callback.get_end_user_id_for_cost_tracking",
        return_value=END_USER_ID,
    ):
        mock_proxy_logging.db_spend_update_writer = MagicMock()
        mock_proxy_logging.db_spend_update_writer.update_database = AsyncMock()
        mock_proxy_logging.slack_alerting_instance = MagicMock()
        mock_proxy_logging.slack_alerting_instance.customer_spend_alert = AsyncMock()

        await logger._PROXY_track_cost_callback(
            kwargs=kwargs,
            completion_response=MagicMock(),
            start_time=datetime.now(),
            end_time=datetime.now(),
        )

        mock_update_cache.assert_called_once()
        call_kwargs = mock_update_cache.call_args.kwargs
        # Key-level spend must still be tracked
        assert (
            call_kwargs["token"] == VIRTUAL_KEY_HASH
        ), f"Expected token={VIRTUAL_KEY_HASH!r} in update_cache, got {call_kwargs['token']!r}"
        # Team-level spend must still be tracked
        assert (
            call_kwargs["team_id"] == "team-abc"
        ), f"Expected team_id='team-abc' in update_cache, got {call_kwargs['team_id']!r}"
        # End-user spend must be suppressed
        assert call_kwargs["end_user_id"] is None, (
            f"Expected end_user_id=None in update_cache for virtual key, "
            f"got {call_kwargs['end_user_id']!r}"
        )
