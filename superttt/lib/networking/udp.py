"""
User Datagram Protocol (UDP) uses a fundamentally different system from
Transmission Control Protocol (TCP). UDP sockets have no connection. They
can Send to/Recv from any other socket. The Client must send to a known
host address available locally or port-forwarded. This establishes the
connection so the host can respond. This means that the `Lighthouse` and
`Facilitator` used in TCP aren't necessary as the act of using `recvfrom`
establishes new connections in the `Facilitator`
"""

import select
import socket
from queue import Empty as QueueEmptyError
from queue import Queue
from threading import Event as ThreadEvent

from .message import Message, get_wrapped_size, replace_sender, unwrap, wrap
from .room import uid_from_addr
from .socketing import UNKNOWN_UID, IPv4Addr, ms_since_epoch
from .threading import ThreadScope


class UDPFacilitator(ThreadScope):
    CLIENT_TIMEOUT = 10_000

    def __init__(self, addr: IPv4Addr, close_event: ThreadEvent, name: str | None = None) -> None:
        super().__init__(close_event, name)
        self._socket: socket.socket
        self._addr = addr
        self._connections: list[IPv4Addr] = []
        self._uid: dict[IPv4Addr, int] = {}
        self._timeout: dict[IPv4Addr, int] = {}

    def _enter(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind(self._addr)
        self._socket.settimeout(0.0)
        print("Started Facilitator")

    def _run(self):
        rcvd = self._recv_messages()
        while not rcvd:
            rcvd = self._recv_messages()
        self._clear_stale()

    def _exit(self):
        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close()

    def _recv_messages(self) -> bool:
        try:
            # No message we are sending will be more than 1024 bytes
            (msg, addr) = self._socket.recvfrom(1024)
            if len(msg) == 0:  # If we got an empty UDP packet then the client was saying hi
                print(f"Connection Estalished with new Client <{addr}>")
                self._connect(addr)
                return False
            if (size := get_wrapped_size(msg)) is None:
                print(f"received an invalid msg from <{addr}> ignoring.")
                return False
            if len(msg) != size:
                print(f"failed to retrieve message <{msg}> from <{addr}> in one piece ignoring.")
                return False

            self._connect(addr)
            msg = replace_sender(msg, self._uid[addr])
            self._dispatch_message(msg, addr)
            return True
        except BlockingIOError:
            return True
        except ConnectionResetError:
            return False  # Windows turns a failed send into the next

    def _connect(self, addr: IPv4Addr):
        if addr in self._uid:
            self._timeout[addr] = ms_since_epoch()
            return

        uid = uid_from_addr(addr)
        print(f"New connection <{uid}> <{addr}>")
        self._connections.append(addr)
        self._uid[addr] = uid
        self._timeout[addr] = ms_since_epoch()

    def _disconnect(self, addr: IPv4Addr):
        if addr not in self._uid:
            return

        self._connections.remove(addr)
        self._uid.pop(addr)
        self._timeout.pop(addr)

    def _dispatch_message(self, msg: bytes, addr: IPv4Addr):
        for other in self._connections[:]:
            if other == addr:
                continue
            self._socket.sendto(msg, other)

    def _clear_stale(self):
        time = ms_since_epoch()
        for addr, timeout in tuple(self._timeout.items()):
            if timeout + UDPFacilitator.CLIENT_TIMEOUT < time:
                self._disconnect(addr)


class UDPClient(ThreadScope):
    def __init__(
        self,
        name: str,
        addr: IPv4Addr,
        incoming: Queue[tuple[Message, int, int]],
        outgoing: Queue[tuple[Message, int]],
        close_event: ThreadEvent,
    ):
        super().__init__(close_event, f"Client-{name}")
        self._connection: socket.socket
        self._incoming: Queue[tuple[Message, int, int]] = incoming
        self._outgoing: Queue[tuple[Message, int]] = outgoing
        self._client_name: str = name
        self._addr: IPv4Addr = addr
        self._uid: int = UNKNOWN_UID

    def _enter(self):
        self._connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._connection.sendto(b"", self._addr)
        self._connection.settimeout(0.0)
        print(f"connection msg sent, client bound to {self._connection.getsockname()}")

    def _run(self):
        rlist, wlist, _ = select.select((self._connection,), (self._connection,), ())
        if rlist:
            self._recv_messages()
        if wlist:
            self._send_messages()

    def _exit(self):
        self._connection.shutdown(socket.SHUT_RDWR)
        self._connection.close()

    def _recv_messages(self):
        try:
            # No message we are sending will be more than 1024 bytes
            (data, addr) = self._connection.recvfrom(1024)
            if (size := get_wrapped_size(data)) is None:
                print(f"received an invalid msg from <{addr}> ignoring.")
                return
            if len(data) != size:
                print(f"failed to retrieve message <{data}> from <{addr}> in one piece ignoring.")
                return
            if (package := unwrap(data)) is None:
                print(f"failed to unwrap message <{data}> from <{addr}> ignoring.")
                return
            msg, time, uid = package
            print(f"retrieved msg <{msg}> @ {time}ms from <{uid}>")
            self._incoming.put_nowait((msg, time, uid))
        except ConnectionError:
            # A UDP socket can still return an error code that python (windows?) raises
            # as an exception.
            print("host has closed disconnecting")
            self._close_event.set()
            return

    def _send_messages(self):
        try:
            while new := self._outgoing.get_nowait():
                self._connection.sendto(wrap(new[0], new[1], self._uid), self._addr)
        except QueueEmptyError:
            pass
