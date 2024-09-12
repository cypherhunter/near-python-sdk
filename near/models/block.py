from decimal import Decimal
from datetime import datetime
from typing import List
from near.models.chunk import ChunkHeader


class BlockHeader(object):
    decimal = 24

    def __init__(self, **kwargs):
        self.approvals = kwargs.pop("approvals", [])
        self.height = kwargs.pop("height", 0)
        self.prev_height = kwargs.pop("prev_height", 0)
        self.hash = kwargs.pop("hash", "")
        self.prev_hash = kwargs.pop("prev_hash", "")
        self._gas_price = kwargs.pop("gas_price", 0)
        self._total_supply = kwargs.pop("total_supply", 0)
        self.timestamp = kwargs.pop("timestamp", 0)

    def __str__(self):
        return (
            f"Height: {self.height}\n"
            f"Hash: {self.hash}\n"
            f"Gas Price: {self.gas_price}\n"
            f"Total Supply: {self.total_supply}\n"
            f"Date: {self.date}"
        )

    @property
    def total_supply(self) -> Decimal:
        total_supply = Decimal(self._total_supply)
        return total_supply / Decimal(10**self.decimal)

    @property
    def gas_price(self) -> Decimal:
        gas_price = Decimal(self._gas_price)
        return gas_price / Decimal(10**self.decimal)

    @property
    def date(self):
        return datetime.fromtimestamp(self.timestamp / 10**9)


class Block(object):
    def __init__(self, **kwargs):
        self.author = kwargs.pop("author")
        self._header = kwargs.pop("header", {})
        self._chunks = kwargs.pop("chunks", [])

    def __str__(self):
        return f"Author: {self.author}\nBlock Height: {self.header.height}\nBlock Hash: {self.header.hash}"

    @property
    def header(self):
        _header = BlockHeader(**self._header)
        return _header

    @property
    def chunks(self) -> List:
        return [ChunkHeader(**chunk) for chunk in self._chunks]
