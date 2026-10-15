"""Fail closed if a test accidentally reaches an external HTTP transport."""

import httpx
import pytest


@pytest.fixture(autouse=True)
def no_external_http(monkeypatch, tmp_path):
    # Never load a developer's real .env file during unit tests.
    monkeypatch.chdir(tmp_path)

    def fail(*args, **kwargs):
        pytest.fail("Unit tests must use httpx.MockTransport")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", fail)
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)
