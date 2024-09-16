import logging
from pprint import pprint
from typing import List
from near.models.block import Block


class NearBlock(object):
    def __init__(self, client, near_rpc_url, **kwargs):
        self.id = kwargs.pop("id", "dontcare")
        self.jsonrpc = kwargs.pop("jsonrpc", "2.0")
        self.near_rpc_url = near_rpc_url
        self.client = client

    def finality(self) -> Block:
        _payload = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": "block",
            "params": {"finality": "final"},
        }
        _r = self.client.post(self.near_rpc_url, json=_payload)

        if "error" in _r.json():
            logging.error(_r.json()["error"])
            raise
        else:
            return Block(**_r.json()["result"])

    def block(self, block_id: List[int, str, None]) -> Block:
        _payload = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": "block",
            # "params": {
            #     "block_id": block_id,
            # },
        }
        if block_id is None:
            _payload.update({"params": {"finality": "final"}})
        else:
            _payload.update(
                {
                    "params": {
                        "block_id": block_id,
                    }
                }
            )

        _r = self.client.post(self.near_rpc_url, json=_payload)

        if "error" in _r.json():
            logging.error(_r.json()["error"])
            raise
        else:
            return Block(**_r.json()["result"])
        # return _r.json()

    def chunk(self, chunk_id: str):
        _payload = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": "chunk",
            "params": {
                "chunk_id": chunk_id,
            },
        }
        _r = self.client.post(self.near_rpc_url, json=_payload)

        if "error" in _r.json():
            _error = _r.json()
            logging.error(_error["error"]["cause"]["info"]["error_message"])
        else:
            return _r.json()


if __name__ == "__main__":
    pass
