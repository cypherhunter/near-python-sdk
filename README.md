# near-python-sdk

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)






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
