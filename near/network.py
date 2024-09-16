class NearNetwork(object):
    def __init__(self, client, near_rpc_url, **kwargs):
        self.id = kwargs.pop("id", "dontcare")
        self.jsonrpc = kwargs.pop("jsonrpc", "2.0")
        self.near_rpc_url = near_rpc_url
        self.client = client

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


if __name__ == "__main__":
    import requests
    from pprint import pprint

    client = requests.Session()
    near_network = NearNetwork(
        client=client, near_rpc_url="https://rpc.testnet.near.org"
    )

    pprint(near_network.status(), indent=2)
    print(
        "================================================================================="
    )
    pprint(near_network.info(), indent=2)
    print(
        "================================================================================="
    )
    pprint(near_network.validators(), indent=2)
