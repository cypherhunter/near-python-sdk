from decimal import Decimal
from typing import List


class ChunkHeader(object):
    decimal = 24

    def __init__(self, **kwargs):
        self._balance_burnt = kwargs.pop("balance_burnt", 0)
        self.chunk_hash = kwargs.pop("chunk_hash", "")
        self.prev_block_hash = kwargs.pop("prev_block_hash", "")
        self.prev_state_root = kwargs.pop("prev_state_root", "")
        self.rent_paid = kwargs.pop("rent_paid", 0)
        self.shard_id = kwargs.pop("shard_id", 0)
        self.signature = kwargs.pop("signature", "")
        self.tx_root = kwargs.pop("tx_root", "")

    def __str__(self):
        return (
            f"Balance Burnt: {self.balance_burnt}\nShard id: {self.shard_id}"
        )

    @property
    def balance_burnt(self) -> Decimal:
        _balance_burnt = Decimal(self._balance_burnt)
        return _balance_burnt / Decimal(10**self.decimal)


class Receipt(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __str__(self):
        return f"{self.receipt_id}"


class Chunk(object):
    def __init__(self, **kwargs):
        self.author = kwargs.pop("author", "")
        self._header = kwargs.pop("header", {})
        self._receipts = kwargs.pop("receipts", [])

    @property
    def header(self) -> ChunkHeader:
        return ChunkHeader(**self._header)

    @property
    def receipts(self) -> List:
        return [Receipt(**receipt) for receipt in self._receipts]
