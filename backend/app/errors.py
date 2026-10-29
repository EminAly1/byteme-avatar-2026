class DomainError(Exception):
    def __init__(self, code: str, message: str, status: int = 409, details: dict | None = None):
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}


class GraphChanged(Exception):
    """Internal signal: release every lock and retry the whole transaction."""
