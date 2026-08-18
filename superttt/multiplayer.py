from dataclasses import dataclass

from superttt.lib.networking.message import Message


@dataclass
class SetHost(Message):
    uid: int # Tell other clients who the host is


@dataclass
class SetPlayer(Message):
    player: int # Player's networking UID
    is_player1: bool # Is the player player 1 or 2?


@dataclass
class SetTile(Message):
    location: tuple[int, ...]


@dataclass
class SetTurn(Message):
    turn: int