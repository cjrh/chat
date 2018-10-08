import asyncio
import json
import ssl
import queue

import utils
from tkinter import *
from tkinter.ttk import *


async def receiver(reader, queue_ui):
    async for msg in utils.messages(reader):
        d = json.loads(msg)
        print(d)
        queue_ui.put(d, block=False)


async def sender(writer, room='general', msg='hi!'):
    await utils.send_message(
        writer,
        json.dumps(dict(room=room, msg=msg)).encode()
    )


async def handle_io(queue_io: queue.Queue, writer):
    while True:
        try:
            data = queue_io.get(block=False)
        except queue.Empty:
            await asyncio.sleep(0.1)
        else:
            if all(k in data for k in ['room', 'msg']):
                await sender(writer, data['room'], data['msg'])


async def main(use_signal=True, queue_ui=None, queue_io=None):
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

        rtask = asyncio.create_task(receiver(reader, queue_ui))
        stask = asyncio.create_task(handle_io(queue_io, writer))

        done, pending = await asyncio.wait(
            [rtask, stask, shutdown],
            return_when=asyncio.FIRST_COMPLETED)

        rtask.cancel()
        stask.cancel()
        await asyncio.gather(rtask, stask, return_exceptions=True)


def make_style(name, color):
    s = Style()
    s.configure(name, background=color)
    return name


def uimain():
    root = Tk()
    if sys.platform.startswith('linux'):
        s = Style()
        s.theme_use('clam')
    Grid.rowconfigure(root, 1, weight=1)
    Grid.columnconfigure(root, 0, weight=1)

    Button(root, text="Join Room").grid(row=0, column=0, sticky=W)

    frame = Frame(master=root, style=make_style('My.TFrame', 'red'),
                  width=100, padding=5)
    frame.grid(row=1, column=0, sticky=N+S+E+W)
    Grid.rowconfigure(frame, 0, weight=1)
    Grid.columnconfigure(frame, 1, weight=1)

    room_items = ['general']
    room_var = StringVar(value=room_items)
    # rooms = Listbox(frame, listvariable=room_var).grid(row=0, column=0, sticky=N+S+W+E)
    rooms = Treeview(
        frame,
        show='headings',  # Suppress column headers
        columns=['rooms'],
    )
    rooms.grid(row=0, column=0, sticky=N+S+W)
    rooms.insert('', 'end', text='general', values=['gen'])

    rhsframe = Frame(frame, padding=5, style=make_style('My2.TFrame', 'blue'))
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

    text = Text(rhsframe, font=('Helvetica', 10), height=10, wrap=WORD)
    text.grid(row=1, column=0, sticky=N+S+E+W)

    new_message = Entry(master=rhsframe)
    new_message.grid(row=2, column=0, sticky=E+W)#, padx=10, pady=10)

    def add_item(text):
        msgsd.append(text)
        msgs.set(msgsd)
        text.insert(END, text + '\n')

    # Setting up bidirectional communication between the main
    # thread (UI), and the asyncio thread (IO).
    import queue
    queue_ui = queue.Queue()
    queue_io = queue.Queue()

    def handler():
        try:
            data = queue_ui.get(block=False)
            print(f'Got ui data: {data}')
        except queue.Empty:
            return
        else:
            if all(k in data for k in ['room', 'msg']):
                msgsd.append(data['msg'])
                msgs.set(msgsd)

                msg = data['msg']

                matches_bold = []
                for m in re.finditer(r'\*(.*?)\*', msg):
                    matches_bold.append(m)

                matches_under = []
                for m in re.finditer(r'_(.*?)_', msg):
                    matches_under.append(m)

                current = text.index(END) + ' - 1 lines'
                print('current', current)
                text.insert(END, msg + '\n', ('new',))
                # ranges = text.tag_ranges('new')
                # print(ranges)

                text.tag_config('bold', font=('Times', '12', 'bold'))
                for m in matches_bold:
                    a = current + f' + {m.start() + 1} chars'
                    b = current + f' + {m.end() + 1} chars'
                    print(a, b)
                    text.tag_add('bold', a, b)

                text.tag_config('underline', underline=1)
                for m in matches_under:
                    a = current + f' + {m.start() + 1} chars'
                    b = current + f' + {m.end() + 1} chars'
                    print(a, b)
                    text.tag_add('underline', a, b)
        finally:
            root.after(100, handler)

    root.after(100, handler)

    def ui_send_msg(event):
        msg = dict(room='general', msg=new_message.get())
        queue_io.put(msg, block=False)
        new_message.delete(0, END)

    new_message.bind('<Return>', ui_send_msg)

    def run_thread():
        asyncio.run(
            main(use_signal=False, queue_ui=queue_ui, queue_io=queue_io))

    import threading
    thread = threading.Thread(target=run_thread, daemon=True)
    thread.start()
    root.mainloop()


if __name__ == '__main__':
    uimain()
