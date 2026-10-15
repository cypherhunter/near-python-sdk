from near.models.block import Block
from near.rpc import RPCConfig, request_rpc


class NearBlock(object):
    def __init__(self, client, near_rpc_url, **kwargs):
        self.id = kwargs.pop("id", "dontcare")
        self.jsonrpc = kwargs.pop("jsonrpc", "2.0")
        self.near_rpc_url = near_rpc_url
        self.client = client
        self._rpc_config = kwargs.pop("rpc_config", None) or RPCConfig()

    def finality(self, finality="final") -> Block:
        _payload = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": "block",
            "params": {"finality": finality},
        }
        _data = request_rpc(
            self.client, self.near_rpc_url, _payload, config=self._rpc_config
        )
        return Block(**_data["result"])

    def block(self, block_id: [int, str, None]) -> Block:
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

        _data = request_rpc(
            self.client, self.near_rpc_url, _payload, config=self._rpc_config
        )
        return Block(**_data["result"])

    def chunk(self, chunk_id: str):
        _payload = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": "chunk",
            "params": {
                "chunk_id": chunk_id,
            },
        }
        return request_rpc(
            self.client, self.near_rpc_url, _payload, config=self._rpc_config
        )


if __name__ == "__main__":
    pass
