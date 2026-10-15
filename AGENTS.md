# AGENTS.md — near-python-sdk

## Project overview

Synchronous Python SDK for read-only NEAR JSON-RPC queries: accounts, blocks,
chunks, validators, gas prices, network information, and contract view calls.
Python 3.10+ is required. Preserve existing SDK method names and successful
return formats when changing transport or CLI behavior.

## Setup and entry points

```bash
uv sync --dev
uv run near-rpc --help
uv run near-rpc status --json
uv run python -m near.main --help
```

- Library: `from near.api import NearAPI`.
- CLI: `near-rpc` and `python -m near.main`; explicit Cyclopts commands.
- Dependencies: `httpx[socks]>=0.28,<1`, `cyclopts>=4,<5`, and
  `python-dotenv>=1,<2`.
- Package metadata and dependency declarations: `pyproject.toml`.
- Dependencies and development tools are managed with uv; commit `uv.lock` updates.

## Code map

| File | Responsibility |
| --- | --- |
| `near/api.py` | `NearAPI`, `BaseAPI`, payload generation, contract result decoding, client ownership |
| `near/rpc.py` | HTTPX requests, `RPCConfig`, retry allowlists, JSON-RPC envelope validation |
| `near/block.py` | `NearBlock`: block and chunk queries |
| `near/network.py` | `NearNetwork`: status, peers, validators |
| `near/exceptions.py` | Public `NearException` and its original `.error` payload |
| `near/main.py` | Cyclopts `app`, explicit query commands, output formatting, `main` entry point |
| `near/models/` | Existing account, gas, block, and chunk response models |
| `tests/test_rpc.py` | Transport, SDK compatibility, timeout, retry, and lifecycle tests |
| `tests/test_cli.py` | CLI parsing, help, output, endpoint, and exit code tests |
| `tests/conftest.py` | Block external HTTP transport calls and isolate proxy settings |

## Transport rules

- Centralize HTTP requests in `near/rpc.py`; reuse one synchronous `httpx.Client`
  across `NearAPI`, `NearBlock`, and `NearNetwork`.
- Configure RPC through `NearAPI(rpc_url=..., timeout=..., max_retries=...,
  retry_statuses=..., backoff_factor=..., client=...)`.
- Load `.env` from the current working directory at API initialization, before
  client creation, using python-dotenv without overriding existing environment
  variables. Never load it at module import or for CLI help/version.
- Endpoint precedence: explicit `rpc_url`, existing `NEAR_RPC_URL` environment
  variable, `.env` value, then `https://rpc.mainnet.near.org`.
  Testnet is `https://rpc.testnet.near.org`.
- Defaults: connect timeout 5s; read/write/pool timeouts 15s; 3 additional retry
  attempts; HTTP retry statuses 502/503/504; backoff waits 0.5, 1, then 2s.
- `timeout` accepts HTTPX timeout objects, seconds, or `None` to disable timeouts.
  An injected client retains its timeout unless explicitly overridden.
- Retry only explicitly allowlisted read-only methods and query request types
  on connection errors, connect timeouts, or configured HTTP status errors.
- Never automatically retry unknown methods or transaction submissions. Do not
  retry JSON-RPC errors, malformed responses, or read/write/pool timeouts.
- Validate HTTP status and JSON-RPC 2.0 envelopes, matching response IDs, and
  result/error fields. Raise `NearException` consistently for RPC failures;
  retain raw application error payloads and chain underlying transport/JSON errors.
- `close()` and context manager exit close only SDK-owned clients. Externally
  injected clients remain caller-owned, including when a request fails.
- SOCKS support is included through `httpx[socks]`; SDK-owned clients honor HTTPX
  environment proxy settings.

## SDK compatibility and gotchas

- `view_account()` returns a formatted string, despite its existing annotation.
  `Account.amount` and `Account.locked` are in NEAR, divided by 10²⁴.
- `gas()` returns a formatted string in NEAR. Do not change SDK return types just
  to support CLI formatting.
- Network queries and account changes return dictionaries. Contract calls return
  block information, logs, and a decoded JSON result dictionary.
- Contract arguments must be JSON-serializable dictionaries/lists and are
  base64-encoded. Decode returned bytes as UTF-8 before parsing JSON.
- Account, contract, and account change queries default to `"optimistic"`;
  `NearAPI(finality="final")` selects final data.
- Account changes accept an optional block height/hash, including height 0.
  Send either `block_id` or `finality`, never both.
- Block queries return `Block`; `block.finality()` and `block.block(None)` select
  `"final"` by default. `block.finality("optimistic")` is also supported.
- `chunk()` returns the full JSON-RPC envelope.
- Block model properties print data as a side effect. CLI JSON formatting uses
  stored header/chunk data; avoid unrelated model redesign during CLI work.

## CLI contract

Explicit commands: `status`, `gas`, `validators`, `account`, `block`, `info`,
`chunk`, `account-changes`, and `contract-call`. Register supported commands
explicitly rather than exposing the entire SDK object.

```bash
uv run near-rpc account example.near
uv run near-rpc gas --block 123
uv run near-rpc validators --json
uv run near-rpc block --finality final --json
uv run near-rpc status --rpc-url https://rpc.testnet.near.org --json
uv run near-rpc account-changes example.near --block-id 123 --json
uv run near-rpc contract-call contract.near get_value '{}' --json
uv run near-rpc account --help
uv run near-rpc --version
```

- `--rpc-url` is a command option; precedence is explicit option, environment,
  Mainnet default.
- Root and command-level `--help`/`-h`, and `--version`, must never construct HTTP
  clients or make requests. Keep module import free of client construction.
- Human-readable output is the default. `--json` is available on all query
  commands except `account` and `gas`; output must be valid JSON without extra
  printing from SDK model properties.
- Success exits 0; invalid arguments and RPC failures exit nonzero and report
  errors to stderr. CLI commands release SDK-owned resources on success/failure.
- Keep parameter descriptions readable and document CLI name changes in README.

## Formatting and verification

Black uses a 79-character line length, configured in `pyproject.toml`.

```bash
uv run black .
uv run black --check .
uv run python -m pytest
uv run near-rpc --help
uv build
```

Add or update tests for transport, SDK, or CLI behavior changes. Use
`httpx.MockTransport`; unit tests must run without external network access.
Cover retries and exhaustion, non-retryable failures, exception payloads and
causes, timeout propagation, shared clients, and resource ownership as relevant.
CLI checks should cover parsing, help/version without clients, endpoint priority,
JSON validity, stderr, and exit codes. Documentation-only changes need relevant
example/help checks rather than a new test suite.

## Packaging

- `pyproject.toml` is the source of package metadata; current version is 0.0.3.
- Setuptools is the build backend; `setup.py` delegates to project configuration.
- `[project.scripts]` defines `near-rpc = "near.main:main"`.
- Development tools are declared in the dev dependency group and optional extras.
- Build wheel and source distributions with `uv build`; outputs go to `dist/`.
- `MANIFEST.in` includes test Python files, including `conftest.py`, in the sdist.
- Verify built metadata uses HTTPX/Cyclopts and includes `near.models` and the
  console entry point when changing packaging. Keep README and this file aligned
  with dependencies, commands, defaults, and public behavior.
