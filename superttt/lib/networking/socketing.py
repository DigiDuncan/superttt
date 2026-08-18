import socket
import urllib.request
from time import time_ns

type IPv4Addr = tuple[str, int]


def get_private_ipv4() -> str:
    return socket.gethostbyname(socket.gethostname())


def get_public_ipv4() -> str:
    return urllib.request.urlopen("https://api.ipify.org").read().decode("utf8")


def ms_since_epoch() -> int:
    return time_ns() // 1_000_000


FACILITATOR_UID = 0x00  # The zero uid is reserved for the Facilitator
UNKNOWN_UID = 0x01  # the one uid is reserved for Clients who don't know their uid
