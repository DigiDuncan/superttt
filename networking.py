from __future__ import annotations

import json
import queue
import select
import socket
import threading
import urllib.request
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from queue import Queue
from string import ascii_uppercase
from time import time_ns
from typing import ClassVar, Literal, Self

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

    def start(self) -> bool:
        if self._thread.is_alive() or self._has_started:
            # TODO: logging print("This thread is currently alive and cannot be started again.")
            # TODO: logging print("Cannot restart a thread. The close event has been set.")
            return False
        self._has_started = True
        self._thread.start()
        return True

    def stop(self) -> bool:
        if not self._thread.is_alive():
            return False
        self._close_event.set()
        return True

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

SOH = b'\x01'
STX = b'\x02'
ETX = b'\x03'
EOT = b'\x04'

MIN_SIZE = 1 + 4 + 1 + 2 + 8 + 1 + 1

def wrap(message: Message, time: int) -> bytes:
    """
    Message object to wrap and the ms since epoch for syncing.

    A wrapped message looks like this

    <SOH> <msg_size:0>4> <ETX> <name_size:0>2> <name> <msg_time:BE> <STX> <data> <EOT>
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

    header = SOH + f"{msg_size:0>4X}".encode() + ETX + f"{name_size:0>2X}".encode() + name + time_data
    body = STX + data
    tail = EOT

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

def find_wrapped(data: bytes) -> tuple[int, int] | None:
    """
    Look through a stream of data and find a wrapped message.
    If it fails to find a message it returns None.
    If it finds a message it returns the range (end exclusive like range(a,b)) of the message.
    if a != 0, find_wrapped doesn't care, but that does indicate a msg fragment.

    We are looking for the specific shape <SOH> FFFF <ETX> ... <EOT>
    we don't actually care about the rest of the header or the body marker <STX>.
    If that is illformed the unwrap function handles that.
    """
    idx = 0
    size = len(data)
    # Since were are looking for a very specific shape we know that it must be MIN_SIZE or more bytes
    while idx < size - MIN_SIZE:
        if data[idx:idx+1] == SOH and data[idx+5:idx+6] == ETX:
            # We know that the data is in the form <SOH> ???? <ETX>
            try:
                msg_size = int(data[idx+1:idx+5], base=16)
            except ValueError:
                pass # The message size is not a Hexadecimal number so it can't correct
            else:
                # We know the data is in the form <SOH> FFFF <ETX> so let's look for <EOT>
                if data[idx+msg_size-1:idx+msg_size] == EOT:
                    return idx, idx + msg_size # The shape is all correct we have a message to send.
        idx += 1 # We haven't found a <SOH>FFF<ETX> ... <EOT> marker so move on.
        continue

    return None # We reached the end of the data without finding a wrapped msg

def send(socket: socket.socket, data: bytes) -> bool:
    sent = 0
    while sent < len(data):
        out = socket.send(data[sent:])
        if out == 0:
            return False # Failed to send msg
        sent += out
    return True

def recv(socket: socket.socket) -> Literal[False] | bytes:
    # TODO: better Validiation, and handle retrieving msg fragments
    # because if that happens every message from then on will be broken.
    # It might require a more stateful recv that just eats bytes till there are none left
    # Once that's true we look for the <SOH> <SOH> <STX> <EOT> marker and extract those messages
    # Which would also mean that we don't need the message size, but also that can be a good sanity
    # check.
    chunks = []
    rcvd = 0
    size = 5 # 5 bytes for <SOH> and 0000 - FFFF size string
    while rcvd < size:
        chunk = socket.recv(size - rcvd)
        if chunk == b'':
            return False # Failed to recv msg
        rcvd += len(chunk)
        chunks.append(chunk)
    header = b''.join(chunks)
    size = int(header[1:], base=16)
    while rcvd < size:
        chunk = socket.recv(min(size - rcvd, 2048))
        if chunk == b'':
            return False # Failed to recv msg
        rcvd += len(chunk)
        chunks.append(chunk)
    return b''.join(chunks)



@dataclass
class MouseCursorMoved(Message):
    "Mouse Cursor Moved"
    x: float
    y: float
    dx: float
    dy: float

@dataclass
class TextMessage(Message):
    text: str

@dataclass
class AssignNameMessage(Message):
    name: str

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
        print("starting a socket")
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
            connection.setblocking(False)
            self._queue.put(connection)

    def _exit(self):
        self._connection.close()


class Facilitator(ThreadScope):
    """
    The facilitator holds all of the connections and relays messages between clients.
    It uses non-blocking connections to handle an arbitrary number of clients.
    """
    SELECT_TIMEOUT = 10.0

    def __init__(self, conn_queue: Queue[socket.socket], close_event: threading.Event, name: str | None = None) -> None:
        super().__init__(close_event, name)
        self._connection_queue = conn_queue

        self._connections: list[socket.socket] = []
        self._connection_outgoing: dict[tuple[str, int], bytes] = {}
        self._connection_incoming: dict[tuple[str, int], bytes] = {}

    def _run(self):
        self._meet_new_connections()

        if not self._connections:
            return

        ready_to_read, ready_to_write, _ = select.select(
            self._connections,
            self._connections,
            (),
            Facilitator.SELECT_TIMEOUT
        )

        self.recv_messages(ready_to_read)
        self.send_messages(ready_to_write)

    def _meet_new_connections(self):
        try:
            while new := self._connection_queue.get_nowait():
                index = new.getpeername()
                name = get_roomcode(index[0], index[1])
                self._connections.append(new)
                self._connection_incoming[index] = b''
                self._connection_outgoing[index] = wrap(AssignNameMessage("Facilitator", name), ms_since_epoch())
                print(f'got new connection {name} <{index}>')
        except queue.Empty:
            pass

    def _close_connection(self, connection: socket.socket, shutdown: bool = True):
        index = connection.getpeername()
        print(f"disconnecting from {index}")
        self._connections.remove(connection)
        dangling = self._connection_incoming.pop(index)
        if dangling != b'':
            print(f"{index} has left dangling incoming data <{dangling}>")
        dangling = self._connection_outgoing[index]
        if dangling != b'':
            print(f"{index} has dangling outgoing data <{dangling}>")

    def recv_messages(self, rlist: Iterable[socket.socket]):
        for connection in rlist:
            try:
                chunk = connection.recv(2048)
            except ConnectionError:
                chunk = b'' # TODO: we lose the error info do we need it?
            if chunk == b'':
                print("failed to retrieve msg disconnecting.")
                self._close_connection(connection, shutdown=False)
                continue
            print(f"got data <{chunk}> from {connection.getpeername()}")
            index = connection.getpeername()
            data = self._connection_incoming[index] + chunk
            if (msg := find_wrapped(data)) is None: # No message found
                continue
            if msg[0] != 0:
                print(f"{index} had sent a message fragment <{data[:msg[0]]}> discarding")
            self._connection_incoming[index] = data[msg[1]:] # consume found message
            self._dispatch_message(index, data[msg[0]:msg[1]]) # Send the message to every other connection

    def _dispatch_message(self, index: tuple[str, int], data: bytes):
        # For every connection except the sender reroute the data.
        # We ensure that we are only sending whole messaged through `find_wrapped`
        # If we didn't each connection could get an interleaving of messages
        for key in self._connection_outgoing:
            if key == index:
                continue
            self._connection_outgoing[key] += data

    def send_messages(self, wlist: Iterable[socket.socket]):
        for connection in wlist:
            index = connection.getpeername()
            data = self._connection_outgoing[index]
            if data == b'':
                continue

            try:
                sent = connection.send(data)
            except ConnectionError:
                sent = 0 # TODO: we lose the error info do we need it?
            if sent == 0:
                print(f"failed to send msg to {index} disconnecting.")
                self._close_connection(connection, shutdown=False)
                continue

            self._connection_outgoing[index] = data[sent:]

    def _exit(self):
        for connection in self._connections[:]:
            self._close_connection(connection, shutdown=True)

class Client(ThreadScope):
    TIMEOUT = 0.1
    TIMEOUT_GROWTH = 0.1
    NAME_TIMEOUT = 1.0

    def __init__(self, addr: tuple[str, int], close_event: threading.Event, name: str | None = None) -> None:
        super().__init__(close_event, name)
        self._addr = addr
        self._connection: socket.socket

        self._name: str = ""

        self._p_time: int = 0

    def _enter(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        attempts = 0
        accumulated = 0.0
        while True:
            duration = min(10.0, Client.TIMEOUT + attempts * Client.TIMEOUT)
            try:
                s.settimeout(duration)
                s.connect(self._addr)
            except TimeoutError:
                accumulated += duration
                attempts += 1
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                print(f"Failed to connect after {duration:g}s (accumulated {accumulated:g}s) trying again.")
            except OSError as e:
                print(f"Failed to connect with {e}. Exiting")
                self._close_event.set()
                break
            else:
                print(f"found connection <{s.getpeername()}>")
                break

        # TODO: YIKES
        self._connection = s
        s.settimeout(Client.NAME_TIMEOUT)
        name_data = recv(s)
        name_msg = unwrap(name_data) if name_data else None
        name, time = (None, None) if name_msg is None else name_msg
        if name is not None and isinstance(name, AssignNameMessage) and name.sender == "Facilitator":
            print(f"Got name {name.name} from {name.sender} @ {time}")
            self._name = name.name
        else:
            print("Never got name msg from Faciliator closing")
            self._close_event.set()
            return

        s.settimeout(Client.TIMEOUT)
        self._p_time = ms_since_epoch()

    def _run(self):
        time = ms_since_epoch()
        if self._p_time + 2000 < time:
            print("sending msg")
            self._p_time = time
            msg = TextMessage(self._name, "random tick")
            time = ms_since_epoch()
            send(self._connection, wrap(msg, time))

        try:
            if data := recv(self._connection):
                print(data)
        except TimeoutError:
            pass

    def _exit(self):
        self._connection.shutdown(socket.SHUT_RDWR)
        self._connection.close()


def host():
    addr = get_private_ipv4()
    socket = 10000

    conn_queue = Queue()
    close = threading.Event()

    lighthouse = Lighthouse((addr, socket), conn_queue, close)
    facilitator = Facilitator(conn_queue, close)

    lighthouse.start()
    facilitator.start()

    facilitator.watch()

def join():
    addr = get_private_ipv4()
    socket = 10000

    close = threading.Event()

    client = Client((addr, socket), close)
    client.start()

    client.watch()

if __name__ == "__main__":
    host()