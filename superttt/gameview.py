from functools import reduce
from operator import or_

from arcade import Camera2D, Sprite, SpriteList, Text, View, XYWH, LBWH, draw_rect_filled, draw_rect_outline, draw_texture_rect
import arcade.key

from superttt.game import board
from superttt.game.board import State, Tile
from superttt.game.drawing import draw_board, get_tile_from_position, TEXTURES, get_rect_from_coordinate, split_rect
from superttt.lib.utils import format_time, ease_rect, ease
from .context import nav
from superttt.lib.gradient import draw_rect_gradient

DEBUG_FONT = "GohuFont 11 Nerd Font Mono"
GRADIENT = (arcade.color.LIGHT_CYAN, arcade.color.CYAN)
DARK_GRADIENT = (arcade.types.Color(0, 64, 64), arcade.color.BLACK)
MOVE_TIME = 0.5

class GameView(View):
    def __init__(self, grid_size: int = 3, depth: int = 2):
        super().__init__()
        self.camera = Camera2D(projection=XYWH(0, 0, *self.window.size))
        self.spritelist = SpriteList()

        self.grid_size = grid_size
        self.depth = depth

        self.game = board.create_board(self.grid_size, self.depth)
        self.game_rect = XYWH(*self.center, self.height * 0.9, self.height * 0.9)

        self.current_turn: State = State.X
        self.current_turn_rect = LBWH(10, 10, 100, 100)

        self.latest_tile: Tile | None = None
        self.next_moves: list[tuple[int, ...]] = self.game.get_valid_moves_from_latest_move(None)
        self.last_move_time = None
        self.hover_id = None

        self.time_elapsed: float = 0.0
        self.paused = False

        self.spritelist = SpriteList()
        self.paused_sprite = Sprite("./resources/superttt/paused.png")
        self.paused_sprite.center_x = self.center_x
        self.paused_sprite.center_y = self.center_y
        self.spritelist.append(self.paused_sprite)
        self.paused_sprite.visible = False

        self.quit = Sprite("./resources/superttt/quit.png")
        self.quit.scale = 0.5
        self.quit.bottom = 10
        self.quit.right = self.width - 10
        self.spritelist.append(self.quit)

        self.turn_label = Sprite("./resources/superttt/turn.png")
        self.turn_label.scale = 0.333
        self.turn_label.bottom = self.current_turn_rect.top + 10
        self.turn_label.center_x = self.current_turn_rect.center_x
        self.spritelist.append(self.turn_label)

        self.timer_text = Text(
            "0:00",
            10,
            self.height - 10,
            font_size=24,
            anchor_y="top",
            font_name="Static",
            color = arcade.color.RED
        )
        self.timer_shadow = Text(
                    "0:00",
                    11,
                    self.height - 11,
                    font_size=24,
                    anchor_y="top",
                    font_name="Static",
                    color = arcade.color.WHITE
        )

        self.debug = False
        self.debug_text = Text(
            "[DEBUG]",
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
        self.latest_tile = None
        self.next_moves = self.game.get_valid_moves_from_latest_move(None)
        self.time_elapsed: float = 0.0

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> bool | None:
        if self.paused:
            return
        tile = get_tile_from_position((x, y), self.game, self.game_rect)
        if tile:
            if tile.state != State.NONE:
                return
            if tile.id not in self.next_moves:
                return
            tile.state = self.current_turn
            self.latest_tile = tile
            self.last_move_time = self.time_elapsed
            self.next_moves = self.game.get_valid_moves_from_latest_move(self.latest_tile.id)
            self.current_turn = State.O if self.current_turn == State.X else State.X

        if (x, y) in self.quit.rect:
            nav.pop_to_start()

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> bool | None:
        tile = get_tile_from_position((x, y), self.game, self.game_rect)
        if self.debug:
            if tile:
                self.debug_text.text = "[DEBUG] " + str(tile.id)
            else:
                self.debug_text.text = "[DEBUG]"
        if tile:
            if tile.id in self.next_moves:
                self.hover_id = tile.id
            else:
                self.hover_id = None
        else:
            self.hover_id = None

    def on_key_press(self, symbol: int, modifiers: int) -> bool | None:
        if symbol == arcade.key.R:
            if self.debug:
                self.reset()
        elif symbol == arcade.key.D:
            self.debug = not self.debug
        elif symbol == arcade.key.P:
            print(self.game.data)
        elif symbol == arcade.key.SPACE:
            self.paused = not self.paused
            self.paused_sprite.visible = self.paused

    def on_update(self, delta_time: float):
        if not self.paused:
            self.time_elapsed += delta_time
        self.timer_text.text = format_time(self.time_elapsed, 0)
        self.timer_shadow.text = format_time(self.time_elapsed, 0)

    def on_draw(self) -> bool | None:
        self.clear()
        draw_rect_gradient(self.window.rect, DARK_GRADIENT[0], DARK_GRADIENT[1])
        with self.camera.activate():
            draw_board(self.game, self.game_rect)

        if self.current_turn == State.X:
            draw_texture_rect(TEXTURES["x"], self.current_turn_rect)
        else:
            draw_texture_rect(TEXTURES["o"], self.current_turn_rect)

        if self.debug:
            self.debug_text.draw()

        if self.depth != 1 and self.latest_tile and self.next_moves and self.game.get_next_board_from_latest_move(self.latest_tile.id).state == State.NONE:
            with self.window.ctx.enabled(self.window.ctx.DEPTH_TEST):
                latest_tile_rect = get_rect_from_coordinate(self.latest_tile.id, self.game_rect, self.grid_size)
                new_move_rects = []
                for move in self.next_moves:
                    new_rect = get_rect_from_coordinate(move, self.game_rect, self.game.size)
                    draw_rect = ease_rect(latest_tile_rect, new_rect, self.last_move_time, self.last_move_time + MOVE_TIME, self.time_elapsed)
                    new_move_rects.append(draw_rect)
                    draw_rect_filled(draw_rect, (0, 255, 0, 128))
                outline = reduce(or_, new_move_rects)
                draw_rect_outline(outline, arcade.color.GREEN, 3)
            grid_alpha = 255 if self.time_elapsed <= self.last_move_time + MOVE_TIME else int(ease(255, 0, self.last_move_time + MOVE_TIME, self.last_move_time + MOVE_TIME + MOVE_TIME, self.time_elapsed))
            super_board_id = self.latest_tile.id[:-1]
            super_board = get_rect_from_coordinate(super_board_id, self.game_rect, self.grid_size)
            super_super_board_id = super_board_id[1:]
            super_super_board = get_rect_from_coordinate(super_super_board_id, self.game_rect, self.grid_size)
            draw_rect = ease_rect(super_board, super_super_board, self.last_move_time, self.last_move_time + MOVE_TIME, self.time_elapsed)
            super_super_splits = split_rect(draw_rect, self.grid_size)
            with self.window.ctx.enabled(self.window.ctx.DEPTH_TEST):
                for sss in super_super_splits:
                    draw_rect_outline(sss, arcade.color.GREEN.replace(a = grid_alpha), 1)

        self.timer_shadow.draw()
        self.timer_text.draw()
        self.spritelist.draw()
        if self.hover_id:
            draw_texture_rect(TEXTURES["x"] if self.current_turn == State.X else TEXTURES["o"], get_rect_from_coordinate(self.hover_id, self.game_rect, self.grid_size), alpha = 127)
