from __future__ import annotations
from enum import StrEnum
from functools import cache
import math
from itertools import batched

from superttt.lib.utils import flatten

class State(StrEnum):
    NONE = "#"
    X = "X"
    O = "O"  # noqa: E741

type Data = tuple[str | Data, ...]

class Tile:
    def __init__(self, state: State | None = None, id: tuple[int, ...] | None = None) -> None:
        self.state: State = state if state else State.NONE
        self.id: tuple[int, ...] = id  # type: ignore -- it's not going to be None for long don't worry about it

    def __str__(self) -> str:
        return "X" if self.state == State.X else "O" if self.state == State.O else "#"

class Board:
    def __init__(self, items: list[Tile | Board] | None = None, id: tuple[int, ...] | None = None, parent = None) -> None:
        # Because of Arcade being bottom-up, the layout is:
        # 6 7 8
        # 3 4 5
        # 0 1 2
        self.items: list[Tile | Board] = items if items else []

        # winning combinations for this board size
        self.winning_combos = get_winning_combos(self.size)

        self.id: tuple[int, ...] = id  # type: ignore -- by the time you check the ID it's not None

    @property
    def state(self) -> State:
        return self.get_state()

    @property
    def data(self) -> Data:
        if self.type == Tile:
            return tuple(t.state.value for t in self.items)
        else:
            return tuple(b.data for b in self.items)  # type: ignore -- This should be a Board, I hope!!

    @property
    def stalemate(self) -> bool:
        return self.state == State.NONE and all(b.state != State.NONE for b in self.items)

    @property
    def size(self) -> int:
        return int(math.sqrt(len(self.items)))

    @property
    def type(self) -> type[Board] | type[Tile]:
        return type(self.items[0])

    @property
    def depth(self) -> int:
        return len(self.id)

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

    def get_item_from_id(self, id: tuple[int, ...]) -> Tile | Board:
        item = self
        for i in id:
            item = item.items[i]
        return item

    def get_next_board_from_latest_move(self, latest_move_coord: tuple[int, ...]) -> Board:
        valid_next_board = latest_move_coord[1:]
        board = self
        for coord in valid_next_board:
            board = board.items[coord]  # type: ignore -- This should be a Board, I hope!!

        return board

    def get_all_none_state_tiles(self):
        if self.type == Tile:
            if self.state != State.NONE:
                return []
            else:
                return [t for t in self.items if t.state == State.NONE]
        else:
            if self.state != State.NONE:
                return []
            else:
                return [b.get_all_none_state_tiles() for b in self.items]

    def get_valid_moves_from_latest_move(self, latest_move_coord: tuple[int, ...] | None) -> list[tuple[int, ...]]:
        if self.state != State.NONE:
            return []

        if latest_move_coord is None:
            return [t.id for t in flatten(self.get_all_none_state_tiles())]

        board = self.get_next_board_from_latest_move(latest_move_coord)

        if board.state != State.NONE:  # Wild
            return [t.id for t in flatten(self.get_all_none_state_tiles())]

        return [t.id for t in board.items if t.state == State.NONE]  # type: ignore -- This should be a Board, I hope!!

    @classmethod
    def from_data(cls, data: Data) -> Board:
        b = Board()
        for item in data:
            if isinstance(item, tuple):
                b.items.append(Board.from_data(item))
            elif isinstance(item, str):
                state = State.X if item == "X" else State.O if item == "O" else State.NONE
                b.items.append(Tile(state))
        return b

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

def create_board(size: int, depth: int, id: tuple[int, ...] = tuple()) -> Board:
    if depth == 0:
        return Tile(id = id)  # type: ignore
    board = Board([create_board(size, depth-1, (*id, idx)) for idx in range(size ** 2)], id)
    return board
