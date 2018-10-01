import asyncio
import json
import ssl

import utils
from tkinter import *
from tkinter.ttk import *


async def receiver(reader, add_item=None):
    async for msg in utils.messages(reader):
        print(msg)
        if add_item:
            print('adding_item')
            add_item(msg)


async def sender(writer):
    for i in range(200):
        await asyncio.sleep(2)
        await utils.send_message(
            writer,
            json.dumps(dict(room='general', msg=f'Hi! {i}')).encode()
        )


async def main(use_signal=True, add_item=None):
    # Install signal handlers for shutdown
    shutdown = asyncio.Future()
    if use_signal:
        utils.install_signal_handling(shutdown)

    # Handle reconnection!
    while True:
        try:
            if shutdown.done():
                return

            print('Connecting...')
            ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            ctx.check_hostname = False
            ctx.load_verify_locations('chat.crt')
            reader, writer = await asyncio.open_connection(
                host='localhost', port=9011, ssl=ctx
            )
        except OSError:
            await asyncio.sleep(1.0)
            continue

        # Join a room
        await utils.send_message(
            writer,
            json.dumps(dict(action='join', room='general')).encode()
        )

        rtask = asyncio.create_task(receiver(reader, add_item))
        stask = asyncio.create_task(sender(writer))

        done, pending = await asyncio.wait(
            [rtask, stask, shutdown],
            return_when=asyncio.FIRST_COMPLETED)

        rtask.cancel()
        stask.cancel()
        await asyncio.gather(rtask, stask, return_exceptions=True)


def uimain():
    root = Tk()
    Grid.rowconfigure(root, 1, weight=1)
    Grid.columnconfigure(root, 0, weight=1)

    Button(root, text="Join Room").grid(row=0, column=0, sticky=W)

    s = Style()
    s.configure('My.TFrame', background='red')
    frame = Frame(master=root, style='My.TFrame')
    frame.grid(row=1, column=0, sticky=N+S+E+W)
    Grid.rowconfigure(frame, 0, weight=1)
    Grid.columnconfigure(frame, 1, weight=1)

    rooms = Listbox(frame).grid(row=0, column=0, sticky=N+S+W+E)

    rhsframe = Frame(frame)
    rhsframe.grid(row=0, column=1, sticky=N+S+E+W)
    Grid.rowconfigure(rhsframe, 0, weight=1)
    Grid.columnconfigure(rhsframe, 0, weight=1)

    msgsd = list()
    msgs = StringVar(value=msgsd)
    messages = Listbox(rhsframe, listvariable=msgs, width=60, height=20)
    messages.grid(row=0, column=0, sticky=N+S+E+W)

    scrollbar = Scrollbar(rhsframe)
    scrollbar.grid(row=0, column=1, sticky=N+S+E)
    messages.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=messages.yview)

    new_message = Entry(master=rhsframe)
    new_message.grid(row=1, column=0, sticky=E+W)


    def add_item(text):
        msgsd.append(text)
        msgs.set(msgsd)

    def run_thread():
        asyncio.run(main(use_signal=False, add_item=add_item))

    import threading
    thread = threading.Thread(target=run_thread, daemon=True)
    thread.start()
    root.mainloop()


if __name__ == '__main__':
    uimain()
