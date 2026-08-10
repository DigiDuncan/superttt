from __future__ import annotations
from enum import Enum
from functools import cache
import math
from itertools import batched

class State(Enum):
    NONE = None
    X = "X"
    O = "O"  # noqa: E741

class Tile:
    def __init__(self, state: State | None = None) -> None:
        self.state: State = state if state else State.NONE

    def __str__(self) -> str:
        return "X" if self.state == State.X else "O" if self.state == State.O else "?"

class Board:
    def __init__(self, items: list[Tile | Board] | None = None) -> None:
        # Because of Arcade being bottom-up, the layout is:
        # 6 7 8
        # 3 4 5
        # 0 1 2
        self.items: list[Tile | Board] = items if items else []

        # winning combinations for this board size
        self.winning_combos = get_winning_combos(self.size)

    @property
    def state(self) -> State:
        return self.get_state()

    @property
    def stalemate(self) -> bool:
        return self.state == State.NONE and all(b.state != State.NONE for b in self.items)

    @property
    def size(self) -> int:
        return int(math.sqrt(len(self.items)))

    @property
    def type(self) -> type[Board] | type[Tile]:
        return type(self.items[0])

    def get_state(self) -> State:
        for s in [State.X, State.O]:
            for combo in self.winning_combos:
                if all(self.items[n].state == s for n in combo):
                    return s
        return State.NONE

    def set_state(self, row: int, col: int, state: State | str | None):
        if state is None:
            state = State.NONE
        elif state == "X":
            state = State.X
        elif state == "O":
            state = State.O
        else:
            raise ValueError(f"State not valid! {state}")

        tile = self.items[(row * 3) + col]

        if not isinstance(tile, Tile):
            raise TypeError("Can't set state of a Board directly!")
        
        tile.state = state

    def __str__(self) -> str:
        if self.type == Tile:
            chunks = [list(batch) for batch in batched(self.items, self.size)]
            return "\n".join(' '.join([str(t) for t in c]) for c in chunks[::-1])
        else:
            return f"\n{'=' * (self.size * 2 - 1)}\n".join(str(b) for b in self.items)

@cache
def get_winning_combos(size: int) -> list[list[int]]:
    winning_combos = []
    # Horiz
    for n in range(0, size ** 2, size):
        winning_combos.append(list(range(n, n + size)))
    # Vert
    for n in range(size):
        winning_combos.append(list(range(n, size ** 2, size)))
    # Diag 1
    winning_combos.append(list(range(0, size ** 2, size + 1)))
    # Diag 2
    winning_combos.append(list(range(size - 1, size ** 2 - 1, size - 1)))
    return winning_combos

def create_board(size: int, depth: int) -> Board:
    if depth == 0:
        return Tile()  # type: ignore
    return Board([create_board(size, depth-1) for _ in range(size ** 2)])
