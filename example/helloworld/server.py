import asyncio

from grpclib.utils import graceful_exit
from grpclib.server import Server

from .helloworld_pb2 import HelloReply
from .helloworld_grpc import GreeterBase


class Greeter(GreeterBase):

    async def SayHello(self, stream):
        request = await stream.recv_message()
        message = 'Hello, {}!'.format(request.name)
        await stream.send_message(HelloReply(message=message))


async def main(*, host='127.0.0.1', port=50051):
    server = Server([Greeter()], loop=asyncio.get_event_loop())
    await server.start(host, port)
    print('Serving on {}:{}'.format(host, port))
    await graceful_exit([server])


if __name__ == '__main__':
    asyncio.run(main())
