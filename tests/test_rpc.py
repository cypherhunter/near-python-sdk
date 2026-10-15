import base64
from contextlib import nullcontext
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import httpx

from near.api import NearAPI, parse_near_result
from near.exceptions import NearException
from near.models.block import Block
from near.rpc import RPCConfig, request_rpc

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
def rpc():
    state = SimpleNamespace(
        requests=[], result={}, error=None, response=None, exception=None
    )

    def handler(request):
        state.requests.append(request)
        if state.exception is not None:
            raise state.exception
        if state.response is not None:
            return state.response
        data = {"jsonrpc": "2.0", "id": json.loads(request.content)["id"]}
        if state.error is not None:
            data["error"] = state.error
        else:
            data["result"] = state.result
        return httpx.Response(200, json=data)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        state.client = client
        yield state


@pytest.fixture
def api(rpc):
    return NearAPI(
        client=rpc.client, rpc_url="https://rpc.example.test", max_retries=0
    )


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


def test_contract_unicode_and_arguments(api, rpc):
    value = {"message": "你好 🌏"}
    result = {
        "block_height": 123,
        "block_hash": "block-hash",
        "logs": ["日志"],
        "result": list(json.dumps(value, ensure_ascii=False).encode("utf-8")),
    }
    rpc.result = result
    args = {"name": "中文"}
    assert api.call_contract_func("example.near", "get", args) == {
        **result,
        "result": value,
    }
    payload = json.loads(rpc.requests[-1].content)
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
def test_rpc_errors_preserve_raw_payload(api, rpc, operation, error):
    rpc.error = error
    with pytest.raises(NearException) as caught:
        operation(api)
    assert caught.value.error == error
    assert caught.value.args == (error,)
    assert "message" in str(caught.value)


@pytest.mark.parametrize("operation", OPERATIONS)
def test_transport_errors(api, rpc, operation):
    error = httpx.ConnectError("connection failed")
    rpc.exception = error
    with pytest.raises(NearException, match="connection failed") as caught:
        operation(api)
    assert caught.value.__cause__ is error


@pytest.mark.parametrize("operation", OPERATIONS)
def test_http_errors(api, rpc, operation):
    rpc.response = httpx.Response(503)
    with pytest.raises(NearException, match="503") as caught:
        operation(api)
    assert isinstance(caught.value.__cause__, httpx.HTTPStatusError)


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("response", [None, [], {}, {"jsonrpc": "2.0"}])
def test_invalid_response(api, rpc, operation, response):
    rpc.response = httpx.Response(200, content=json.dumps(response))
    with pytest.raises(NearException, match="Invalid RPC response"):
        operation(api)


@pytest.mark.parametrize("operation", OPERATIONS)
def test_invalid_json(api, rpc, operation):
    rpc.response = httpx.Response(200, content="not json")
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
def test_success_return_values(api, rpc, operation, result, expected):
    rpc.result = result
    assert operation(api) == expected
    assert str(rpc.requests[-1].url) == api.near_rpc_url


@pytest.mark.parametrize(
    "operation",
    [
        lambda a: a.block.finality(),
        lambda a: a.block.block(123),
        lambda a: a.block.block(None),
    ],
)
def test_block_success(api, rpc, operation):
    rpc.result = {
        "author": "validator.near",
        "header": {"height": 123},
        "chunks": [],
    }
    block = operation(api)
    assert isinstance(block, Block)
    assert block.author == "validator.near"
    assert block.header.height == 123


def test_chunk_success_preserves_envelope(api, rpc):
    response = {"jsonrpc": "2.0", "id": "dontcare", "result": {"header": {}}}
    rpc.result = response["result"]
    assert api.block.chunk("chunk-hash") == response


PAYLOAD = {"jsonrpc": "2.0", "id": "test", "method": "status", "params": []}


def run_transport(handler, config=None, payload=None):
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        return request_rpc(
            client,
            "https://rpc.example.test",
            payload or PAYLOAD,
            config=config,
        )


@pytest.mark.parametrize(
    "failure", [httpx.ConnectError, httpx.ConnectTimeout, 502, 503, 504]
)
def test_retry_then_success(failure, monkeypatch):
    calls = []
    sleep = Mock()
    monkeypatch.setattr("near.rpc.time.sleep", sleep)

    def handler(request):
        calls.append(request)
        if len(calls) <= 3:
            if isinstance(failure, int):
                return httpx.Response(failure)
            raise failure("temporary failure", request=request)
        return httpx.Response(200, json={**PAYLOAD, "result": {"ok": True}})

    assert run_transport(handler)["result"] == {"ok": True}
    assert len(calls) == 4
    assert [call.args[0] for call in sleep.call_args_list] == [0.5, 1.0, 2.0]


@pytest.mark.parametrize(
    "failure", [httpx.ConnectError, httpx.ConnectTimeout, 502, 503, 504]
)
def test_retry_exhaustion(failure, monkeypatch):
    calls = []
    sleep = Mock()
    monkeypatch.setattr("near.rpc.time.sleep", sleep)

    def handler(request):
        calls.append(request)
        if isinstance(failure, int):
            return httpx.Response(failure)
        raise failure("temporary failure", request=request)

    with pytest.raises(NearException) as caught:
        run_transport(handler, RPCConfig(max_retries=2))
    assert len(calls) == 3
    assert sleep.call_count == 2
    expected = httpx.HTTPStatusError if isinstance(failure, int) else failure
    assert isinstance(caught.value.__cause__, expected)


@pytest.mark.parametrize(
    "failure",
    [
        400,
        404,
        429,
        500,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
        httpx.ReadError,
    ],
)
def test_non_retryable_http_failures(failure):
    calls = []

    def handler(request):
        calls.append(request)
        if isinstance(failure, int):
            return httpx.Response(failure)
        raise failure("failure", request=request)

    with pytest.raises(NearException) as caught:
        run_transport(handler)
    assert len(calls) == 1
    expected = httpx.HTTPStatusError if isinstance(failure, int) else failure
    assert isinstance(caught.value.__cause__, expected)


@pytest.mark.parametrize("failure", [httpx.ConnectError, 503])
@pytest.mark.parametrize(
    "method, params",
    [
        ("broadcast_tx_commit", ["signed-transaction"]),
        ("broadcast_tx_async", ["signed-transaction"]),
        ("send_tx", {}),
        ("unknown_method", []),
        ("query", {"request_type": "unknown_query"}),
        ("query", []),
    ],
)
def test_unknown_and_transaction_methods_are_never_retried(
    failure, method, params
):
    calls = []

    def handler(request):
        calls.append(request)
        if isinstance(failure, int):
            return httpx.Response(failure)
        raise failure("failure", request=request)

    with pytest.raises(NearException):
        run_transport(
            handler, payload={**PAYLOAD, "method": method, "params": params}
        )
    assert len(calls) == 1


@pytest.mark.parametrize(
    "response",
    [
        {"jsonrpc": "1.0", "id": "test", "result": {}},
        {"jsonrpc": "2.0", "result": {}},
        {"jsonrpc": "2.0", "id": "other", "result": {}},
        {"jsonrpc": "2.0", "id": "test"},
        {"jsonrpc": "2.0", "id": "test", "result": {}, "error": {}},
    ],
)
def test_envelope_validation_does_not_retry(response):
    handler = Mock(return_value=httpx.Response(200, json=response))
    with pytest.raises(NearException, match="Invalid RPC response"):
        run_transport(handler)
    handler.assert_called_once()


def test_application_errors_do_not_retry():
    error = {"code": -32602, "message": "Invalid params", "data": {"foo": 1}}
    handler = Mock(
        return_value=httpx.Response(200, json={**PAYLOAD, "error": error})
    )
    with pytest.raises(NearException) as caught:
        run_transport(handler)
    assert caught.value.error == error
    handler.assert_called_once()


def test_null_result_is_valid():
    assert (
        run_transport(
            lambda r: httpx.Response(200, json={**PAYLOAD, "result": None})
        )["result"]
        is None
    )


def test_retry_statuses_are_configurable():
    handler = Mock(return_value=httpx.Response(503))
    with pytest.raises(NearException):
        run_transport(handler, RPCConfig(retry_statuses=()))
    handler.assert_called_once()


@pytest.mark.parametrize("operation", OPERATIONS)
def test_retry_configuration_shared_by_all_clients(operation, rpc):
    rpc.response = httpx.Response(503)
    api = NearAPI(client=rpc.client, max_retries=1, backoff_factor=0)
    with pytest.raises(NearException):
        operation(api)
    assert len(rpc.requests) == 2


def test_shared_client_and_request_id(rpc):
    api = NearAPI(client=rpc.client, id="custom-id")
    assert api.client is api.network.client is api.block.client
    api.network.status()
    rpc.result = {"author": "v.near", "header": {}, "chunks": []}
    api.block.finality()
    assert all(
        json.loads(r.content)["id"] == "custom-id" for r in rpc.requests
    )


@pytest.mark.parametrize("fail", [False, True])
def test_owned_client_context_cleanup(fail):
    with pytest.raises(RuntimeError) if fail else nullcontext():
        with NearAPI() as api:
            assert not api.client.is_closed
            if fail:
                raise RuntimeError("failure inside context")
    assert api.client.is_closed
    api.close()  # Explicit cleanup is idempotent.


def test_explicit_owned_client_cleanup():
    api = NearAPI()
    api.close()
    assert api.client.is_closed


def test_injected_client_remains_open(rpc):
    with NearAPI(client=rpc.client) as api:
        api.network.status()
    api.close()
    assert not rpc.client.is_closed
    api.network.status()


def test_default_timeout():
    with NearAPI() as api:
        assert api.client.timeout.connect == 5.0
        assert api.client.timeout.read == 15.0


@pytest.mark.parametrize(
    "timeout, expected",
    [
        (
            httpx.USE_CLIENT_DEFAULT,
            {"connect": 5, "read": 5, "write": 5, "pool": 5},
        ),
        (2.5, {"connect": 2.5, "read": 2.5, "write": 2.5, "pool": 2.5}),
        (None, {"connect": None, "read": None, "write": None, "pool": None}),
        (
            httpx.Timeout(10, connect=2),
            {"connect": 2, "read": 10, "write": 10, "pool": 10},
        ),
    ],
)
def test_timeout_reaches_shared_client_requests(rpc, timeout, expected):
    api = NearAPI(client=rpc.client, timeout=timeout)
    api.network.status()
    rpc.result = {"author": "v.near"}
    api.block.finality()
    api.view_account("example.near")
    assert all(r.extensions["timeout"] == expected for r in rpc.requests)


def test_injected_timeout_is_preserved():
    handler = Mock(
        return_value=httpx.Response(
            200, json={"jsonrpc": "2.0", "id": "dontcare", "result": {}}
        )
    )
    with httpx.Client(
        transport=httpx.MockTransport(handler), timeout=42
    ) as client:
        NearAPI(client=client).network.status()
    assert handler.call_args.args[0].extensions["timeout"]["read"] == 42


@pytest.mark.parametrize("timeout", [2, None, httpx.Timeout(7, connect=1)])
def test_owned_client_timeout(timeout):
    with NearAPI(timeout=timeout) as api:
        assert api.client.timeout == httpx.Timeout(timeout)


def test_endpoint_configuration_at_initialization(monkeypatch):
    monkeypatch.delenv("NEAR_RPC_URL", raising=False)
    with NearAPI() as api:
        assert api.near_rpc_url == "https://rpc.mainnet.near.org"
    monkeypatch.setenv("NEAR_RPC_URL", "https://rpc.testnet.near.org")
    with NearAPI() as api:
        assert api.near_rpc_url == "https://rpc.testnet.near.org"
    with NearAPI(rpc_url="https://custom.example") as api:
        assert api.near_rpc_url == "https://custom.example"


@pytest.mark.parametrize(
    "kwargs",
    [{"max_retries": -1}, {"max_retries": 1.5}, {"backoff_factor": -1}],
)
def test_invalid_retry_configuration(kwargs):
    with pytest.raises(ValueError):
        NearAPI(**kwargs)


def test_invalid_endpoint_raises_near_exception(rpc):
    api = NearAPI(
        client=rpc.client, rpc_url="https://rpc.example:invalid-port"
    )
    with pytest.raises(NearException) as caught:
        api.network.status()
    assert isinstance(caught.value.__cause__, httpx.InvalidURL)


@pytest.mark.parametrize("block_id", [0, 123, "block-hash"])
def test_account_changes_block_selection(api, rpc, block_id):
    api.view_account_change(["a.near"], block_id)
    params = json.loads(rpc.requests[0].content)["params"]
    assert params["block_id"] == block_id
    assert "finality" not in params
