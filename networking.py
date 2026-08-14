from __future__ import annotations

import json
import socket
import threading
import urllib.request
from dataclasses import asdict, dataclass
from queue import Queue
from string import ascii_uppercase
from time import time_ns
from typing import ClassVar, Self

from arcade import View, Window

ROOM_CHR = ascii_uppercase
ROOM_MAP = {s: idx for idx, s in enumerate(ROOM_CHR)}
def int_to_base(x: int, base: str = ROOM_CHR):
    n, m = divmod(x, len(base))
    s = base[m]
    while 0 < n:
        n, m = divmod(n, len(base))
        s = base[m] + s
    return s

def base_to_int(s: str, base: dict[str, int] = ROOM_MAP):
    x = 0
    size = len(base)
    for char in s:
        x = x * size + base[char]
    return x

def get_roomcode(addr: str, port: int, mapping: str = ROOM_CHR) -> str:
    (a1, a2, a3, a4) = (max(0, min(0xFE, int(a))) for a in addr.split('.'))
    n = (a1 << 40) + (a2 << 32) + (a3 << 24) + (a4 << 16) + max(0, min(0xFFFE, port))
    print(n)
    return int_to_base(n, mapping)

def get_addr(room: str, mapping: dict[str, int]) -> tuple[str, int]:
    n = base_to_int(room, mapping).to_bytes(6, signed=False)
    (a1, a2, a3, a4) = n[0:4] # automatically converts to 8-bit unsigned int
    return f"{a1}.{a2}.{a3}.{a4}", int.from_bytes(n[4:6], "big")


def get_private_ipv4() -> str:
    return socket.gethostbyname(socket.gethostname())


def get_public_ipv4() -> str:
    return urllib.request.urlopen("https://api.ipify.org").read().decode('utf8')

def ms_since_epoch() -> int:
    return time_ns() // 1_000_000


class ThreadScope:
    """
    A Simple class which provides a simple threaded loop that can be closed using the
    passed in close_event. The methods _enter, _run, and _exit are to be overwritten in subclasses.
    It is unsafe to call any of the public ThreadScope methods from within the thread.
    """

    def __init__(self, close_event: threading.Event, name: str | None = None) -> None:
        name = self.__class__.__name__ if name is None else name
        self._thread: threading.Thread = threading.Thread(target=self._scope, name=name)
        self._close_event: threading.Event = close_event
        self._has_started: bool = False

    def join(self, timeout: float | None = None):
        return self._thread.join(timeout)

    def is_alive(self) -> bool:
        return self._thread.is_alive()

    def has_started(self) -> bool:
        return self._has_started

    def start(self):
        if self._thread.is_alive() or self.has_started:
            # TODO: logging print("This thread is currently alive and cannot be started again.")
            # TODO: logging print("Cannot restart a thread. The close event has been set.")
            return
        self._has_started = True
        self._thread.start()

    def stop(self):
        if not self._thread.is_alive():
            return
        self._close_event.set()

    def watch(self):
        try:
            while self._thread.is_alive():
                self._thread.join(0.1)
        except KeyboardInterrupt:
            #TODO: logging print(f"Received KeyboardInterrupt. Closing thread `{self._thread.name}`.")
            pass
        finally:
            self._close_event.set()

    def _scope(self):
        self._enter()
        while not self._close_event.is_set():
            self._run()
        self._exit()

    def _enter(self):
        pass

    def _run(self):
        pass

    def _exit(self):
        pass


@dataclass
class Message:
    subcls_mapping: ClassVar[dict[str, type[Message]]] = {}
    sender: str

    def __init_subclass__(cls) -> None:
        if cls.__name__ in Message.subcls_mapping:
            print("hmmm what to do about this")
            return
        Message.subcls_mapping[cls.__name__] = cls

    @classmethod
    def get[T](cls, name: str, default: T | None = None) -> type[Message] | T | None:
        return cls.subcls_mapping.get(name, default)

    def encode(self) -> bytes:
        """
        Convert a message dataclass into a json byte encoding using utf-8
        """
        as_string: str = json.dumps(asdict(self), ensure_ascii=False, check_circular=True, indent=None, separators=(',', ':'))
        return as_string.encode(encoding='utf-8')

    @classmethod
    def decode(cls, data: bytes) -> Self:
        """
        Convert a utf-8 json byte encoding into a dataclass.
        """
        return cls(**json.loads(data.decode('utf-8')))

def wrap(message: Message, time: int) -> bytes:
    """
    Message object to wrap and the ms since epoch for syncing.

    A wrapped message looks like this

    <SOH> <msg_size:0>4> <SOH> <name_size:0>2> <name> <msg_time:BE> <STX> <data> <EOT>
    | ^^^^^^^^^^^^^^^^ | | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ | | ^^^^^^^^ | | ^ |
      Size for Reading     Rest of header for decoding                Data        Tail
      1 + 4 bytes          1 + 2 + N + 8 bytes                        1 + N bytes 1 b
      UTF-8                UTF-8 except for time which is 64-bit int  UTF-8
    """
    data = message.encode()
    name = message.__class__.__name__.encode('utf-8')
    name_size = len(name)
    time_data = time.to_bytes(8, "little", signed=False)

    tail_size = 1
    body_size = 1 + len(data)
    head_size = 16 + name_size
    msg_size = head_size + body_size + tail_size

    header = f"\x01{msg_size:0>4X}\x01{name_size:0>2X}".encode() + name + time_data
    body = b'\x02'+data
    tail = b'\x04'

    return header + body + tail

def unwrap(data: bytes) -> tuple[Message, int] | None:
    """
    Unwrap bytes to retrieve the Message and ms since epoch. see wrap for structure of a message.
    The Socket uses the first 6 bytes to determine size of message. It does not do any other validation.
    That validation happens here. If the time and/or message can't be parsed return None.
    """
    # TODO: actual validation
    recv_size = len(data)
    msg_size = int(data[1:5], base=16)
    if recv_size != msg_size:
        print("The received data does not match the messages claimed size")
    name_size = int(data[6:8], base=16)
    name = data[8:8+name_size].decode('utf-8')
    time = int.from_bytes(data[8+name_size:16+name_size], "little", signed=False)

    typ: type[Message] | None = Message.get(name)
    if typ is None:
        print("Failed to unwrap valid message type")
        return None

    message = typ.decode(data[17 + name_size:-1])

    return message, time

@dataclass
class MouseCursorMoved(Message):
    "Mouse Cursor Moved"
    x: float
    y: float
    dx: float
    dy: float


class Lighthouse(ThreadScope):
    """
    Holds the host's `lighthouse` server until told to stop.
    Can be told to stop before the clients have closed their connecctions.
    Just makes connections and pipes them through the provided connections Queue.
    Won't create socket until the thread has been started.
    """
    TIMEOUT = 0.5

    def __init__(self, addr: tuple[str, int], conn_queue: Queue[socket.socket], close_event: threading.Event, *, backlog: int = 5) -> None:
        super().__init__(close_event)
        self._addr = addr
        self._backlog = backlog

        self._queue = conn_queue

        self._connection: socket.socket

    def _enter(self):
        self._connection = s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(self._addr)
        s.listen(self._backlog)

    def _run(self):
        try:
            self._connection.settimeout(Lighthouse.TIMEOUT)
            (connection, _) = self._connection.accept()
        except TimeoutError:
            pass # TODO: track accumulated? reset on connection?
        else:
            # TODO: log address in some way?
            self._queue.put(connection)

    def _exit(self):
        self._connection.close()


class Facilitator(ThreadScope):
    """
    The facilitator holds all of the connections and relays messages between clients.
    It uses non-blocking connections to handle an arbitrary number of clients.
    """
    def __init__(self, conn_queue: Queue[socket.socket], close_event: threading.Event, name: str | None = None) -> None:
        super().__init__(close_event, name)
        self._connection = conn_queue

class Client:
    pass
