from unittest.mock import patch

from chatty_agent_common.sentry import init_sentry


def test_init_sentry_without_dsn_is_noop(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.delenv("ADK_DEV_MODE", raising=False)
    monkeypatch.delenv("COMMIT_SHA", raising=False)
    with patch("chatty_agent_common.sentry.sentry_sdk.init") as init:
        with patch("chatty_agent_common.sentry.sentry_sdk.set_tag") as set_tag:
            init_sentry("amaru")
            init.assert_called_once()
            assert init.call_args.kwargs["dsn"] is None
            assert init.call_args.kwargs["send_default_pii"] is False
            assert init.call_args.kwargs["max_request_body_size"] == "never"
            assert init.call_args.kwargs["traces_sample_rate"] == 0
            assert init.call_args.kwargs["environment"] == "production"
            assert init.call_args.kwargs["release"] == "dev"
            set_tag.assert_called_once_with("agent", "amaru")


def test_init_sentry_dev_environment(monkeypatch):
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    with patch("chatty_agent_common.sentry.sentry_sdk.init") as init:
        with patch("chatty_agent_common.sentry.sentry_sdk.set_tag"):
            init_sentry("apana")
            assert init.call_args.kwargs["environment"] == "development"


def test_init_sentry_adk_dev_mode_false_is_production(monkeypatch):
    monkeypatch.setenv("ADK_DEV_MODE", "false")
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    with patch("chatty_agent_common.sentry.sentry_sdk.init") as init:
        with patch("chatty_agent_common.sentry.sentry_sdk.set_tag"):
            init_sentry("be-unique")
            assert init.call_args.kwargs["environment"] == "production"


def test_init_sentry_release_from_commit_sha(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.delenv("ADK_DEV_MODE", raising=False)
    monkeypatch.setenv("COMMIT_SHA", "abc123def")
    with patch("chatty_agent_common.sentry.sentry_sdk.init") as init:
        with patch("chatty_agent_common.sentry.sentry_sdk.set_tag"):
            init_sentry("amaru")
            assert init.call_args.kwargs["release"] == "abc123def"
