"""
SuperTTT multiplayer messages and protocol. We are doing a "overactive" tcp p2p connection.
That means when a new connection comes in, every peer tells every other peer every piece of
relivant information. So with every new connection the host will tell everyone who player1 is,
and who player2 is, and that they are the host, and every client will tell every other client
their name.
"""
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Event as ThreadEvent

from superttt.lib.networking.message import Message
from superttt.lib.networking.room import get_addr, get_roomcode
from superttt.lib.networking.socketing import (
    FACILITATOR_UID,
    MY_UID,
    UNKNOWN_UID,
    ClientClosed,
    ConnectionClosed,
    ConnectionOpened,
    ExistingConnections,
    get_private_ipv4,
    get_public_ipv4,
    ms_since_epoch,
)
from superttt.lib.networking.tcp import TCPClient, TCPFacilitator
from superttt.lib.networking.threading import QueueIter, clear_queue


@dataclass
class SetHost(Message):
    uid: int # Tell other clients who the host is

@dataclass
class SetBoard(Message):
    size: int
    depth: int
    easy: bool

@dataclass
class Kick(Message):
    uid: int # Tell other clients to kick uid. Only the Host or Facilitator can send this msg

@dataclass
class SetPlayer(Message):
    player: int # Player's networking UID
    is_player1: bool # Is the player player 1 or 2?

@dataclass
class SetName(Message): # The name is assigned with the uid of the sender
    name: str

# Non-host sends these, which the handle picks up and decides if it's valid
@dataclass
class AttemptSetTile(Message):
    location: tuple[int, ...]

# Host sends these either on their turn or after the other player has tried to set a tile
@dataclass
class SetTile(Message):
    location: tuple[int, ...]

@dataclass
class SetTurn(Message):
    turn: int

@dataclass
class MouseCursorMoved(Message):
    x: int
    y: int

PORT = 25565

class _Multiplayer:
    """
    Global abstraction over Client and Facilitator. To ensure that threads get closed
    and opened properly. We used the ThreadScope's `Reset` functionality so we keep the
    same Client, Facilitator, and Queues (and close_events but we just use `ThreadScope.close()`)
    """

    def __init__(self):
        # -- GENERIC REUSABLE ATTRIBUTES --
        self.incoming: Queue[tuple[Message, int, int]] = Queue()
        self.outgoing: Queue[tuple[Message, int]] = Queue()
        self.auth: Queue[tuple[Message, int]] = Queue()

        self.client: TCPClient = TCPClient(("127.0.0.1", PORT), self.incoming, self.outgoing, ThreadEvent())
        self.facilitator: TCPFacilitator = TCPFacilitator(PORT, self.auth, ThreadEvent())
        self._is_hosting: bool = False
        self._is_connected: bool = False

        # -- SUPERTTT SPECIFIC ATTRIBUTES --
        self.name: str | None = None
        self.room: str | None = None
        self.uid: int | None = None
        self.host: int = UNKNOWN_UID # Who has the authority to send certain messages
        self.player1: int = UNKNOWN_UID
        self.player2: int = UNKNOWN_UID
        self.connecting: list[int] = [] # Who have we been told is connecting, but has no name?
        self.connections: dict[int, str] = {} # Who has connected and given us their name

        # * Because we have a `process` method we want to look at every message coming through
        self._processed: Queue[tuple[Message, int, int]] = Queue()

    # -- GENERIC REUSABLE METHODS --

    def send_msg(self, msg: Message, time: int | None = None):
        self.outgoing.put_nowait((msg, ms_since_epoch() if time is None else time))

    def send_auth_msg(self, msg: Message, time: int | None = None):
        if not self._is_hosting:
            return # You can try, but if you aren't the host you have no facilitator to send too
        self.auth.put_nowait((msg, ms_since_epoch() if time is None else time))

    def get_msg(self) -> tuple[Message, int, int] | None:
        try:
            # * This is SuperTTT specific
            return self._processed.get_nowait()
        except Empty:
            return None

    def get_all_msgs(self) -> QueueIter[tuple[Message, int, int]]:
            # * This is SuperTTT specific
        return QueueIter(self._processed)

    # -- SUPERTTT SPECIFIC* METHODS ---
    # * a generic connect/disconnect could be made, but we do special stuff with names in superttt

    def has_auth(self, uid: int) -> bool:
        """
        Does the provided uid have authority
        """
        if uid == UNKNOWN_UID:
            return False
        return uid == FACILITATOR_UID or uid == self.host

    def process(self):
        """
        We have custom behaviour which need to done as regularly as possible.
        """
        for incoming in QueueIter(self.incoming):
            msg, _, uid = incoming
            match msg:
                case ClientClosed():
                    if uid != MY_UID:
                        continue
                    self._processed.put_nowait(incoming)
                    self.disconnect()
                case ExistingConnections():
                    if not self.has_auth(uid):
                        continue
                    self._processed.put_nowait(incoming)
                    self.uid = msg.uid
                    self.connections[msg.uid] = self.name or "Me"
                    for connection in msg.uids:
                        if connection in self.connections or connection in self.connecting:
                            continue
                        self.connecting.append(connection)
                case ConnectionOpened():
                    if not self.has_auth(uid):
                        continue
                    self._processed.put_nowait(incoming)
                    if msg.uid in self.connections or msg in self.connecting:
                        continue
                    self.connecting.append(msg.uid)
                case ConnectionClosed():
                    if not self.has_auth(uid):
                        continue
                    self._processed.put_nowait(incoming)
                    if msg.uid in self.connecting:
                        self.connecting.remove(msg.uid)
                    self.connections.pop(msg.uid, None)
                case SetName():
                    self._processed.put_nowait(incoming)
                    if uid in self.connecting:
                        self.connecting.remove(uid)
                    self.connections[uid] = msg.name
                case SetHost():
                    if not self.has_auth(uid):
                        continue
                    self._processed.put_nowait(incoming)
                    self.host = uid
                case SetBoard():
                    if not self.has_auth(uid):
                        continue
                    self._processed.put_nowait(incoming)
                case SetPlayer():
                    if not self.has_auth(uid):
                        continue
                    self._processed.put_nowait(incoming)
                    if msg.is_player1:
                        self.player1 = msg.player
                    else:
                        self.player2 = msg.player
                case Kick():
                    if self.has_auth(uid) or msg.uid == self.uid:
                        self._processed.put_nowait(incoming)
                        self.disconnect()
                        return
                case SetTile():
                    if self.has_auth(uid):
                        self._processed.put_nowait(incoming)
                case SetTurn():
                    if self.has_auth(uid):
                        self._processed.put_nowait(incoming)

    def _reset(self):
        clear_queue(self.incoming)
        clear_queue(self.outgoing)
        clear_queue(self._processed)
        self.room: str | None = None
        self.uid: int | None = None
        self.host: int = UNKNOWN_UID
        self.player1: int = UNKNOWN_UID
        self.player2: int = UNKNOWN_UID
        self.connecting.clear()
        self.connections.clear()

    def start_hosting(self, name: str, is_local: bool):
        if self._is_hosting or self.facilitator.is_alive():
            self.disconnect()

        # A local client must use the private ip address even for a public facing host
        # Only get_public_ipv4 is blocking and 'expensive'
        local_room = get_roomcode(get_private_ipv4(), PORT)
        addr = get_private_ipv4() if is_local else get_public_ipv4()
        room = get_roomcode(addr, PORT)

        self.facilitator.reset()
        clear_queue(self.auth)
        self.facilitator.update_addr("0.0.0.0")
        self.facilitator.update_port(PORT)
        self.facilitator.start()

        self.connect(name, local_room)

        self.room = room # The room the local client uses can diverge from the actual room code
        self._is_hosting = True

    def connect(self, name: str, room: str):
        if self._is_connected or self.client.is_alive():
            self.disconnect()
        self.name = name

        self.client.reset()
        self._reset()
        self.client.update_addr(get_addr(room))
        self.client.start()
        self.room = room
        self._is_connected = True
        self.process()

    def disconnect(self):
        if not self._is_connected:
            return
        self.client.stop()
        self.client.watch()
        self._reset()

        if self._is_hosting:
            print("Ending Hosting")
            self.facilitator.stop()
            self.facilitator.watch()
            clear_queue(self.auth)

        self._is_connected = False
        self._is_hosting = False

    def is_player1(self, uid: int | None = None) -> bool:
        if uid is None:
            return self.player1 == MY_UID or self.player1 == self.uid
        return uid == self.player1

    def is_player2(self, uid: int | None = None) -> bool:
        if uid is None:
            return self.player2 == MY_UID or self.player2 == self.uid
        return uid == self.player2

    def is_spectator(self, uid: int | None = None) -> bool:
        return uid != self.player1 and uid != self.player2

    def is_connected(self, uid: int | None) -> bool:
        if uid is None:
            return self._is_connected
        return uid in self.connections

    def is_host(self, uid: int | None = None) -> bool:
        if uid is None:
            return self._is_hosting
        return uid == self.host

    def set_name(self, name: str):
        self.outgoing.put_nowait((SetName(name), ms_since_epoch()))
        self.name = name
        if self.uid is not None:
            self.connections[self.uid] = name


multiplayer = _Multiplayer()