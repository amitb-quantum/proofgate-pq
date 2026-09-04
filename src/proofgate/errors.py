class GateError(Exception):
    """Stable, non-secret rejection code for untrusted input boundaries."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def require(condition: bool, code: str) -> None:
    if not condition:
        raise GateError(code)
