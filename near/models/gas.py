from decimal import Decimal


class GasPrice(object):
    decimal = 24

    def __init__(self, **kwargs):
        if "result" in kwargs:
            _result = kwargs.pop("result")
            self.gas_price = Decimal(_result.get("gas_price")) / Decimal(
                10**self.decimal
            )

    def __repr__(self) -> str:
        return f"{self.gas_price:.24f}"
