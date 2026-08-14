import random

from arcade import Camera2D, Sprite, SpriteList, Text, View, XYWH, LBWH, draw_rect_filled, draw_texture_rect, Rect, LRBT
from arcade.color import WHITE
import arcade.key

from pyglet.graphics import Batch, Group

from superttt.game import board
from superttt.game.board import State, Tile
from superttt.game.drawing import draw_board, get_tile_from_position, TEXTURES, get_rect_from_coordinate
from superttt.lib.utils import format_time
from .context import nav
from superttt.lib.gradient import draw_rect_gradient

DEBUG_FONT = "GohuFont 11 Nerd Font Mono"

class SuperTTTView(View):
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

        self.timer_text = Text(
            "0:00",
            10,
            self.height - 10,
            font_size=24,
            anchor_y="top",
            font_name="Static",
            color = arcade.color.RED
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
            self.next_moves = self.game.get_valid_moves_from_latest_move(self.latest_tile.id)
            self.current_turn = State.O if self.current_turn == State.X else State.X

        if (x, y) in self.quit.rect:
            nav.push(StartView())

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> bool | None:
        if self.debug:
            tile = get_tile_from_position((x, y), self.game, self.game_rect)
            if tile:
                self.debug_text.text = "[DEBUG] " + str(tile.id)
            else:
                self.debug_text.text = "[DEBUG]"

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

        if self.latest_tile and self.game.get_next_board_from_latest_move(self.latest_tile.id).state == State.NONE:
            for move in self.next_moves:
                draw_rect_filled(get_rect_from_coordinate(move, self.game_rect, self.game.size), (0, 255, 0, 128))

        self.timer_text.draw()
        self.spritelist.draw()

class StartView(View):
    def __init__(self) -> None:
        super().__init__()
        self.spritelist = SpriteList()

        self.gradient = (arcade.color.LIGHT_CYAN, arcade.color.CYAN)

        self.logo = Sprite("./resources/superttt/logo.png")
        self.logo.center_x = self.center_x
        self.logo.center_y = self.height * 0.75
        self.spritelist.append(self.logo)

        self.splash_text = Text("Splash did not load!", self.logo.center_x, self.logo.bottom + 30, anchor_y = "top", font_name = "Static", color = arcade.color.RED, font_size = 24)

        self.new_game = Sprite("./resources/superttt/new_game.png")
        self.new_game.scale = 0.5
        self.new_game.center_x = self.center_x
        self.new_game.center_y = self.height * 0.4
        self.spritelist.append(self.new_game)

        self.quit = Sprite("./resources/superttt/quit.png")
        self.quit.scale = 0.5
        self.quit.center_x = self.center_x
        self.quit.center_y = self.height * 0.25
        self.spritelist.append(self.quit)

        self.setup()

    def setup(self):
        with open("./resources/superttt/splashes.txt") as f:
            self.splash_text.text = random.choice(f.readlines()).strip()

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> bool | None:
        for button in [self.new_game, self.quit]:
            if (x, y) in button.rect:
                button.color = arcade.color.CYAN
            else:
                button.color = arcade.color.WHITE

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> bool | None:
        if (x, y) in self.new_game.rect:
            nav.push(ModeView())
        elif (x, y) in self.quit.rect:
            arcade.close_window()

    def on_key_press(self, symbol: int, modifiers: int) -> bool | None:
        if symbol == arcade.key.ENTER or symbol == arcade.key.NUM_ENTER:
            nav.push(SuperTTTView())
        if symbol == arcade.key.BACKSPACE:
            arcade.close_window()

    def on_draw(self) -> bool | None:
        self.clear()
        draw_rect_gradient(self.window.rect, self.gradient[0], self.gradient[1])
        self.spritelist.draw()
        self.splash_text.draw()

class RectText(Text):
    def __init__(self, text: str, x: float, y: float, color: tuple[int, int, int] | tuple[int, int, int, int] = arcade.color.WHITE, font_size: float = 12, width: int | None = None, align: str = "left", font_name: str | tuple[str, ...] = ("calibri", "arial"), bold: bool | str = False, italic: bool = False, anchor_x: str = "left", anchor_y: str = "baseline", multiline: bool = False, rotation: float = 0, batch: Batch | None = None, group: Group | None = None, z: float = 0, **kwargs):
        super().__init__(text, x, y, color, font_size, width, align, font_name, bold, italic, anchor_x, anchor_y, multiline, rotation, batch, group, z, **kwargs)

        self.hovered = False

    @property
    def rect(self) -> Rect:
        return LRBT(self.left, self.right, self.bottom, self.top)

class SettingsView(View):
    def __init__(self) -> None:
        super().__init__()
        self.spritelist = SpriteList()

        self.logo = Sprite("./resources/superttt/settings.png")
        self.logo.scale = 0.75
        self.logo.center_x = self.center_x
        self.logo.top = self.height - 10
        self.spritelist.append(self.logo)

        # This is what happens when I don't have Mint.
        self.start = Sprite("./resources/superttt/start.png")
        self.start.scale = 0.5
        self.start.bottom = 10
        self.start.right = self.width - 10
        self.spritelist.append(self.start)

        self.back = Sprite("./resources/superttt/back.png")
        self.back.scale = 0.5
        self.back.bottom = 10
        self.back.left = 10
        self.spritelist.append(self.back)

        self.text_batch = Batch()

        self.grid_size_label = self.splash_text = Text("Grid Size", self.width * 0.4, self.center_y + 50, anchor_x = "right", font_name = "Static", font_size = 32, batch = self.text_batch)
        self.depth_label = self.splash_text = Text("Depth", self.width * 0.4, self.center_y - 50, anchor_x = "right", font_name = "Static", font_size = 32, batch = self.text_batch)

        self.grid_size_2 = self.splash_text = RectText("2", self.width * 0.6, self.center_y + 50, font_name = "Static", font_size = 32, batch = self.text_batch)
        self.grid_size_3 = self.splash_text = RectText("3", self.width * 0.6 + 50, self.center_y + 50, font_name = "Static", font_size = 32, batch = self.text_batch)
        self.grid_size_4 = self.splash_text = RectText("4", self.width * 0.6 + 100, self.center_y + 50, font_name = "Static", font_size = 32, batch = self.text_batch)
        self.grid_size_5 = self.splash_text = RectText("5", self.width * 0.6 + 150, self.center_y + 50, font_name = "Static", font_size = 32, batch = self.text_batch)

        self.depth_1 = self.splash_text = RectText("1", self.width * 0.6, self.center_y - 50, font_name = "Static", font_size = 32, batch = self.text_batch)
        self.depth_2 = self.splash_text = RectText("2", self.width * 0.6 + 50, self.center_y - 50, font_name = "Static", font_size = 32, batch = self.text_batch)
        self.depth_3 = self.splash_text = RectText("3", self.width * 0.6 + 100, self.center_y - 50, font_name = "Static", font_size = 32, batch = self.text_batch)
        self.depth_4 = self.splash_text = RectText("4", self.width * 0.6 + 150, self.center_y +-50, font_name = "Static", font_size = 32, batch = self.text_batch)

        self.caution = Sprite("./resources/superttt/caution.png")
        self.caution.center_x = self.depth_4.rect.center_x
        self.caution.center_y = self.depth_4.rect.center_y
        self.caution.height = self.depth_4.rect.height
        self.caution.width = self.depth_4.rect.height
        self.caution.alpha = 128
        self.spritelist.append(self.caution)

        self.caution_text = Text("Depth 4 is extremely laggy, and will take several hours to play!\nSelect this at your own peril!",
                                 self.center_x, self.height * 0.25, anchor_x = "center", anchor_y = "center", font_name = "Static",
                                 font_size = 24, color = arcade.color.YELLOW, multiline = True, width = self.width / 2, align = "center")
        self.hovering_caution = False

        self.grid_size = 3
        self.depth = 2

        self.update_text_colors()

    def update_text_colors(self):
        for t in [self.grid_size_2, self.grid_size_3, self.grid_size_4, self.grid_size_5, self.depth_1, self.depth_2, self.depth_3, self.depth_4]:
            t.color = arcade.color.WHITE if not t.hovered else arcade.color.CYAN

        [self.grid_size_2, self.grid_size_3, self.grid_size_4, self.grid_size_5][self.grid_size - 2].color = arcade.color.RED
        [self.depth_1, self.depth_2, self.depth_3, self.depth_4][self.depth - 1].color = arcade.color.RED

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> bool | None:
        if (x, y) in self.start.rect:
            nav.push(SuperTTTView(self.grid_size, self.depth))
        elif (x, y) in self.back.rect:
            nav.pop()

        if (x, y) in self.grid_size_2.rect:
            self.grid_size = 2
        elif (x, y) in self.grid_size_3.rect:
            self.grid_size = 3
        elif (x, y) in self.grid_size_4.rect:
            self.grid_size = 4
        elif (x, y) in self.grid_size_5.rect:
            self.grid_size = 5

        if (x, y) in self.depth_1.rect:
            self.depth = 1
        elif (x, y) in self.depth_2.rect:
            self.depth = 2
        elif (x, y) in self.depth_3.rect:
            self.depth = 3
        elif (x, y) in self.depth_4.rect:
            self.depth = 4

        self.update_text_colors()

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> bool | None:
        self.hovering_caution = (x, y) in self.caution.rect
        for button in [self.start, self.back]:
            if (x, y) in button.rect:
                button.color = arcade.color.CYAN
            else:
                button.color = arcade.color.WHITE

        for text in [self.depth_1, self.depth_2, self.depth_3, self.depth_4,
                     self.grid_size_2, self.grid_size_3, self.grid_size_4, self.grid_size_5]:
            text.hovered = (x, y) in text.rect

        self.update_text_colors()
    
    def on_key_press(self, symbol: int, modifiers: int) -> bool | None:
        if symbol == arcade.key.BACKSPACE:
            nav.pop()

    def on_draw(self) -> bool | None:
        self.clear()
        self.spritelist.draw()
        self.text_batch.draw()
        if self.hovering_caution:
            self.caution_text.draw()

class ModeView(View):
    def __init__(self):
        super().__init__()

        self.spritelist = SpriteList()

        self.couch = Sprite("./resources/superttt/couch.png")
        self.couch.scale = 0.5
        self.couch.center_x = self.center_x
        self.couch.center_y = self.height * 0.75
        self.spritelist.append(self.couch)

        self.local = Sprite("./resources/superttt/local.png")
        self.local.scale = 0.5
        self.local.center_x = self.center_x
        self.local.center_y = self.center_y
        self.spritelist.append(self.local)

        self.online = Sprite("./resources/superttt/online.png")
        self.online.scale = 0.5
        self.online.center_x = self.center_x
        self.online.center_y = self.height * 0.25
        self.spritelist.append(self.online)

        self.back = Sprite("./resources/superttt/back.png")
        self.back.scale = 0.5
        self.back.bottom = 10
        self.back.left = 10
        self.spritelist.append(self.back)

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> bool | None:
        for button in [self.couch, self.local, self.online, self.back]:
            if (x, y) in button.rect:
                button.color = arcade.color.CYAN
            else:
                button.color = arcade.color.WHITE

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> bool | None:
        if (x, y) in self.couch.rect:
            nav.push(SettingsView())
        elif (x, y) in self.back.rect:
            nav.pop()

    def on_draw(self) -> bool | None:
        self.clear()
        self.spritelist.draw()
