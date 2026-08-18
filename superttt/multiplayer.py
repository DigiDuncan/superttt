"""
SuperTTT multiplayer messages and protocol. We are doing a "overactive" tcp p2p connection.
That means when a new connection comes in, every peer tells every other peer every piece of
relivant information. So with every new connection the host will tell everyone who player1 is,
and who player2 is, and that they are the host, and every client will tell every other client
their name.
"""
from dataclasses import dataclass

from superttt.lib.networking.message import Message


@dataclass
class SetHost(Message):
    uid: int # Tell other clients who the host is

@dataclass
class SetPlayer(Message):
    player: int # Player's networking UID
    is_player1: bool # Is the player player 1 or 2?

# TODO: Do we want names?
@dataclass
class SetPlayerName(Message): # The name is assigned with the uid of the sender
    name: str

@dataclass
class SetTile(Message):
    location: tuple[int, ...]


@dataclass
class SetTurn(Message):
    turn: int


class Connection:
    """
    Abstraction over Client, Facilitator.
    """

    def send_msg(self):
        pass

    def send_auth_msg(self):
        pass

    # TODO: return an Iterable which handles fetching from a queue until it is empty
    def msgs(self):
        pass

    def connect(self):
        pass

    def disconnect(self):
        pass

    def reconnect(self):
        pass