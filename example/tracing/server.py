import uuid
import asyncio
import logging
import contextvars

from grpclib.server import Server
from grpclib.events import listen, RequestReceived

from helloworld.server import serve
from helloworld.helloworld_pb2 import HelloReply
from helloworld.helloworld_grpc import GreeterBase


log = logging.getLogger(__name__)

request_id = contextvars.ContextVar('x-request-id')


class Greeter(GreeterBase):

    async def SayHello(self, stream):
        log.info('Request ID: %s', request_id.get('NA'))
        request = await stream.recv_message()
        message = 'Hello, {}!'.format(request.name)
        await stream.send_message(HelloReply(message=message))


async def request_received(event: RequestReceived):
    r_id = event.payload.get('x-request-id') or str(uuid.uuid4())
    request_id.set(r_id)


async def main():
    server = Server([Greeter()], loop=asyncio.get_event_loop())
    listen(server, RequestReceived, request_received)
    await serve(server)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
