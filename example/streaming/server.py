import asyncio

from grpclib.utils import graceful_exit
from grpclib.server import Server

from .helloworld_pb2 import HelloReply
from .helloworld_grpc import GreeterBase


class Greeter(GreeterBase):

    # UNARY_UNARY - simple RPC
    async def UnaryUnaryGreeting(self, stream):
        request = await stream.recv_message()
        message = 'Hello, {}!'.format(request.name)
        await stream.send_message(HelloReply(message=message))

    # UNARY_STREAM - response streaming RPC
    async def UnaryStreamGreeting(self, stream):
        request = await stream.recv_message()
        await stream.send_message(
            HelloReply(message='Hello, {}!'.format(request.name)))
        await stream.send_message(
            HelloReply(message='Goodbye, {}!'.format(request.name)))

    # STREAM_UNARY - request streaming RPC
    async def StreamUnaryGreeting(self, stream):
        names = []
        async for request in stream:
            names.append(request.name)
        message = 'Hello, {}!'.format(' and '.join(names))
        await stream.send_message(HelloReply(message=message))

    # STREAM_STREAM - bidirectional streaming RPC
    async def StreamStreamGreeting(self, stream):
        async for request in stream:
            message = 'Hello, {}!'.format(request.name)
            await stream.send_message(HelloReply(message=message))
        # Send another message to demonstrate responses are not
        # coupled to requests.
        message = 'Goodbye, all!'
        await stream.send_message(HelloReply(message=message))


async def main(*, host='127.0.0.1', port=50051):
    server = Server([Greeter()], loop=asyncio.get_event_loop())
    await server.start(host, port)
    print('Serving on {}:{}'.format(host, port))
    await graceful_exit([server])


if __name__ == '__main__':
    asyncio.run(main())
