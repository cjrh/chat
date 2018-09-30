import asyncio
from collections import defaultdict
from weakref import WeakValueDictionary
import json
import utils
from pprint import pprint


WRITERS = WeakValueDictionary()
ROOMS = defaultdict(WeakValueDictionary)


async def sender(addr, writer, room, msg):
    try:
        await utils.send_message(
            writer,
            json.dumps(dict(room=room, msg=msg)).encode()
        )
    except (ConnectionAbortedError, ConnectionResetError):
        """ Connection is dead, remove it."""
        if addr in WRITERS:
            print(f'deleting {addr} from WRITERS')
            del WRITERS[addr]
        if addr in ROOMS[room]:
            print(f'deleting {addr} from ROOMS[{room}]')
            del ROOMS[room][addr]


def send_to_room(from_addr, room: str, msg: str):
    """Send the message to all clients in the room."""
    for addr, writer in ROOMS[room].items():
        print(f'Sending message to {addr} in room {room}: {msg}')
        asyncio.create_task(sender(addr, writer, room, msg))


async def client_connected_cb(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f'New connection from {addr}')
    WRITERS[addr] = writer
    async for msg in utils.messages(reader):
        print(f'Received bytes: {msg}')
        d = json.loads(msg)
        print(f'Received msg: {d}')
        if d.get('action') == 'join':
            ROOMS[d['room']][addr] = writer
        elif d.get('action') == 'leave':
            del ROOMS[d['room']][addr]
        else:
            d['from'] = addr
            send_to_room(addr, d['room'], d['msg'])


async def main():
    server = await asyncio.start_server(
        client_connected_cb=client_connected_cb,
        host='localhost',
        port='9011',
    )
    shutdown = asyncio.Future()
    utils.install_signal_handling(shutdown)
    print('listening...')
    async with server:
        done, pending = await asyncio.wait(
            [server.serve_forever(), shutdown],
            return_when=asyncio.FIRST_COMPLETED
        )
        if shutdown.done():
            return


if __name__ == '__main__':
    asyncio.run(main())
