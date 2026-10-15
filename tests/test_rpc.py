import base64
import json
from unittest.mock import Mock

import pytest
import requests

from near.api import NearAPI, parse_near_result
from near.exceptions import NearException
from near.models.block import Block

OPERATIONS = [
    pytest.param(lambda a: a.view_account("example.near"), id="account"),
    pytest.param(
        lambda a: a.view_account_change(["example.near"]), id="changes"
    ),
    pytest.param(
        lambda a: a.call_contract_func("example.near", "get", {}),
        id="contract",
    ),
    pytest.param(lambda a: a.gas(), id="gas"),
    pytest.param(lambda a: a.block.finality(), id="final-block"),
    pytest.param(lambda a: a.block.block(123), id="block-height"),
    pytest.param(lambda a: a.block.block(None), id="latest-block"),
    pytest.param(lambda a: a.block.chunk("chunk-hash"), id="chunk"),
    pytest.param(lambda a: a.network.status(), id="status"),
    pytest.param(lambda a: a.network.info(), id="network-info"),
    pytest.param(lambda a: a.network.validators(), id="validators"),
]


@pytest.fixture
def api():
    api = NearAPI()
    api.client.close()
    api.client = Mock()
    api.near_rpc_url = "https://rpc.example.test"
    return api


@pytest.mark.parametrize(
    "value",
    [
        "你好，世界 🌏",
        {"名称": "中文合约", "emoji": "🚀"},
        ["中文", "café", "日本語"],
        "ASCII",
        123,
        None,
    ],
)
def test_parse_utf8_json(value):
    encoded = json.dumps(value, ensure_ascii=False).encode("utf-8")
    assert parse_near_result(list(encoded)) == value


def test_contract_unicode_and_arguments(api):
    value = {"message": "你好 🌏"}
    result = {
        "block_height": 123,
        "block_hash": "block-hash",
        "logs": ["日志"],
        "result": list(json.dumps(value, ensure_ascii=False).encode("utf-8")),
    }
    api.client.post.return_value.json.return_value = {"result": result}
    args = {"name": "中文"}
    assert api.call_contract_func("example.near", "get", args) == {
        **result,
        "result": value,
    }
    payload = api.client.post.call_args.kwargs["json"]
    assert payload["method"] == "query"
    assert payload["params"]["method_name"] == "get"
    decoded = base64.b64decode(payload["params"]["args_base64"])
    assert json.loads(decoded.decode("utf-8")) == args


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize(
    "error",
    [
        {"code": -32602, "message": "Invalid params"},
        {
            "code": -32000,
            "message": "Server error",
            "data": "details",
            "cause": {
                "name": "UNKNOWN_ACCOUNT",
                "info": {"account_id": "missing"},
            },
        },
    ],
)
def test_rpc_errors_preserve_raw_payload(api, operation, error):
    api.client.post.return_value.json.return_value = {"error": error}
    with pytest.raises(NearException) as caught:
        operation(api)
    assert caught.value.error is error
    assert caught.value.args == (error,)
    assert "message" in str(caught.value)


@pytest.mark.parametrize("operation", OPERATIONS)
def test_transport_errors(api, operation):
    error = requests.ConnectionError("connection failed")
    api.client.post.side_effect = error
    with pytest.raises(NearException, match="connection failed") as caught:
        operation(api)
    assert caught.value.__cause__ is error


@pytest.mark.parametrize("operation", OPERATIONS)
def test_http_errors(api, operation):
    error = requests.HTTPError("503 Service Unavailable")
    api.client.post.return_value.raise_for_status.side_effect = error
    with pytest.raises(NearException, match="503") as caught:
        operation(api)
    assert caught.value.__cause__ is error


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("response", [None, [], {}, {"jsonrpc": "2.0"}])
def test_invalid_response(api, operation, response):
    api.client.post.return_value.json.return_value = response
    with pytest.raises(NearException, match="Invalid RPC response"):
        operation(api)


@pytest.mark.parametrize("operation", OPERATIONS)
def test_invalid_json(api, operation):
    api.client.post.return_value.json.side_effect = ValueError("invalid JSON")
    with pytest.raises(NearException, match="Invalid JSON") as caught:
        operation(api)
    assert isinstance(caught.value.__cause__, ValueError)


@pytest.mark.parametrize(
    "operation, result, expected",
    [
        (
            lambda a: a.view_account("example.near"),
            {
                "amount": "1000000000000000000000000",
                "locked": "0",
                "storage_usage": 12,
            },
            "Amount: 1.0\nLocked: 0.0\nStorage Usage: 12",
        ),
        (
            lambda a: a.view_account_change(["example.near"]),
            {"changes": []},
            {"changes": []},
        ),
        (
            lambda a: a.gas(),
            {"gas_price": "100000000"},
            "0.000000000000000100000000",
        ),
        (
            lambda a: a.network.status(),
            {"chain_id": "mainnet"},
            {"chain_id": "mainnet"},
        ),
        (
            lambda a: a.network.info(),
            {"active_peers": []},
            {"active_peers": []},
        ),
        (
            lambda a: a.network.validators(),
            {"current_validators": []},
            {"current_validators": []},
        ),
    ],
)
def test_success_return_values(api, operation, result, expected):
    api.client.post.return_value.json.return_value = {"result": result}
    assert operation(api) == expected
    assert api.client.post.call_args.args == (api.near_rpc_url,)
    api.client.post.return_value.raise_for_status.assert_called_once()


@pytest.mark.parametrize(
    "operation",
    [
        lambda a: a.block.finality(),
        lambda a: a.block.block(123),
        lambda a: a.block.block(None),
    ],
)
def test_block_success(api, operation):
    api.client.post.return_value.json.return_value = {
        "result": {
            "author": "validator.near",
            "header": {"height": 123},
            "chunks": [],
        }
    }
    block = operation(api)
    assert isinstance(block, Block)
    assert block.author == "validator.near"
    assert block.header.height == 123


def test_chunk_success_preserves_envelope(api):
    response = {"jsonrpc": "2.0", "id": "dontcare", "result": {"header": {}}}
    api.client.post.return_value.json.return_value = response
    assert api.block.chunk("chunk-hash") == response
