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


## Setup Near RPC

```.shell
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

