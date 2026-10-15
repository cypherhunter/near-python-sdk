# near-python-sdk

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## TODO

- [x] Browser Accounts / Contracts
- [ ] Block / Chunk
- [x] Browser Gas
- [ ] Config Protocol
- [x] Browser Near Network Info
- [ ] Browser Transactions
- [ ] Handling error messages
- [x] Support CLI

## Setup Near RPC

```.bash
export NEAR_RPC_URL=https://rpc.testnet.near.org
```

[https://docs.near.org/docs/api/rpc](https://docs.near.org/docs/api/rpc)

## Usage

```.python
from near.api import NearAPI

near_api = NearAPI()

res = near_api.call_contract_func(
  account_id="dev-1588039999690",
  method_name="get_num",
  args={},
)
```

---

### Network

```.python
from near.api import NearAPI

# fetch near validiators
res = near_api.network.validators()

res = near_api.call_contract_func(
  account_id="nearfans.poolv1.near",
  method_name="get_reward_fee_fraction",
  args=[]
)

{
	'block_hash': 'J13uE8vwQAGDeecNBVXMCZxUZXYv3crN8XY5gSfuTZsk',
 	'block_height': 57574416,
  	'logs': [],
  	'result': {'denominator': 100, 'numerator': 3}
}

```

### CLI

```.bash
python  near/main.py view_account root.near
Amount: 8566.744926870419
Locked: 0.0
Storage Usage: 26564
```

### Error handling

All RPC methods raise `NearException` for JSON-RPC errors, HTTP or connection
failures, and invalid RPC response envelopes. For JSON-RPC errors, `.error`
contains the original error payload (including code, message, and details).
Transport and JSON decoding failures retain the underlying exception as
`__cause__`.

```python
from near.api import NearAPI
from near.exceptions import NearException

try:
    result = NearAPI().view_account("example.near")
except NearException as exc:
    print(exc.error)
```

`view_account_change()` now raises on RPC errors instead of returning an error
dictionary, and `chunk()` raises instead of logging and returning `None`.
Successful return values keep their existing format.

### Tests

```bash
uv sync --dev
uv run python -m pytest
```

Tests use mocked RPC responses and do not require network access.
