class DomainError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        self.code = code
        self.message = message
        self.status = status


class GraphChanged(Exception):
    """Internal signal: release every lock and retry the whole transaction."""
