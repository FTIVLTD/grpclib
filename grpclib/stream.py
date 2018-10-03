import abc
import struct

from typing import TypeVar, Generic, Type

from .protocol import Stream


RT = TypeVar('RT')
ST = TypeVar('ST')


async def recv_message(stream: Stream, codec, message_type: Type[RT]):
    meta = await stream.recv_data(5)
    if not meta:
        return

    compressed_flag = struct.unpack('?', meta[:1])[0]
    if compressed_flag:
        raise NotImplementedError('Compression not implemented')

    message_len = struct.unpack('>I', meta[1:])[0]
    message_bin = await stream.recv_data(message_len)
    assert len(message_bin) == message_len, \
        '{} != {}'.format(len(message_bin), message_len)
    message = codec.decode(message_bin, message_type)
    return message


async def send_message(stream, codec, message: ST, message_type: Type[ST], *,
                       end=False):
    reply_bin = codec.encode(message, message_type)
    reply_data = (struct.pack('?', False)
                  + struct.pack('>I', len(reply_bin))
                  + reply_bin)
    await stream.send_data(reply_data, end_stream=end)


class StreamIterator(Generic[RT, ST], metaclass=abc.ABCMeta):

    @abc.abstractmethod
    async def recv_message(self) -> RT:
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        message = await self.recv_message()
        if message is None:
            raise StopAsyncIteration()
        else:
            return message
