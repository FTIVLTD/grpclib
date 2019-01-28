import sys
import signal
import asyncio

from contextlib import contextmanager


if sys.version_info > (3, 7):
    _current_task = asyncio.current_task
else:
    _current_task = asyncio.Task.current_task


class Wrapper:
    """Special wrapper for coroutines to wake them up in case of some error.

    Example:

    .. code-block:: python

        w = Wrapper()

        async def blocking_call():
            with w:
                await asyncio.sleep(10)

        # and somewhere else:
        w.cancel(NoNeedToWaitError('With explanation'))

    """
    _error = None
    _task = None

    cancelled = None

    def __enter__(self):
        if self._task is not None:
            raise RuntimeError('Concurrent call detected')

        if self._error is not None:
            raise self._error

        self._task = _current_task()
        assert self._task is not None, 'Called not inside a task'

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._task = None
        if self._error is not None:
            raise self._error

    def cancel(self, error):
        self._error = error
        if self._task is not None:
            self._task.cancel()
        self.cancelled = True


class DeadlineWrapper(Wrapper):
    """Deadline wrapper to specify deadline once for any number of awaiting
    method calls.

    Example:

    .. code-block:: python

        dw = DeadlineWrapper()

        with dw.start(deadline):
            await handle_request()

        # somewhere during request handling:

        async def blocking_call():
            with dw:
                await asyncio.sleep(10)

    """
    @contextmanager
    def start(self, deadline, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        timeout = deadline.time_remaining()
        if not timeout:
            raise asyncio.TimeoutError('Deadline exceeded')

        def callback():
            self.cancel(asyncio.TimeoutError('Deadline exceeded'))

        timer = loop.call_later(timeout, callback)
        try:
            yield self
        finally:
            timer.cancel()


def _service_name(service):
    methods = service.__mapping__()
    method_name = next(iter(methods), None)
    assert method_name is not None
    _, service_name, _ = method_name.split('/')
    return service_name


def _signal_handler(sig_num):
    raise SystemExit(128 + sig_num)


async def graceful_exit(servers, *,
                        signals=frozenset({signal.SIGINT, signal.SIGTERM})):
    """Utility coroutine to properly close servers when receive OS signals

    It waits indefinitely until process receives ``SIGINT`` or ``SIGTERM``
    signal (by default). Then it properly closes servers and
    :py:class:`python:asyncio.CancelledError` is propagated up
    by the call stack (this is OK).

    Example:

    .. code-block:: python

        async def main():
            ...
            server = Server(handlers, loop=loop)
            await server.start(host, port)
            await graceful_exit([server])

    This coroutine is designed to work with :py:func:`python:asyncio.run`
    function, introduced in Python 3.7:

    .. code-block:: python

        if __name__ == '__main__':
            asyncio.run(main())

    .. note:: This coroutine exits if one of the servers closes unexpectedly
      for whatever reason. So a process supervisor will be able to restart
      our process and recover from some temporary error or notify
      about our failure.

    :param servers: list of servers
    :param signals: set of the OS signals to handle
    """
    loop = asyncio.get_event_loop()
    for sig_num in signals:
        loop.add_signal_handler(sig_num, _signal_handler, sig_num)
    try:
        await asyncio.wait({server.wait_closed() for server in servers},
                           return_when=asyncio.FIRST_COMPLETED)
    finally:
        for sig_num in signals:
            loop.remove_signal_handler(sig_num)
        for server in servers:
            server.close()
        await asyncio.gather(*[server.wait_closed() for server in servers])
