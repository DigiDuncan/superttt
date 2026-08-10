from arcade import Camera2D, Rect, Text, View, XYWH, LBWH, draw_rect_filled, draw_rect_outline, draw_texture_rect
import arcade.key

from superttt.game import board
from superttt.game.board import State, Tile
from superttt.game.drawing import draw_board, get_tile_from_position, TEXTURES, get_rect_from_coordinate

DEBUG_FONT = "GohuFont 11 Nerd Font Mono"

class SuperTTTView(View):
    def __init__(self):
        super().__init__()
        self.camera = Camera2D(projection=XYWH(0, 0, *self.window.size))

        self.grid_size = 3
        self.depth = 3

        self.game = board.create_board(self.grid_size, self.depth)
        self.game_rect = XYWH(*self.center, self.height * 0.9, self.height * 0.9)

        self.current_turn: State = State.X
        self.current_turn_rect = LBWH(10, 10, 100, 100)

        self.latest_tile: Tile | None = None
        self.next_moves: list[tuple[int, ...]] = []

        self.debug = False
        self.debug_text = Text(
            "DEBUG",
            5,
            self.height - 5,
            font_size=11,
            anchor_y="top",
            font_name=DEBUG_FONT,
            multiline=True,
            width=self.width / 2,
        )

    def reset(self):
        self.game = board.create_board(self.grid_size, self.depth)
        self.current_turn = State.X

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> bool | None:
        tile = get_tile_from_position((x, y), self.game, self.game_rect)
        if tile:
            if tile.state != State.NONE:
                return
            if self.next_moves and tile.id not in self.next_moves:
                return
            tile.state = self.current_turn
            self.latest_tile = tile
            self.next_moves = self.game.get_valid_moves_from_latest_move(self.latest_tile.id)
            self.current_turn = State.O if self.current_turn == State.X else State.X

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> bool | None:
        tile = get_tile_from_position((x, y), self.game, self.game_rect)
        if tile:
            self.debug_text.text = str(tile.id)

    def on_key_press(self, symbol: int, modifiers: int) -> bool | None:
        if symbol == arcade.key.R:
            self.reset()
        if symbol == arcade.key.D:
            self.debug = not self.debug

    def on_draw(self) -> bool | None:
        self.clear()
        with self.camera.activate():
            draw_board(self.game, self.game_rect)

        if self.current_turn == State.X:
            draw_texture_rect(TEXTURES["x"], self.current_turn_rect)
        else:
            draw_texture_rect(TEXTURES["o"], self.current_turn_rect)

        if self.debug:
            self.debug_text.draw()

        if self.next_moves:
            for move in self.next_moves:
                draw_rect_filled(get_rect_from_coordinate(move, self.game_rect, self.game.size), (0, 255, 0, 128))
