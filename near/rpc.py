"""Shared synchronous HTTPX transport for NEAR JSON-RPC."""

import time
from dataclasses import dataclass

import httpx

from near.exceptions import NearException

DEFAULT_RPC_URL = "https://rpc.mainnet.near.org"
DEFAULT_TIMEOUT = httpx.Timeout(15.0, connect=5.0)

# Unknown methods (especially transaction submissions) must never be retried.
READ_ONLY_METHODS = frozenset(
    {
        "status",
        "network_info",
        "validators",
        "gas_price",
        "block",
        "chunk",
        "EXPERIMENTAL_changes",
    }
)
READ_ONLY_QUERIES = frozenset(
    {
        "view_account",
        "call_function",
        "view_code",
        "view_state",
        "view_access_key",
        "view_access_key_list",
    }
)


@dataclass(frozen=True)
class RPCConfig:
    """Retry limits count additional attempts after the initial request."""

    timeout: object = httpx.USE_CLIENT_DEFAULT
    max_retries: int = 3
    retry_statuses: tuple[int, ...] = (502, 503, 504)
    backoff_factor: float = 0.5

    def __post_init__(self):
        if not isinstance(self.max_retries, int) or self.max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")
        if self.backoff_factor < 0:
            raise ValueError("backoff_factor must be non-negative")


def _is_read_only(payload):
    method = payload.get("method")
    if method == "query":
        params = payload.get("params")
        return (
            isinstance(params, dict)
            and params.get("request_type") in READ_ONLY_QUERIES
        )
    return method in READ_ONLY_METHODS


def request_rpc(client, url, payload, *, config=None):
    """Return a validated envelope, preserving RPC errors and failure causes."""
    config = config or RPCConfig()
    retries = config.max_retries if _is_read_only(payload) else 0
    for attempt in range(retries + 1):
        try:
            response = client.post(url, json=payload, timeout=config.timeout)
            response.raise_for_status()
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            if attempt == retries:
                raise NearException(str(exc)) from exc
        except httpx.HTTPStatusError as exc:
            if (
                exc.response.status_code not in config.retry_statuses
                or attempt == retries
            ):
                raise NearException(str(exc)) from exc
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            raise NearException(str(exc)) from exc
        else:
            break
        time.sleep(config.backoff_factor * 2**attempt)

    try:
        data = response.json()
    except ValueError as exc:
        raise NearException("Invalid JSON in RPC response") from exc

    if not isinstance(data, dict):
        raise NearException("Invalid RPC response: expected an object")
    if data.get("jsonrpc") != "2.0":
        raise NearException("Invalid RPC response: expected JSON-RPC 2.0")
    if "id" not in data or data["id"] != payload["id"]:
        raise NearException("Invalid RPC response: mismatched or missing id")
    if "error" in data and "result" in data:
        raise NearException("Invalid RPC response: both result and error")
    if "error" in data:
        raise NearException(data["error"])
    if "result" not in data:
        raise NearException("Invalid RPC response: missing result")
    return data
