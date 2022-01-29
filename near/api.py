import os
import base64
import json
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from near.exceptions import NearException
from near.network import NearNetwork
from near.models.account import Account

near_rpc_url = os.getenv("NEAR_RPC_URL", "https://rpc.mainnet.near.org")


def parse_near_result(r: list) -> dict:
    data = "".join([chr(i) for i in r])
    return json.loads(data)


class BaseAPI(object):
    near_rpc_url = near_rpc_url
    jsonrpc = "2.0"

    def __init__(self, **kwargs):
        """
        :param kwargs:
        finality: optimistic or final
        """
        self.id = kwargs.pop("id", "dontcare")
        self.finality = kwargs.pop("finality", "optimistic")
        self.client = requests.Session()
        retries = Retry(
            total=5, backoff_factor=0.5, status_forcelist=[502, 503, 504]
        )
        self.client.mount("https://", HTTPAdapter(max_retries=retries))

    def __str__(self):
        return f"NEAR RPC URL: {self.near_rpc_url}"

    def generate_payload(self, method="query", **params) -> dict:
        _params = params.copy()
        _params.update(
            {
                "finality": self.finality,
            }
        )
        return {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": method,
            "params": _params,
        }


class NearAPI(BaseAPI):
    @property
    def network(self) -> NearNetwork:
        _network = NearNetwork(
            client=self.client, near_rpc_url=self.near_rpc_url
        )
        return _network

    def view_account(self, account_id) -> Account:
        params = {"request_type": "view_account", "account_id": account_id}

        _payload = self.generate_payload(**params)

        _r = self.client.post(self.near_rpc_url, json=_payload)

        if "error" in _r.json():
            raise NearException()
        else:
            return Account(**_r.json()["result"])
        # return _r.json()["result"]

    def view_account_change(self, account_ids: list, block_id=None) -> dict:
        params = {
            "changes_type": "account_changes",
            "account_ids": account_ids,
            # "block_id": block_id
        }
        if block_id:
            params.update({"block_id": block_id})
        _payload = self.generate_payload(
            method="EXPERIMENTAL_changes", **params
        )
        _r = self.client.post(self.near_rpc_url, json=_payload)

        if "error" in _r.json():
            return _r.json()["error"]

        return _r.json()["result"]

    def call_contract_func(
        self, account_id, method_name, args: [dict, list]
    ) -> dict:
        args_base64 = base64.b64encode(json.dumps(args).encode("utf-8"))

        params = {
            "request_type": "call_function",
            "account_id": account_id,
            "method_name": method_name,
            "args_base64": args_base64.decode("utf-8"),
        }
        _payload = self.generate_payload(**params)
        _r = self.client.post(self.near_rpc_url, json=_payload)

        _data = _r.json()
        if "error" in _data["result"]:
            return _data["result"]["error"]
        return {
            "block_height": _data["result"]["block_height"],
            "block_hash": _data["result"]["block_hash"],
            "logs": _data["result"]["logs"],
            "result": parse_near_result(_data["result"]["result"]),
        }

    def gas(self, block=None) -> dict:

        _payload = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": "gas_price",
            "params": [block],
        }

        # if block:
        #     _payload.update({"params": [block]})
        _r = self.client.post(near_rpc_url, json=_payload)
        return _r.json()


if __name__ == "__main__":
    from pprint import pprint

    near_api = NearAPI()

    # res = near_api.call_contract_func(
    #     account_id="debionetwork.octopus-registry.near",
    #     method_name="get_validator_rewards_of",
    #     # args={"start_era": "0", "end_era": "41", "delegator_id": "d1-octopus.near", "validator_id": "d1-octopus.near"}
    #     args={
    #         "start_era": "0",
    #         "end_era": "54",
    #         # "delegator_id": "d1.near",
    #         "validator_id": "d1-octopus.near",
    #     },
    # )

    res = near_api.call_contract_func(
        account_id="octopus-registry.near",
        method_name="get_appchain_status_of",
        args={"appchain_id": "debionetwork"},
        # args={"appchain_id": "myriad"},
    )

    # res = near_api.network_status()

    # res = near_api.call_contract_func(
    #     account_id="d1.poolv1.near",
    #     method_name="get_reward_fee_fraction",
    #     args=[],
    # )

    # res = near_api.call_contract_func(
    #     account_id="v2.ref-finance.near",
    #     method_name="get_pool",
    #     # args={"from_index":0,"limit":100},
    #     args={"pool_id": 79},
    # )

    # res = near_api.view_account("nearfans.poolv1.near")
    # metadata = near_api.call_contract_func(
    #     account_id="aaaaaa20d9e0e2461697782ef11675f668207961.factory.bridge.near",
    #     method_name="ft_metadata",
    #     args={},
    # )
    # pprint(metadata, indent=2)
    #
    # res = near_api.call_contract_func(
    #     account_id="aaaaaa20d9e0e2461697782ef11675f668207961.factory.bridge.near",
    #     method_name="ft_total_supply",
    #     args={},
    # )
    # total_supply = res["result"]
    # print(int(total_supply) / 10 ** 18)
    # account = near_api.view_account("jiaxin.near")
    # print(account)

    # pprint(account, indent=2)
    pprint(res, indent=2)
