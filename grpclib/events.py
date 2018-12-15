from collections import defaultdict


class Event:
    __slots__ = ()


class LoadedEvent(Event):
    __slots__ = Event.__slots__ + ('payload', 'intercepted')

    def __init__(self, payload):
        self.payload = payload
        self.intercepted = False

    def intercept(self, value):
        self.payload = value
        self.intercepted = True

    def replace(self, value):
        self.payload = value


async def _ident(payload, **kwargs):
    return payload


def _dispatches(event_type):
    def decorator(func):
        func.__dispatches__ = event_type
        return func
    return decorator


class _Dispatch:
    __dispatch_methods__ = {}

    def __init__(self):
        self._listeners = defaultdict(list)
        for name in self.__dispatch_methods__.values():
            self.__dict__[name] = _ident

    def add_listener(self, event_type, callback):
        self.__dict__.pop(self.__dispatch_methods__[event_type], None)
        self._listeners[event_type].append(callback)

    async def __dispatch__(self, event):
        for callback in self._listeners[event.__class__]:
            await callback(event)
            if event.intercepted:
                break
        return event.payload


class _DispatchMeta(type):

    def __new__(mcs, name, bases, params):
        dispatch_methods = {}
        for key, value in params.items():
            dispatches = getattr(value, '__dispatches__', None)
            if dispatches is not None:
                assert (isinstance(dispatches, type)
                        and issubclass(dispatches, Event)), dispatches
                assert dispatches not in dispatch_methods, dispatches
                dispatch_methods[dispatches] = key
        params['__dispatch_methods__'] = dispatch_methods
        return super().__new__(mcs, name, bases, params)


def listen(target, event_type, callback):
    """Register a listener function for the given target and event type

    .. code-block:: python

        async def callback(event: RequestReceived):
            print(event.payload)

        listen(server, RequestReceived, callback)
    """
    target.__dispatch__.add_listener(event_type, callback)


class RequestReceived(LoadedEvent):
    """Dispatches when request was received and a task was launched to handle
    this request

    .. py:attribute:: payload

        Request headers as a mutable MultiDict

    """
    __slots__ = LoadedEvent.__slots__ + ()


class CallHandler(LoadedEvent):
    __slots__ = LoadedEvent.__slots__ + ('name',)

    def __init__(self, payload, *, name):
        super().__init__(payload)
        self.name = name


class DispatchServerEvents(_Dispatch, metaclass=_DispatchMeta):

    @_dispatches(RequestReceived)
    async def request_received(self, payload):
        return await self.__dispatch__(RequestReceived(payload))

    @_dispatches(CallHandler)
    async def call_handler(self, payload, *, name):
        return await self.__dispatch__(CallHandler(payload, name=name))


class SendRequest(LoadedEvent):
    """Dispatches before sending request

    .. py:attribute:: payload

        Request metadata as a mutable MultiDict

    """
    __slots__ = LoadedEvent.__slots__ + ()


class DispatchChannelEvents(_Dispatch, metaclass=_DispatchMeta):

    @_dispatches(SendRequest)
    async def send_request(self, payload):
        return await self.__dispatch__(SendRequest(payload))
