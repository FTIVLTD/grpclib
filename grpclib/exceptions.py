from typing import Optional

from .const import Status


class GRPCError(Exception):

    def __init__(self, status: Status, message: Optional[str] = None) -> None:
        super().__init__(status, message)
        self.status = status
        self.message = message


class ProtocolError(Exception):
    pass


class StreamTerminatedError(Exception):
    pass
