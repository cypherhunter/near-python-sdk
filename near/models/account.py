class Account(object):
    def __init__(self, **kwargs):
        self._amount = int(kwargs.pop("amount", 0))
        self._locked = int(kwargs.pop("locked", 0))
        self.code_hash = kwargs.pop("code_hash", "")
        self.storage_usage = kwargs.pop("storage_usage", 0)
        self.storage_paid_at = kwargs.pop("storage_paid_at", 0)
        self.block_height = kwargs.pop("block_height", 0)
        self.block_hash = kwargs.pop("block_hash", "")

    def __str__(self):
        return f"Amount: {self.amount}\nLocked: {self.locked}\nStorage Usage: {self.storage_usage}"

    @property
    def amount(self) -> int:
        return self._amount / 10 ** 24

    @property
    def locked(self) -> int:
        return self._locked / 10 ** 24
