from near.rpc import RPCConfig, request_rpc


class NearNetwork(object):
    def __init__(self, client, near_rpc_url, **kwargs):
        self.id = kwargs.pop("id", "dontcare")
        self.jsonrpc = kwargs.pop("jsonrpc", "2.0")
        self.near_rpc_url = near_rpc_url
        self.client = client
        self._rpc_config = kwargs.pop("rpc_config", None) or RPCConfig()

    def __repr__(self):
        r = self.status()
        _info = f"NEAR Protocol\nVersion: {r['version']['version']}\n"
        _info += f"Build: {r['version']['build']}\n"
        _info += f"ChainId: {r['chain_id']}"
        return _info

    def __len__(self):
        r = self.validators()
        return len(r["current_validators"])

    def status(self) -> dict:
        _payload = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": "status",
            "params": [],
        }
        _data = request_rpc(
            self.client, self.near_rpc_url, _payload, config=self._rpc_config
        )
        return _data["result"]

    def info(self) -> dict:
        _payload = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": "network_info",
            "params": [],
        }

        _data = request_rpc(
            self.client, self.near_rpc_url, _payload, config=self._rpc_config
        )
        return _data["result"]

    def validators(self, block=None) -> dict:
        _payload = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": "validators",
            "params": [block],
        }
        _data = request_rpc(
            self.client, self.near_rpc_url, _payload, config=self._rpc_config
        )
        return _data["result"]
