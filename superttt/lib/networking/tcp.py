"""
Transmission Control Protocol (TCP) uses a fundamentally different system from
User Datagram Protocol (UDP). In TCP sockets have connections which get formed when
a client connects to a server socket. The server then makes a new client socket so
the two clients have a direct connection. To avoid every user having a forwarded port
the host create's a `Lighthouse` which holds the server socket and outputs client
sockets for the `Facilitator`.
"""

import select
import socket
from collections.abc import Iterable
from queue import Empty as QueueEmptyError
from queue import Queue
from threading import Event as ThreadEvent

from .message import Message, get_wrapped_size, replace_sender, wrap
from .room import uid_from_addr
from .socketing import UNKNOWN_UID
from .threading import ThreadScope


class Lighthouse(ThreadScope):
    """
    Holds the host's `lighthouse` server until told to stop.
    Can be told to stop before the clients have closed their connecctions.
    Just makes connections and pipes them through the provided connections Queue.
    Won't create socket until the thread has been started.
    """

    TIMEOUT = 0.5

    def __init__(
        self,
        addr: tuple[str, int],
        conn_queue: Queue[socket.socket],
        close_event: ThreadEvent,
        *,
        backlog: int = 5,
    ) -> None:
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
            pass  # TODO: track accumulated? reset on connection?
        else:
            # TODO: log address in some way?
            connection.setblocking(False)
            self._queue.put(connection)

    def _exit(self):
        self._connection.close()


class TCPFaciliator(ThreadScope):
    """
    The facilitator holds all of the connections and relays messages between clients.
    It uses non-blocking connections to handle an arbitrary number of clients.
    """

    def __init__(self, conn_queue: Queue[socket.socket], close_event: ThreadEvent):
        super().__init__(close_event)
        self._connection_queue: Queue[socket.socket] = conn_queue

        self._connections: list[socket.socket] = []
        self._uid: dict[socket.socket, int] = {}
        self._pending_messages: dict[socket.socket, list[bytes]] = {}

    def _run(self):
        self._meet_new_connections()
        if not self._connections:
            return

        rlist, wlist, _ = select.select(self._connections, self._connections, ())

        self._recv_messages(rlist)
        self._send_messages(wlist)

    def _exit(self):
        for connection in self._connections[:]:
            self._disconnect(connection, shutdown=True, alert=False)

    def _meet_new_connections(self):
        try:
            while new := self._connection_queue.get_nowait():
                self._connections.append(new)
                self._pending_messages[new] = []
                self._uid[new] = uid_from_addr(new.getpeername())
                print(f"New connection formed with <{new.getpeername()}>")
        except QueueEmptyError:
            return

    def _recv_messages(self, rlist: Iterable[socket.socket]):
        for connection in rlist:
            try:
                # Peek doesn't remove the bytes from the buffer
                msg = connection.recv(6, socket.MSG_PEEK)
                if len(msg) == 0:
                    raise ConnectionError
                if (size := get_wrapped_size(msg)) is None:
                    print(f"received an invalid msg from <{connection.getpeername()}> ignoring.")
                    continue
                msg = connection.recv(size)
                print(msg)
                if len(msg) != size:
                    print(f"failed to retrieve message <{msg}> in one piece ignoring.")
                    continue
                msg = replace_sender(msg, self._uid[connection])
                self._dispatch_message(msg, connection)
            except ConnectionError:
                print(f"failed to recv from <{connection.getpeername()}> disconnecting")
                self._disconnect(connection, shutdown=False, alert=True)
                continue

    def _dispatch_message(self, msg: bytes, connection: socket.socket):
        for other, pending in self._pending_messages.items():
            if other is connection:
                continue
            pending.append(msg)

    def _send_messages(self, wlist: Iterable[socket.socket]):
        for connection in wlist:
            # If a connection was removed during recv it might still be in the wlist
            pending = self._pending_messages.get(connection, ())
            if not pending:
                continue
            msg = pending.pop(0)
            if not msg:
                continue

            if (size := get_wrapped_size(msg)) is None:
                print(f"tried sending an invalid msg to <{connection.getpeername()}> ignoring.")
                continue

            try:
                sent = connection.send(msg)
            except ConnectionError:
                print(f"failed to send to <{connection.getpeername()}> disconnecting")
                self._disconnect(connection, shutdown=False, alert=True)
                continue

            if sent != size:
                print(f"failed to send whole message to <{connection.getpeername()}>")

    def _disconnect(self, connection: socket.socket, shutdown: bool, alert: bool = True):
        self._connections.remove(connection)
        self._pending_messages.pop(connection)
        self._uid.pop(connection)

        if shutdown:
            connection.shutdown(socket.SHUT_RDWR)
            connection.close()

        if alert:
            print("Connection closed but alerting other connections is not implemented.")
            # TODO: for every other alive connection tell it that a connection with uid has closed


class TCPClient(ThreadScope):
    CONNECTING_TIMEOUT = 0.5
    CONNECTING_MAX = 10.0
    MESSAGE_TIMEOUT = 0.0

    def __init__(
        self,
        name: str,
        addr: tuple[str, int],
        incoming: Queue[tuple[Message, int]],
        outgoing: Queue[tuple[Message, int]],
        close_event: ThreadEvent,
    ) -> None:
        super().__init__(close_event, f"{name} Client")
        self._connection: socket.socket | None = None
        self._incoming: Queue[tuple[Message, int]] = incoming
        self._outgoing: Queue[tuple[Message, int]] = outgoing
        self._client_name: str = name
        self._addr: tuple[str, int] = addr
        self._uid: int = UNKNOWN_UID

    def _enter(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        attempts = 1
        accumulated = 0.0
        while accumulated < TCPClient.CONNECTING_MAX:
            duration = attempts * TCPClient.CONNECTING_TIMEOUT
            try:
                s.settimeout(duration)
                s.connect(self._addr)
            except TimeoutError:
                accumulated += duration
                attempts += 1
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            except OSError as e:
                print(f"Encountered exception {e} while attempting to connect")
                self._close_event.set()
                return
            else:
                print("found connection")
                self._connection = s
                s.settimeout(TCPClient.MESSAGE_TIMEOUT)
                break
        else:
            print(f"Failed to find connection after {accumulated}s and {attempts} attempts")
            self._close_event.set()
            return

    def _run(self):
        self._recv_messages()
        self._send_messages()

    def _exit(self):
        if self._connection is None:
            return
        self._connection.shutdown(socket.SHUT_RDWR)
        self._connection.close()

    def _recv_messages(self):
        if self._connection is None:
            return
        try:
            pass
        except ConnectionError:
            print("failed to recv messages disconnecting")
            self._close_event.set()
        except TimeoutError:
            return

    def _send_messages(self):
        if self._connection is None:
            return
        try:
            while msg_time := self._outgoing.get_nowait():
                data = wrap(msg_time[0], msg_time[1], self._uid)
                sent = self._connection.send(data)
                if sent == 0:
                    raise ConnectionError
        except ConnectionError:
            print("failed to send messages disconnecting")
            self._close_event.set()
        except TimeoutError:
            pass
        except QueueEmptyError:
            pass
