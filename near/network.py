class NearNetwork(object):
    def __init__(self, client, near_rpc_url, **kwargs):
        self.id = kwargs.pop("id", "dontcare")
        self.jsonrpc = kwargs.pop("jsonrpc", "2.0")
        self.near_rpc_url = near_rpc_url
        self.client = client

    def status(self) -> dict:
        _payload = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": "status",
            "params": [],
        }
        _r = self.client.post(self.near_rpc_url, json=_payload)

        return _r.json()["result"]

    def info(self) -> dict:
        _payload = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": "network_info",
            "params": [],
        }

        _r = self.client.post(self.near_rpc_url, json=_payload)

        return _r.json()["result"]

    def validators(self, block=None) -> dict:
        _payload = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": "validators",
            "params": [block],
        }
        _r = self.client.post(self.near_rpc_url, json=_payload)

        return _r.json()["result"]
