import logging
from typing import Dict


class NearBlock(object):
    def __init__(self, client, near_rpc_url, **kwargs):
        self.id = kwargs.pop("id", "dontcare")
        self.jsonrpc = kwargs.pop("jsonrpc", "2.0")
        self.near_rpc_url = near_rpc_url
        self.client = client

    def finality(self) -> Dict:
        _payload = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": "block",
            "params": {"finality": "final"},
        }
        _r = self.client.post(self.near_rpc_url, json=_payload)

        return _r.json()["result"]

    def block(self, block_id: [int, str]) -> Dict:
        _payload = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": "block",
            "params": {
                "block_id": block_id,
            },
        }
        _r = self.client.post(self.near_rpc_url, json=_payload)

        if "error" in _r.json():
            logging.error(_r.json()["error"])
            raise
        return _r.json()


if __name__ == "__main__":
    import requests
    from pprint import pprint

    client = requests.Session()
    block = NearBlock(
        client=client, near_rpc_url="https://rpc.testnet.near.org"
    )
    pprint(block.finality(), indent=2)
