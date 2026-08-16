# pyright: reportOptionalOperand=false

from functools import reduce
from operator import or_

from arcade import Camera2D, Sprite, SpriteList, Text, View, XYWH, LBWH, draw_rect_filled, draw_rect_outline, draw_texture_rect
import arcade.key

from superttt.game import board
from superttt.game.board import State, Tile, create_board
from superttt.game.drawing import draw_board, get_tile_from_position, TEXTURES, get_rect_from_coordinate, split_rect
from superttt.game.game import Game
from superttt.lib.utils import ease_color, format_time, ease_rect, ease
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

        board = create_board(self.grid_size, self.depth)
        rect = XYWH(*self.center, self.height * 0.9, self.height * 0.9)
        self.game = Game(board, rect)

        self.current_turn: State = State.X
        top_space = self.window.rect.top - self.game.rect.top
        self.current_turn_rect = LBWH(self.game.rect.right - top_space, self.game.rect.top, top_space, top_space)

        self.latest_tile: Tile | None = None
        self.next_moves: list[tuple[int, ...]] = self.game.board.get_valid_moves_from_latest_move(None)
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
        self.quit.scale = 0.33333
        self.quit.bottom = 10
        self.quit.right = self.width - 10
        self.spritelist.append(self.quit)

        self.turn_label = Sprite("./resources/superttt/turn.png")
        ar = self.turn_label.rect.aspect_ratio
        self.turn_label.height = top_space - 10
        self.turn_label.width = (top_space - 10) * ar
        self.turn_label.bottom = self.game.rect.top + 5
        self.turn_label.right = self.current_turn_rect.left - 5
        self.spritelist.append(self.turn_label)

        self.timer_text = Text(
            "0:00",
            self.game.rect.left,
            self.game.rect.top,
            font_size=20,
            anchor_y="bottom",
            font_name="Static",
            color = arcade.color.RED
        )
        self.timer_shadow = Text(
                    "0:00",
                    self.game.rect.left + 1,
                    self.game.rect.top - 1,
                    font_size=20,
                    anchor_y="bottom",
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
        self.game.board = board.create_board(self.grid_size, self.depth)
        self.current_turn = State.X
        self.latest_tile = None
        self.next_moves = self.game.board.get_valid_moves_from_latest_move(None)
        self.time_elapsed: float = 0.0

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> bool | None:
        if self.paused:
            return
        tile = get_tile_from_position((x, y), self.game.board, self.game.rect)
        if tile:
            if tile.state != State.NONE:
                return
            if tile.id not in self.next_moves:
                return
            tile.state = self.current_turn
            self.latest_tile = tile
            self.last_move_time = self.time_elapsed
            self.next_moves = self.game.board.get_valid_moves_from_latest_move(self.latest_tile.id)
            self.current_turn = State.O if self.current_turn == State.X else State.X

        if (x, y) in self.quit.rect:
            nav.pop_to_start()

        self.game.update_state()

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> bool | None:
        tile = get_tile_from_position((x, y), self.game.board, self.game.rect)
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
            print(self.game.board.data)
        elif symbol == arcade.key.SPACE:
            self.paused = not self.paused
            self.paused_sprite.visible = self.paused

    def on_update(self, delta_time: float):
        if not self.paused:
            self.time_elapsed += delta_time
        self.timer_text.text = format_time(self.time_elapsed, 0)
        self.timer_shadow.text = format_time(self.time_elapsed, 0)

    def draw_next_move_animation(self):
        # "The move rule" animation
        # This code is a little insance, but it's a hardcoded animation so I'm not sure what else to do about it.
        if self.depth != 1 and self.latest_tile and self.next_moves and self.game.board.get_next_board_from_latest_move(self.latest_tile.id).state == State.NONE:
            if self.current_turn == State.X:
                color = ease_color(arcade.color.RED, arcade.color.CYAN, self.last_move_time, self.last_move_time + MOVE_TIME, self.time_elapsed)
            else:
                color = ease_color(arcade.color.CYAN, arcade.color.RED, self.last_move_time, self.last_move_time + MOVE_TIME, self.time_elapsed)
            with self.window.ctx.enabled(self.window.ctx.DEPTH_TEST):
                latest_tile_rect = get_rect_from_coordinate(self.latest_tile.id, self.game.rect, self.grid_size)
                new_move_rects = []
                for move in self.next_moves:
                    new_rect = get_rect_from_coordinate(move, self.game.rect, self.game.board.size)
                    draw_rect = ease_rect(latest_tile_rect, new_rect, self.last_move_time, self.last_move_time + MOVE_TIME, self.time_elapsed)
                    new_move_rects.append(draw_rect)
                    draw_rect_filled(draw_rect, color.replace(a = 127))
                outline = reduce(or_, new_move_rects)
                draw_rect_outline(outline, color, 3)
            grid_alpha = 255 if self.time_elapsed <= self.last_move_time + MOVE_TIME else int(ease(255, 0, self.last_move_time + MOVE_TIME, self.last_move_time + MOVE_TIME + MOVE_TIME, self.time_elapsed))
            super_board_id = self.latest_tile.id[:-1]
            super_board = get_rect_from_coordinate(super_board_id, self.game.rect, self.grid_size)
            super_super_board_id = super_board_id[1:]
            super_super_board = get_rect_from_coordinate(super_super_board_id, self.game.rect, self.grid_size)
            draw_rect = ease_rect(super_board, super_super_board, self.last_move_time, self.last_move_time + MOVE_TIME, self.time_elapsed)
            super_super_splits = split_rect(draw_rect, self.grid_size)
            with self.window.ctx.enabled(self.window.ctx.DEPTH_TEST):
                for sss in super_super_splits:
                    draw_rect_outline(sss, color.replace(a = grid_alpha), 1)

    def on_draw(self) -> bool | None:
        self.clear()
        draw_rect_gradient(self.window.rect, DARK_GRADIENT[0], DARK_GRADIENT[1])
        with self.camera.activate():
            self.game.spritelist.draw()
            draw_board(self.game.board, self.game.rect)
            self.draw_next_move_animation()
            if self.hover_id:
                draw_texture_rect(TEXTURES["x"] if self.current_turn == State.X else TEXTURES["o"], get_rect_from_coordinate(self.hover_id, self.game.rect, self.grid_size), alpha = 127)

        if self.current_turn == State.X:
            draw_texture_rect(TEXTURES["x"], self.current_turn_rect)
        else:
            draw_texture_rect(TEXTURES["o"], self.current_turn_rect)

        if self.debug:
            self.debug_text.draw()

        self.timer_shadow.draw()
        self.timer_text.draw()
        self.spritelist.draw()
