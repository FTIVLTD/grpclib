import sys
import time
import signal
import asyncio
import subprocess

import pytest

from grpclib.metadata import Deadline
from grpclib.utils import Wrapper, DeadlineWrapper


class CustomError(Exception):
    pass


class UserAPI:

    def __init__(self, wrapper):
        self.wrapper = wrapper

    async def foo(self, *, time=.0001):
        with self.wrapper:
            await asyncio.sleep(time)


@pytest.mark.asyncio
async def test_wrapper(loop):
    api = UserAPI(Wrapper())
    await api.foo()

    loop.call_soon(lambda: api.wrapper.cancel(CustomError('Some explanation')))

    with pytest.raises(CustomError) as err:
        await api.foo()
    err.match('Some explanation')

    with pytest.raises(CustomError):
        await api.foo()


@pytest.mark.asyncio
async def test_deadline_wrapper(loop):
    deadline = Deadline.from_timeout(0.01)
    deadline_wrapper = DeadlineWrapper()
    api = UserAPI(deadline_wrapper)

    with deadline_wrapper.start(deadline, loop=loop):
        await api.foo(time=0.0001)

        with pytest.raises(asyncio.TimeoutError) as err:
            await api.foo(time=0.1)
        assert err.match('Deadline exceeded')

        with pytest.raises(asyncio.TimeoutError) as err:
            await api.foo(time=0.0001)
        assert err.match('Deadline exceeded')


SCRIPT = """
import asyncio

from grpclib.utils import graceful_exit
from grpclib.server import Server

async def main():
    server = Server([], loop=asyncio.get_event_loop())
    await server.start('127.0.0.1')
    print("Started!")
    await graceful_exit([server])

asyncio.run(main())
"""


@pytest.mark.skipif(sys.version_info < (3, 7, 0), reason='Python < 3.7.0')
@pytest.mark.parametrize('sig_num', [signal.SIGINT, signal.SIGTERM])
def test_graceful_exit(sig_num):
    cmd = [sys.executable, '-u', '-c', SCRIPT]
    with subprocess.Popen(cmd, stdout=subprocess.PIPE) as proc:
        try:
            assert proc.stdout.readline() == b'Started!\n'
            time.sleep(0.001)
            proc.send_signal(sig_num)
            assert proc.wait(1) == 128 + sig_num
        finally:
            if proc.returncode is None:
                proc.kill()
