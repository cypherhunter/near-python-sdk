"""Shared request and response handling for NEAR RPC clients."""

import requests

from near.exceptions import NearException


def request_rpc(client, url, payload):
    """Return the response envelope or raise NearException on RPC failure."""
    try:
        response = client.post(url, json=payload)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise NearException(str(exc)) from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise NearException("Invalid JSON in RPC response") from exc

    if not isinstance(data, dict):
        raise NearException("Invalid RPC response: expected an object")
    if "error" in data:
        raise NearException(data["error"])
    if "result" not in data:
        raise NearException("Invalid RPC response: missing result")
    return data
