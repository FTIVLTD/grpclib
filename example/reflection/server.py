import asyncio

from grpclib.utils import graceful_exit
from grpclib.server import Server
from grpclib.reflection.service import ServerReflection

from helloworld.server import Greeter


async def main(*, host='127.0.0.1', port=50051):
    services = [Greeter()]
    services = ServerReflection.extend(services)

    server = Server(services, loop=asyncio.get_event_loop())
    await server.start(host, port)
    print('Serving on {}:{}'.format(host, port))
    await graceful_exit([server])


if __name__ == '__main__':
    asyncio.run(main())
