from queue import Empty, Queue
import socket
from typing import Iterable, Self
import urllib.request
from dataclasses import dataclass
from time import time_ns

from .message import Message

type IPv4Addr = tuple[str, int]


def get_private_ipv4() -> str:
    return socket.gethostbyname(socket.gethostname())


def get_public_ipv4() -> str:
    return urllib.request.urlopen("https://api.ipify.org").read().decode("utf8")


def ms_since_epoch() -> int:
    return time_ns() // 1_000_000


FACILITATOR_UID = 0x00  # The zero uid is reserved for the Facilitator
UNKNOWN_UID = 0x01  # the one uid is reserved for Clients who don't know their uid
MY_UID = 0x02 # this uid acts as an alias for my own uid if I don't know it yet

@dataclass
class ClientClosed(Message): ... # Used by client thread to tell application it has closed


@dataclass
class ExistingConnections(Message):
    uid: int # Your uid
    uids: tuple[int, ...]


@dataclass
class ConnectionOpened(Message):
    uid: int


@dataclass
class ConnectionClosed(Message):
    uid: int

class QueueIter[T](Iterable[T]):

    def __init__(self, queue: Queue[T]) -> None:
        self.q = queue

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> T:
        try:
            return self.q.get_nowait()
        except Empty:
            raise StopIteration