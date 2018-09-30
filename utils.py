import sys
from asyncio import (StreamReader, StreamWriter, IncompleteReadError, Future,
    get_running_loop)
from signal import signal, SIGBREAK, SIGTERM, SIGINT
from typing import AsyncGenerator


async def messages(reader: StreamReader) -> AsyncGenerator[bytes, None]:
    try:
        while True:
            size_prefix = await reader.readexactly(4)
            size = int.from_bytes(size_prefix, byteorder='little')
            message = await reader.readexactly(size)
            yield message
    except (IncompleteReadError, ConnectionAbortedError, ConnectionResetError):
        return


async def send_message(writer: StreamWriter, message: bytes):
    if not message:
        writer.close()
        await writer.wait_closed()
        return
    size_prefix = len(message).to_bytes(4, byteorder='little')
    writer.write(size_prefix)
    writer.write(message)
    await writer.drain()


def install_signal_handling(fut: Future):
    """Given future will be set a signal is received. This
    can be used to control the shutdown sequence."""
    if sys.platform == 'win32':
        sigs = SIGBREAK, SIGINT
        loop = get_running_loop()

        def busyloop():
            """Required to handle CTRL-C quickly on Windows"""
            loop.call_later(0.1, busyloop)

        loop.call_later(0.1, busyloop)
    else:
        sigs = SIGTERM, SIGINT

    # Signal handlers. Windows is a bit tricky
    for s in sigs:
        signal(
            s,
            lambda *args: loop.call_soon_threadsafe(fut.set_result, None)
        )
