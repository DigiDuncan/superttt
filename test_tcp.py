import queue
import sys
import threading
from dataclasses import dataclass

from arcade import Sprite, SpriteList, View, Window

import superttt.lib.networking.message as msg
import superttt.lib.networking.room as rm
import superttt.lib.networking.socketing as sk
from superttt.lib.networking import tcp


@dataclass
class CursorMovedMessage(msg.Message):
    x: float
    y: float
    dx: float
    dy: float


class CursorView(View):
    def __init__(self, incoming: queue.Queue, outgoing: queue.Queue):
        super().__init__()
        self.incoming = incoming
        self.outgoing = outgoing

        self._cursor: Sprite = Sprite("./resources/networking/cursor1.png", 3)
        self._cursors: SpriteList[Sprite] = SpriteList()
        self._others: dict[int, Sprite] = {}
        self._cursors.append(self._cursor)

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> bool | None:
        self._cursor.left = x
        self._cursor.top = y

        self.outgoing.put_nowait((CursorMovedMessage(x, y, dx, dy), sk.ms_since_epoch()))

    def on_draw(self) -> bool | None:
        self.clear()
        self._cursors.draw(pixelated=True)

    def on_update(self, delta_time: float) -> bool | None:
        try:
            while new := self.incoming.get_nowait():
                msg, time, uid = new

                match msg:
                    case CursorMovedMessage():
                        self._connect(uid)
                        self._others[uid].left = msg.x
                        self._others[uid].top = msg.y
                    case sk.ConnectionClosed():
                        if msg.uid not in self._others:
                            continue
                        sprite = self._others.pop(msg.uid)
                        self._cursors.remove(sprite)
                    case sk.ConnectionOpened():
                        self._connect(msg.uid)
                        self.outgoing.put_nowait((CursorMovedMessage(self._cursor.left, self._cursor.top, 0, 0), sk.ms_since_epoch()))
                    case sk.ExistingConnections():
                        for uid in msg.uids:
                            self._connect(uid)
        except queue.Empty:
            pass

    def _connect(self, uid: int):
        if uid not in self._others:
            sprite = Sprite("./resources/networking/cursor3.png", 2)
            self._others[uid] = sprite
            self._cursors.append(sprite)

    def on_show_view(self) -> None:
        self.window.set_mouse_visible(False)

    def on_hide_view(self) -> None:
        self.window.set_mouse_visible(True)


def host(port) -> threading.Event:
    # TODO: obviously we want a way to communicate and retrieve info from the facilitator
    close_server = threading.Event()

    faciliator = tcp.TCPFacilitator(port, queue.Queue(), close_server)
    faciliator.start()

    return close_server


def join(addr, port) -> tuple[threading.Event, queue.Queue, queue.Queue]:
    close_client = threading.Event()

    incoming = queue.Queue()
    outgoing = queue.Queue()
    client = tcp.TCPClient("Host", (addr, port), incoming, outgoing, close_client)

    client.start()

    return close_client, incoming, outgoing

PORT = 25565


def main():
    is_host = len(sys.argv) == 1
    if is_host:
        port = PORT
        host_addr = sk.get_public_ipv4()
        addr = sk.get_private_ipv4()
        close_server = host(PORT)
        print(f"Hosting <{host_addr, PORT}> with room code <{rm.get_roomcode(host_addr, PORT)}> for wan, and <{rm.get_roomcode(addr, PORT)}> for lan")
    else:
        try:
            addr, port = rm.get_addr(sys.argv[1])
        except ValueError:
            print(f"Invalid room code <{sys.argv[1]}>")
            sys.exit(1)

    close_client, inc, out = join(addr, port)

    try:
        win = Window()
    except KeyboardInterrupt:
        close_client.set()
        if is_host:
            close_server.set()  # type: ignore -- Def exists
        sys.exit(1)

    try:
        view = CursorView(inc, out)
        win.run(view)
    except KeyboardInterrupt:
        win.close()
    finally:
        close_client.set()
        if is_host:
            close_server.set()  # type: ignore -- Def exists


if __name__ == "__main__":
    main()
