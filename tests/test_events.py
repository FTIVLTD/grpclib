import pytest

from grpclib.events import listen, Event, _Dispatch, _DispatchMeta
from grpclib.events import _dispatches, _ident


class MyEvent(Event):
    __slots__ = Event.__slots__ + ('extra',)

    def __init__(self, payload, *, extra):
        super().__init__(payload)
        self.extra = extra


class DispatchMyEvents(_Dispatch, metaclass=_DispatchMeta):

    @_dispatches(MyEvent)
    async def my_event(self, payload, *, extra):
        return await self.__dispatch__(MyEvent(payload, extra=extra))


@pytest.mark.asyncio
async def test():
    payload = object()

    class Target:
        __dispatch__ = DispatchMyEvents()

    async def callback(event: MyEvent):
        assert event.payload is payload
        assert event.extra == 42

    assert Target.__dispatch__.my_event is _ident
    assert await Target.__dispatch__.my_event(payload, extra=42) is payload

    listen(Target, MyEvent, callback)

    assert Target.__dispatch__.my_event is not _ident
    assert await Target.__dispatch__.my_event(payload, extra=42) is payload
