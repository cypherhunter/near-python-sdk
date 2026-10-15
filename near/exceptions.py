class NearException(Exception):
    """RPC failure, retaining the original error payload in ``error``."""

    def __init__(self, error=None):
        self.error = error
        super().__init__(error)
