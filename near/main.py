"""Explicit Cyclopts commands for read-only NEAR RPC operations."""

import json as jsonlib
import sys
from importlib.metadata import version
from pprint import pformat
from typing import Annotated, Literal

from cyclopts import App, Parameter

from near.api import NearAPI
from near.exceptions import NearException
from near.models.block import Block

RPCURL = Annotated[
    str | None,
    Parameter(
        env_var="NEAR_RPC_URL",
        help="RPC endpoint (defaults to Mainnet; overrides NEAR_RPC_URL).",
    ),
]
JSONOutput = Annotated[
    bool, Parameter(name="--json", help="Print machine-readable JSON.")
]
BlockID = Annotated[
    int | str | None,
    Parameter(help="Block height or hash; omit to select by finality."),
]

app = App(
    name="near-rpc",
    help="Read blockchain data from NEAR JSON-RPC.",
    version=lambda: version("near-python-sdk"),
    help_flags=("--help", "-h"),
    result_action="return_value",
)


def _output(value, as_json=False):
    if isinstance(value, Block):
        # Use the stored data to avoid the model's printing properties and
        # retain all block fields in JSON without changing the SDK model.
        value = {
            "author": value.author,
            "header": value._header,
            "chunks": value._chunks,
        }
    if as_json:
        print(jsonlib.dumps(value, ensure_ascii=False))
    elif isinstance(value, str):
        print(value)
    else:
        print(pformat(value, sort_dicts=False))


@app.command
def status(*, rpc_url: RPCURL = None, json: JSONOutput = False):
    """Show node version, chain, and sync status."""
    with NearAPI(rpc_url=rpc_url) as api:
        _output(api.network.status(), json)


@app.command
def gas(*, block: BlockID = None, rpc_url: RPCURL = None):
    """Show the gas price in NEAR at a block (latest by default)."""
    with NearAPI(rpc_url=rpc_url) as api:
        _output(api.gas(block))


@app.command
def validators(
    *,
    block: BlockID = None,
    rpc_url: RPCURL = None,
    json: JSONOutput = False,
):
    """Show validators and staking information."""
    with NearAPI(rpc_url=rpc_url) as api:
        _output(api.network.validators(block), json)


@app.command
def account(
    account_id: Annotated[str, Parameter(help="NEAR account ID to inspect.")],
    *,
    rpc_url: RPCURL = None,
):
    """Show account balance in NEAR and storage usage."""
    with NearAPI(rpc_url=rpc_url) as api:
        _output(api.view_account(account_id))


@app.command
def block(
    block_id: BlockID = None,
    *,
    finality: Annotated[
        Literal["final", "optimistic"],
        Parameter(help="Finality to use when no block height/hash is given."),
    ] = "final",
    rpc_url: RPCURL = None,
    json: JSONOutput = False,
):
    """Show a block by height, hash, or finality."""
    with NearAPI(rpc_url=rpc_url) as api:
        result = (
            api.block.finality(finality)
            if block_id is None
            else api.block.block(block_id)
        )
        _output(result, json)


@app.command
def info(*, rpc_url: RPCURL = None, json: JSONOutput = False):
    """Show network peers and connections."""
    with NearAPI(rpc_url=rpc_url) as api:
        _output(api.network.info(), json)


@app.command
def chunk(
    chunk_id: Annotated[str, Parameter(help="Chunk hash to inspect.")],
    *,
    rpc_url: RPCURL = None,
    json: JSONOutput = False,
):
    """Show a chunk's JSON-RPC response envelope."""
    with NearAPI(rpc_url=rpc_url) as api:
        _output(api.block.chunk(chunk_id), json)


@app.command
def account_changes(
    account_ids: Annotated[
        list[str], Parameter(help="One or more NEAR account IDs.")
    ],
    *,
    block_id: BlockID = None,
    rpc_url: RPCURL = None,
    json: JSONOutput = False,
):
    """Show account changes at a block (optimistic by default)."""
    with NearAPI(rpc_url=rpc_url) as api:
        _output(api.view_account_change(account_ids, block_id), json)


@app.command
def contract_call(
    account_id: Annotated[str, Parameter(help="Contract's NEAR account ID.")],
    method_name: Annotated[str, Parameter(help="View method to call.")],
    args: Annotated[
        str, Parameter(help="Method arguments as a JSON object or array.")
    ] = "{}",
    *,
    rpc_url: RPCURL = None,
    json: JSONOutput = False,
):
    """Call a read-only contract method."""
    try:
        decoded = jsonlib.loads(args)
    except ValueError as exc:
        raise ValueError("args must be a JSON object or array") from exc
    if not isinstance(decoded, (dict, list)):
        raise ValueError("args must be a JSON object or array")
    with NearAPI(rpc_url=rpc_url) as api:
        _output(api.call_contract_func(account_id, method_name, decoded), json)


def main(tokens=None):
    """Run the CLI, reporting RPC failures on stderr with exit status 1."""
    try:
        app(tokens)
    except (NearException, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
