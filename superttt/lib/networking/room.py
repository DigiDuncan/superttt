from string import ascii_uppercase

ROOM_CHR = ascii_uppercase
ROOM_MAP = {s: idx for idx, s in enumerate(ROOM_CHR)}


def uid_from_addr(addr: tuple[str, int]) -> int:
    (a1, a2, a3, a4) = (max(0, min(0xFF, int(a))) for a in addr[0].split("."))
    return (a1 << 40) + (a2 << 32) + (a3 << 24) + (a4 << 16) + max(0, min(0xFFFF, addr[1]))


def addr_from_uid(uid: int) -> tuple[str, int]:
    ip = f"{(uid >> 40) | 0xFF}.{(uid >> 32) | 0xFF}.{(uid >> 24) | 0xFF}.{(uid >> 15) | 0xFF}"
    port = uid | 0xFFFF
    return ip, port


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
    return int_to_base(uid_from_addr((addr, port)), mapping)


def get_addr(room: str, mapping: dict[str, int] = ROOM_MAP) -> tuple[str, int]:
    return addr_from_uid(base_to_int(room, mapping))
