# near-python-sdk

Synchronous Python SDK and CLI for read-only NEAR JSON-RPC queries. Fetch account,
block, chunk, validator, gas price, network, and contract view data. Requires
Python 3.10 or newer.

- HTTPX provides a shared HTTP connection pool, configurable timeouts, and SOCKS
  proxy support through the included `httpx[socks]` dependency.
- Cyclopts provides explicit CLI commands, parameter help, and argument validation.

## Install and quick start

From this checkout, install the SDK and its `near-rpc` command:

```bash
pip install -e .
near-rpc --help
near-rpc status
```

For development with uv:

```bash
uv sync --dev
uv run near-rpc --help
uv run near-rpc status --json
```

Mainnet is the default. Select Testnet through an environment variable or a
command option:

```bash
export NEAR_RPC_URL=https://rpc.testnet.near.org
near-rpc status
near-rpc status --rpc-url https://rpc.mainnet.near.org --json
```

## SDK usage

```python
from near.api import NearAPI

with NearAPI() as api:
    status = api.network.status()
    validators = api.network.validators()
    gas = api.gas()
    print(status["chain_id"])
    print(gas)
```

The API, block client, and network client reuse one HTTPX client. Context manager
exit closes an SDK-owned client, including when a query raises an exception.
`api = NearAPI()` also works; call `api.close()` when finished.

Existing successful return formats are preserved:

| SDK method | Returns |
| --- | --- |
| `api.view_account(account_id)` | Formatted account balance and storage string |
| `api.view_account_change(account_ids, block_id=None)` | Account changes dictionary |
| `api.call_contract_func(account_id, method_name, args)` | Block information, logs, and decoded JSON result dictionary |
| `api.gas(block=None)` | Formatted gas price string in NEAR |
| `api.network.status()` | Node status dictionary |
| `api.network.info()` | Network information dictionary |
| `api.network.validators(block=None)` | Validator information dictionary |
| `api.block.finality(finality="final")` | `Block` model |
| `api.block.block(block_id)` | `Block` model; `None` selects the latest final block |
| `api.block.chunk(chunk_id)` | Complete JSON-RPC response envelope |

Account balances and gas prices are expressed in NEAR, not yoctoNEAR. Query
finality defaults to `"optimistic"`; configure `NearAPI(finality="final")` to use
final data for account, account change, and contract queries. Block queries
without a height/hash default to `"final"`.

Contract calls are read-only. Arguments must be JSON-serializable dictionaries or
lists; the SDK encodes them as base64 and decodes the returned JSON value.
Replace the contract and method below with values from the selected network:

```python
with NearAPI(finality="final") as api:
    result = api.call_contract_func(
        account_id="contract.near",
        method_name="get_value",
        args={},
    )
    print(result["result"])
```

`view_account_change([...], block_id=123)` selects a height or hash instead of
finality. The request sends only one of `block_id` and `finality`.

## RPC configuration

Each API instance loads `.env` from the current working directory before
creating its HTTP client. This works for both the SDK and CLI; a missing `.env`
is fine. Existing environment variables are never overwritten.

```bash
cp .env.example .env
# Edit .env, for example: NEAR_RPC_URL=https://rpc.testnet.near.org
uv run near-rpc status --json
```

Endpoint priority is an explicit `rpc_url` / `--rpc-url`, then the existing
`NEAR_RPC_URL` environment variable, then `NEAR_RPC_URL` in `.env`, then Mainnet.
Values are loaded at API initialization, not at import or when showing help.
`.env` can also set HTTPX proxy variables such as `HTTPS_PROXY`. Loading uses
`python-dotenv` and adds missing values to the process environment; once loaded,
they are treated as existing environment variables. `.env` is ignored by Git.

| Setting | Default |
| --- | --- |
| RPC endpoint | `https://rpc.mainnet.near.org` |
| Connect timeout | 5 seconds |
| Read, write, and pool timeouts | 15 seconds |
| Additional retry attempts | 3 |
| Retry HTTP statuses | 502, 503, 504 |
| Backoff factor | 0.5 seconds; waits of 0.5, 1, then 2 seconds |

```python
import httpx
from near.api import NearAPI

with NearAPI(
    rpc_url="https://rpc.testnet.near.org",
    timeout=httpx.Timeout(15.0, connect=5.0),
    max_retries=3,
    retry_statuses=(502, 503, 504),
    backoff_factor=0.5,
) as api:
    status = api.network.status()
```

`timeout` accepts an HTTPX timeout, a number of seconds for all timeout phases,
or `None` to disable timeouts. These settings apply to the API and its block and
network clients.

Automatic retries apply only to explicitly allowlisted read-only operations,
on connection errors, connect timeouts, or configured HTTP status errors.
`max_retries=3` permits at most four total attempts; use `max_retries=0` to disable
retries. Read/write/pool timeouts, malformed responses, and JSON-RPC application
errors are not retried. Unknown methods and transaction submission methods are
never automatically retried.

Inject an `httpx.Client` to customize transports, authentication, proxies, or
pooling:

```python
with httpx.Client(timeout=30.0) as client:
    with NearAPI(client=client) as api:
        status = api.network.status()
    # The caller still owns client here.
```

An injected client keeps its timeout unless `NearAPI(timeout=...)` explicitly
overrides it for SDK requests. The SDK never closes an injected client.
HTTPX environment proxy settings also apply to SDK-owned clients; SOCKS support
is included in the project dependencies.

## Error handling

HTTP/connection failures, invalid JSON, and invalid JSON-RPC envelopes raise
`NearException`. Envelope validation checks JSON-RPC 2.0, the response ID, and
result/error fields. JSON-RPC application errors retain their original payload
in `.error`; HTTP and JSON decoding failures retain the underlying exception
in `__cause__`.

```python
from near.api import NearAPI
from near.exceptions import NearException

try:
    with NearAPI() as api:
        account = api.view_account("example.near")
except NearException as exc:
    print(exc.error)
```

## CLI

| Command | Purpose | `--json` |
| --- | --- | --- |
| `status` | Node version, chain, and sync status | Yes |
| `gas [--block HEIGHT_OR_HASH]` | Gas price in NEAR | No |
| `validators [--block HEIGHT_OR_HASH]` | Validators and staking information | Yes |
| `account ACCOUNT_ID` | Account balance and storage usage | No |
| `block [HEIGHT_OR_HASH] [--finality final\|optimistic]` | Block data | Yes |
| `info` | Network peers and connections | Yes |
| `chunk CHUNK_HASH` | Chunk response envelope | Yes |
| `account-changes ACCOUNT_ID... [--block-id HEIGHT_OR_HASH]` | Account changes | Yes |
| `contract-call ACCOUNT_ID METHOD [ARGS_JSON]` | Read-only contract call; arguments default to `{}` | Yes |

Every query command accepts `--rpc-url`. Put it after the command; it overrides
`NEAR_RPC_URL`. Block finality applies when no height/hash is supplied.

```bash
near-rpc --help
near-rpc -h
near-rpc --version
near-rpc account --help
near-rpc account example.near
near-rpc block --finality final --json
near-rpc block 123 --json
near-rpc status --rpc-url https://rpc.testnet.near.org --json
near-rpc account-changes example.near --block-id 123 --json
near-rpc contract-call contract.near get_value '{}' --json
```

Account IDs, contract methods, heights, and hashes must exist on the selected
network. Module execution is also supported:

```bash
python -m near.main --help
python -m near.main status --json
```

Default output is human-readable. `--json` emits valid JSON for the supported
commands; account and gas retain their formatted string output. Help and version
create no HTTP client and send no RPC requests. Successful commands exit with
status 0; argument or RPC failures exit nonzero and write errors to stderr.

The CLI replaces automatic Fire method exposure with explicit command names:
`view_account` becomes `account`, `network validators` becomes `validators`,
`view_account_change` becomes `account-changes`, and `call_contract_func` becomes
`contract-call`. SDK method names and successful return formats remain unchanged.

## Development and packaging

```bash
uv sync --dev
uv run black --check .
uv run black .
uv run python -m pytest
uv run near-rpc --help
uv build
```

Tests use `httpx.MockTransport`; `tests/conftest.py` blocks external HTTP transport
calls and isolates proxy environment variables. The suite covers SDK return
compatibility, envelope validation, retries, timeouts, client ownership, CLI
parsing, endpoint precedence, JSON output, help, and exit codes. Tests need no
NEAR node or external network access.

Package metadata and the console entry point live in `pyproject.toml`.
`setup.py` delegates to that configuration. `uv build` writes a wheel and source
distribution to `dist/`; `MANIFEST.in` includes the test fixtures in the source
package. Commit `uv.lock` when changing dependencies. See `AGENTS.md` for repository
contribution guidance.
