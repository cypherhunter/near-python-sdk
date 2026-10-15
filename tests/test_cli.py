import base64
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from near.api import NearAPI

cli = importlib.import_module("near.main")
COMMANDS = [
    "status",
    "gas",
    "validators",
    "account",
    "block",
    "info",
    "chunk",
    "account-changes",
    "contract-call",
]


@pytest.fixture
def rpc(monkeypatch):
    state = SimpleNamespace(requests=[], apis=[], result={}, error=None)

    def handler(request):
        state.requests.append(request)
        envelope = {"jsonrpc": "2.0", "id": json.loads(request.content)["id"]}
        envelope["error" if state.error else "result"] = (
            state.error or state.result
        )
        return httpx.Response(200, json=envelope)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:

        def factory(**kwargs):
            api = NearAPI(client=client, **kwargs)
            api.close = Mock(wraps=api.close)
            state.apis.append(api)
            return api

        monkeypatch.setattr(cli, "NearAPI", factory)
        monkeypatch.delenv("NEAR_RPC_URL", raising=False)
        yield state


@pytest.mark.parametrize(
    "tokens",
    [["--help"], ["-h"], ["--version"]]
    + [[command, flag] for command in COMMANDS for flag in ["--help", "-h"]],
)
def test_help_and_version_without_client(tokens, monkeypatch, capsys):
    factory = Mock(side_effect=AssertionError("Help must not create a client"))
    monkeypatch.setattr(cli, "NearAPI", factory)
    cli.main(tokens)
    output = capsys.readouterr()
    assert output.out
    assert not output.err
    assert (
        "0.0.3" in output.out
        if tokens == ["--version"]
        else "Usage:" in output.out
    )
    factory.assert_not_called()


@pytest.mark.parametrize(
    "tokens",
    [
        ["unknown"],
        ["account"],
        ["status", "--unknown"],
        ["block", "--finality", "bad"],
        ["status", "extra"],
        ["contract-call", "c.near", "get", "bad-json"],
        ["contract-call", "c.near", "get", "123"],
    ],
)
def test_invalid_arguments(tokens, rpc, capsys):
    with pytest.raises(SystemExit) as caught:
        cli.main(tokens)
    assert caught.value.code != 0
    output = capsys.readouterr()
    assert output.err
    assert not output.out
    assert not rpc.requests


@pytest.mark.parametrize(
    "tokens, result, method, params",
    [
        (["status"], {"chain_id": "mainnet"}, "status", []),
        (["gas"], {"gas_price": "100000000"}, "gas_price", [None]),
        (
            ["gas", "--block", "123"],
            {"gas_price": "100000000"},
            "gas_price",
            [123],
        ),
        (["validators"], {"current_validators": []}, "validators", [None]),
        (
            ["account", "example.near"],
            {"amount": "0", "locked": "0"},
            "query",
            {
                "request_type": "view_account",
                "account_id": "example.near",
                "finality": "optimistic",
            },
        ),
        (["info"], {"active_peers": []}, "network_info", []),
        (
            ["block", "--finality", "final"],
            {"author": "v.near", "header": {}, "chunks": []},
            "block",
            {"finality": "final"},
        ),
        (
            ["block", "--finality", "optimistic"],
            {"author": "v.near"},
            "block",
            {"finality": "optimistic"},
        ),
        (["block", "123"], {"author": "v.near"}, "block", {"block_id": 123}),
        (
            ["block", "block-hash"],
            {"author": "v.near"},
            "block",
            {"block_id": "block-hash"},
        ),
        (
            ["chunk", "chunk-hash"],
            {"header": {}},
            "chunk",
            {"chunk_id": "chunk-hash"},
        ),
        (
            ["account-changes", "a.near", "b.near"],
            {"changes": []},
            "EXPERIMENTAL_changes",
            {
                "changes_type": "account_changes",
                "account_ids": ["a.near", "b.near"],
                "finality": "optimistic",
            },
        ),
    ],
)
def test_commands(tokens, result, method, params, rpc, capsys):
    rpc.result = result
    cli.main(tokens)
    output = capsys.readouterr()
    assert output.out
    assert not output.err
    payload = json.loads(rpc.requests[0].content)
    assert payload["method"] == method
    assert payload["params"] == params
    rpc.apis[0].close.assert_called_once()


@pytest.mark.parametrize(
    "command, result",
    [
        ("status", {"chain_id": "mainnet"}),
        ("validators", {"current_validators": []}),
        ("info", {"active_peers": []}),
        (
            "block",
            {
                "author": "v.near",
                "header": {"height": 123, "extra": "preserved"},
                "chunks": [],
            },
        ),
    ],
)
def test_json_output(command, result, rpc, capsys):
    rpc.result = result
    cli.main([command, "--json"])
    output = capsys.readouterr()
    assert json.loads(output.out) == result
    assert not output.err


def test_contract_call_json(rpc, capsys):
    rpc.result = {
        "block_height": 1,
        "block_hash": "hash",
        "logs": [],
        "result": list('"你好"'.encode()),
    }
    cli.main(["contract-call", "c.near", "get", '{"name":"中文"}', "--json"])
    assert json.loads(capsys.readouterr().out) == {
        **rpc.result,
        "result": "你好",
    }
    params = json.loads(rpc.requests[0].content)["params"]
    assert params["method_name"] == "get"
    assert json.loads(base64.b64decode(params["args_base64"])) == {
        "name": "中文"
    }


@pytest.mark.parametrize(
    "env, explicit, expected",
    [
        (None, None, "https://rpc.mainnet.near.org"),
        ("https://rpc.testnet.near.org", None, "https://rpc.testnet.near.org"),
        (
            "https://rpc.testnet.near.org",
            "https://custom.example",
            "https://custom.example",
        ),
    ],
)
def test_endpoint_priority(env, explicit, expected, rpc, monkeypatch):
    if env:
        monkeypatch.setenv("NEAR_RPC_URL", env)
    cli.main(["status"] + (["--rpc-url", explicit] if explicit else []))
    assert str(rpc.requests[0].url).rstrip("/") == expected


def test_rpc_error_exit_code_and_cleanup(rpc, capsys):
    rpc.error = {"code": -32000, "message": "node unavailable"}
    with pytest.raises(SystemExit) as caught:
        cli.main(["status", "--json"])
    assert caught.value.code == 1
    output = capsys.readouterr()
    assert "node unavailable" in output.err
    assert not output.out
    assert len(rpc.requests) == 1
    rpc.apis[0].close.assert_called_once()


def test_transport_error_exit_code(rpc, capsys, monkeypatch):
    def fail(*args, **kwargs):
        raise httpx.ReadTimeout("read timed out")

    monkeypatch.setattr(httpx.Client, "post", fail)
    with pytest.raises(SystemExit) as caught:
        cli.main(["status"])
    assert caught.value.code == 1
    assert "read timed out" in capsys.readouterr().err
    rpc.apis[0].close.assert_called_once()


@pytest.mark.parametrize("entry", ["module", "console"])
@pytest.mark.parametrize("flag", ["--help", "-h", "--version"])
def test_installed_entry_points(entry, flag):
    command = (
        [sys.executable, "-m", "near.main"]
        if entry == "module"
        else [str(Path(sys.executable).with_name("near-rpc"))]
    )
    completed = subprocess.run(
        command + [flag],
        capture_output=True,
        text=True,
        timeout=10,
        env={**os.environ, "NEAR_RPC_URL": "invalid://no-network"},
    )
    assert completed.returncode == 0
    assert completed.stdout
    assert not completed.stderr


def test_chunk_json_envelope(rpc, capsys):
    rpc.result = {"header": {"chunk_hash": "chunk-hash"}}
    cli.main(["chunk", "chunk-hash", "--json"])
    assert json.loads(capsys.readouterr().out) == {
        "jsonrpc": "2.0",
        "id": "dontcare",
        "result": rpc.result,
    }


def test_account_changes_json_and_block_selection(rpc, capsys):
    rpc.result = {"changes": []}
    cli.main(["account-changes", "a.near", "--block-id", "123", "--json"])
    assert json.loads(capsys.readouterr().out) == rpc.result
    assert json.loads(rpc.requests[0].content)["params"] == {
        "changes_type": "account_changes",
        "account_ids": ["a.near"],
        "block_id": 123,
    }


@pytest.mark.parametrize(
    "environment, options, expected",
    [
        (None, [], "https://dotenv.example"),
        ("https://env.example", [], "https://env.example"),
        (
            None,
            ["--rpc-url", "https://explicit.example"],
            "https://explicit.example",
        ),
    ],
)
def test_cli_dotenv_endpoint(
    rpc, monkeypatch, tmp_path, capsys, environment, options, expected
):
    (tmp_path / ".env").write_text("NEAR_RPC_URL=https://dotenv.example\n")
    if environment is not None:
        monkeypatch.setenv("NEAR_RPC_URL", environment)
    cli.main(["status", "--json", *options])
    assert str(rpc.requests[-1].url) == expected
    assert json.loads(capsys.readouterr().out) == rpc.result


@pytest.mark.parametrize(
    "tokens", [["--help"], ["status", "--help"], ["--version"]]
)
def test_help_does_not_load_dotenv(monkeypatch, tmp_path, capsys, tokens):
    import near.api

    (tmp_path / ".env").write_text("NEAR_RPC_URL=https://dotenv.example\n")
    loader = Mock(side_effect=AssertionError("Help must not load .env"))
    monkeypatch.setattr(near.api, "load_dotenv", loader)
    cli.main(tokens)
    assert capsys.readouterr().out
    loader.assert_not_called()
