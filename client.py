import asyncio
import json
import utils


async def receiver(reader):
    async for msg in utils.messages(reader):
        print(msg)


async def sender(writer):
    for i in range(200):
        await asyncio.sleep(2)
        await utils.send_message(
            writer,
            json.dumps(dict(room='general', msg=f'Hi! {i}')).encode()
        )


async def main():
    # Install signal handlers for shutdown
    shutdown = asyncio.Future()
    utils.install_signal_handling(shutdown)

    # Handle reconnection!
    while True:
        try:
            if shutdown.done():
                return

            print('Connecting...')
            reader, writer = await asyncio.open_connection(host='localhost',
                                                           port=9011)
        except OSError:
            await asyncio.sleep(1.0)
            continue

        # Join a room
        await utils.send_message(
            writer,
            json.dumps(dict(action='join', room='general')).encode()
        )

        rtask = asyncio.create_task(receiver(reader))
        stask = asyncio.create_task(sender(writer))

        done, pending = await asyncio.wait(
            [rtask, stask, shutdown],
            return_when=asyncio.FIRST_COMPLETED)

        rtask.cancel()
        stask.cancel()
        await asyncio.gather(rtask, stask, return_exceptions=True)


if __name__ == '__main__':
    asyncio.run(main())
