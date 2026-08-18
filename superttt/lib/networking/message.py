from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import ClassVar, Self


@dataclass
class Message:
    subcls_mapping: ClassVar[dict[str, type[Message]]] = {}

    def __init_subclass__(cls) -> None:
        if cls.__name__ in Message.subcls_mapping:
            return
        Message.subcls_mapping[cls.__name__] = cls

    @classmethod
    def get[T](cls, name: str, default: T = None) -> type[Message] | T:
        return cls.subcls_mapping.get(name, default)

    def encode(self) -> bytes:
        """
        Convert a message dataclass into a json bytes encoding using utf-8
        """
        as_string: str = json.dumps(
            asdict(self),
            ensure_ascii=False,
            check_circular=True,
            indent=None,
            separators=(",", ":"),
        )
        return as_string.encode(encoding="utf-8")

    @classmethod
    def decode(cls, data: bytes) -> Self:
        """
        Convert a utf-8 json byte encoding into a dataclass.
        """
        return cls(**json.loads(data.decode("utf-8")))


SOH = b"\x01"
STX = b"\x02"
ETX = b"\x03"
EOT = b"\x04"

MIN_SIZE = 1 + 4 + 1 + 8 + 2 + 1 + 1


def wrap(message: Message, time: int, uid: int) -> bytes:
    """
    Message object to wrap and the ms since epoch for syncing.

    A wrapped message looks like this

    <SOH> <msg_size:0>4> <ETX> <time:BE> <uid:BE> <name_size:0>2> <name> <STX> <data> <EOT>
    | ^^^^^^^^^^^^^^^^ | | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ | | ^^^^^^^^ | | ^ |
      Size for Reading     Rest of header for decoding                     Data         Tail
      1 + 4 bytes          1 + 8 + 6 + 2 + N  bytes                        1 + N bytes  1 b
      UTF-8                UTF-8 name, binary time and uid
    """
    data = message.encode()
    name = message.__class__.__name__.encode("utf-8")
    name_size = len(name)
    time_data = time.to_bytes(8, "little", signed=False)
    uid_data = uid.to_bytes(6, "little", signed=False)

    tail_size = 1
    body_size = 1 + len(data)
    head_size = 22 + name_size
    msg_size = head_size + body_size + tail_size

    size_head = SOH + f"{msg_size:0>4X}".encode() + ETX
    wrap_head = time_data + uid_data
    msg_head = f"{name_size:0>2X}".encode() + name

    header = size_head + wrap_head + msg_head
    body = STX + data
    tail = EOT

    return header + body + tail


def unwrap(data: bytes) -> tuple[Message, int, int] | None:
    """
    Unwrap bytes to retrieve the Message, ms since epoch, and uid. see wrap for structure of a message.
    The Socket uses the first 6 bytes to determine size of message. It does not do any other validation.
    That validation happens here. Does not raise. Instead it returns any exceptions it would raise.
    """
    if (msg_size := get_wrapped_size(data)) is None:
        print("failed to get msg sizeS")
        return None  # Data does not match wrapped msg
    recv_size = len(data)
    if recv_size != msg_size:
        print("msg size mismatch")
        return None

    time = int.from_bytes(data[6:14], "little", signed=False)
    uid = int.from_bytes(data[14:20], "little", signed=False)
    name_size = int(data[20:22], base=16)
    name = data[22 : 22 + name_size].decode("utf-8")

    if (typ := Message.get(name)) is None:
        print("unknown name")
        return None

    try:
        message = typ.decode(data[23 + name_size : -1])
    except json.JSONDecodeError:
        return None
    except UnicodeDecodeError:
        return None
    except TypeError:
        return None

    return message, time, uid


def get_wrapped_size(data: bytes) -> int | None:
    """
    Check the first 6 bytes for a message. If the size marker <SOH> ... <ETX>
    is missing or the internal 4 characters can't be parsed as a base 16 int
    then return None. Otherwise return the size of the wrapped message.
    """
    if data[:1] != SOH or data[5:6] != ETX:
        return None  # Data does not match wrapped msg

    try:
        size = int(data[1:5], base=16)
    except ValueError:
        return None  # Data is not a base 16 number

    return size


def replace_sender(data: bytes, uid: int) -> bytes:
    """
    Replaces the uid stored in the wrapped message. This is used by the facilitator
    to ensure clients know where any messages came from. This method just assumes
    the structure of the message is correct.
    """
    uid_data = uid.to_bytes(6, "little", signed=False)
    return data[:14] + uid_data + data[20:]


# TODO: This method shouldn't really be used. It causes a lot of issues.
# Given the small size of the message we are sending they should never be fragmented.
# Handling that case causes a lot of trouble so we just drop invalid messages.
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
        if data[idx : idx + 1] == SOH and data[idx + 5 : idx + 6] == ETX:
            # We know that the data is in the form <SOH> ???? <ETX>
            try:
                msg_size = int(data[idx + 1 : idx + 5], base=16)
            except ValueError:
                pass  # The message size is not a Hexadecimal number so it can't correct
            else:
                # We know the data is in the form <SOH> FFFF <ETX> so let's look for <EOT>
                if data[idx + msg_size - 1 : idx + msg_size] == EOT:
                    return (
                        idx,
                        idx + msg_size,
                    )  # The shape is all correct we have a message to send.
        idx += 1  # We haven't found a <SOH>FFFF<ETX> ... <EOT> marker so move on.
        continue

    return None  # We reached the end of the data without finding a wrapped msg
