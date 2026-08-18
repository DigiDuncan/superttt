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
from queue import Empty as QueueEmptyError
from queue import Queue
from threading import Event as ThreadEvent

from .message import Message, get_wrapped_size, replace_sender, unwrap, wrap
from .room import uid_from_addr
from .socketing import (
        FACILITATOR_UID,
        UNKNOWN_UID,
        ClientClosed,
        ConnectionClosed,
        ConnectionOpened,
        ExistingConnections,
        IPv4Addr,
        ms_since_epoch,
)
from .threading import ThreadScope


def recv_all(connection: socket.socket) -> bytes | None:
        header = connection.recv(6, socket.MSG_PEEK)
        if len(header) == 0 or (size := get_wrapped_size(header)) is None:
            raise ConnectionError
        available = len(connection.recv(2048, socket.MSG_PEEK))
        if available < size:
            return None
        return connection.recv(size)

class TCPFacilitator(ThreadScope):
    """
    The facilitator holds all of the connections and relays messages between clients.
    It uses non-blocking connections to handle an arbitrary number of clients.
    """
    BACKLOG = 5

    def __init__(self, port: int, auth_comm: Queue[tuple[Message, int]], close_event: ThreadEvent, addr: str | None = None):
        super().__init__(close_event)
        self._socket: socket.socket # Server Socket

        self._addr: str = "0.0.0.0" if addr is None else addr
        self._port = port
        self._auth_comm: Queue[tuple[Message, int]] = auth_comm
        self._connections: list[socket.socket] = []
        self._uid: dict[socket.socket, int] = {}

    def _enter(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((self._addr, self._port))
        self._socket.listen(TCPFacilitator.BACKLOG)
        self._socket.settimeout(0)

    def _run(self):
        self._recv_new_connections()
        if not self._connections:
            return
        self._recv_messages()
        self._send_messages()

    def _exit(self):
        for connection in self._connections:
            self._disconnect(connection, alert=False)
        self._socket.close()

    def _recv_new_connections(self):
        try:
            (new, addr) = self._socket.accept()
            self._connect(new, addr)
        except BlockingIOError:
            # Tried to accept when there was no socket waiting
            pass
        except OSError:
            print("Attempted to accept a new connection when the socket has closed, Exiting")
            self._close_event.set()

    def _recv_messages(self):
        rlist, _, _ = select.select(self._connections, (), (), 0.0)
        for connection in rlist:
            try:
                if (msg := recv_all(connection)) is None:
                    continue
                self._dispatch_message(replace_sender(msg, self._uid[connection]), connection)
            except ConnectionError:
                print(f"failed to recv from <{connection.getpeername()}> disconnecting")
                self._disconnect(connection, shutdown=False, alert=True)

    def _send_messages(self):
        try:
            while new := self._auth_comm.get_nowait():
                msg = wrap(new[0], new[1], FACILITATOR_UID)
                self._dispatch_message(msg, None)
        except QueueEmptyError:
            pass

    def _connect(self, s: socket.socket, addr: IPv4Addr, alert: bool = True):
        s.settimeout(0)
        uid = uid_from_addr(addr)

        msg = wrap(ExistingConnections(tuple(self._uid.values())), ms_since_epoch(), FACILITATOR_UID)
        s.send(msg) # TODO: see if this size gets close to the buffer size (1024 - 2048 bytes)

        self._connections.append(s)
        self._uid[s] = uid


        if alert:
            self._dispatch_message(wrap(ConnectionOpened(uid), ms_since_epoch(), FACILITATOR_UID), s)
        print(f"New connection <{uid}> <{addr}>")

    def _disconnect(self, s: socket.socket, shutdown: bool = True, alert: bool = True):
        try:
            self._connections.remove(s)
        except ValueError:
            pass
        uid = self._uid.pop(s, None)

        if shutdown and uid is not None:
            s.shutdown(socket.SHUT_RDWR)
            s.close()

        if alert and uid is not None:
            self._dispatch_message(wrap(ConnectionClosed(uid), ms_since_epoch(), FACILITATOR_UID), s)

    def _dispatch_message(self, msg: bytes, connection: socket.socket | None):
        for other in self._connections[:]:
            if other == connection:
                continue
            try:
                # TODO: see if this size get's close to the buffer size (1024 - 2048 bytes)
                other.send(msg)
            except BlockingIOError:
                print(f"Failed to dispatch a message to <{self._uid[other]}>.")
                self._disconnect(other, shutdown=False)

class TCPClient(ThreadScope):
    CONNECTING_TIMEOUT = 0.5
    CONNECTING_MAX = 10.0
    MESSAGE_TIMEOUT = 0.0

    def __init__(
        self,
        name: str,
        addr: tuple[str, int],
        incoming: Queue[tuple[Message, int, int]],
        outgoing: Queue[tuple[Message, int]],
        close_event: ThreadEvent,
    ) -> None:
        super().__init__(close_event, f"{name} Client")
        self._connection: socket.socket | None = None
        self._incoming: Queue[tuple[Message, int, int]] = incoming
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
                break
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
        self._incoming.put_nowait((ClientClosed(), ms_since_epoch(), self._uid))
        if self._connection is None:
            return
        self._connection.shutdown(socket.SHUT_RDWR)
        self._connection.close()

    def _recv_messages(self):
        if self._connection is None:
            return
        try:
            if (msg := recv_all(self._connection)) is None:
                return
            if (package := unwrap(msg)) is None:
                print(f"Could not unwrap the message {msg}")
                raise ConnectionError
            self._incoming.put_nowait(package)
        except ConnectionError:
            print("failed to recv messages disconnecting")
            self._close_event.set()
        except BlockingIOError:
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
        except BlockingIOError:
            pass
        except QueueEmptyError:
            pass
