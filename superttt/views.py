import random

import arcade.key
from arcade import LRBT, Rect, Sprite, SpriteList, Text, View
from pyglet.graphics import Batch, Group

from superttt.gameview import GameView
from superttt.lib.gradient import draw_rect_gradient

from .context import nav

DEBUG_FONT = "GohuFont 11 Nerd Font Mono"
GRADIENT = (arcade.color.LIGHT_CYAN, arcade.color.CYAN)
DARK_GRADIENT = (arcade.color.DARK_CYAN, arcade.color.BLACK)
MOVE_TIME = 0.5

class StartView(View):
    def __init__(self) -> None:
        super().__init__()
        self.spritelist = SpriteList()

        self.logo = Sprite("./resources/superttt/logo.png")
        self.logo.center_x = self.center_x
        self.logo.center_y = self.height * 0.75
        self.spritelist.append(self.logo)

        self.splash_text = Text("Splash did not load!", self.logo.center_x, self.logo.bottom + 30, anchor_y = "top", font_name = "Static", color = arcade.color.RED, font_size = 24)
        self.splash_shadow = Text("Splash did not load!", self.logo.center_x + 2, self.logo.bottom + 28, anchor_y = "top", font_name = "Static", color = arcade.color.WHITE, font_size = 24)

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
            s = random.choice(f.readlines()).strip()
            self.splash_shadow.text = s
            self.splash_text.text = s

    def on_show_view(self) -> None:
        self.setup()

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
            nav.push(GameView())
        if symbol == arcade.key.BACKSPACE:
            arcade.close_window()

    def on_draw(self) -> bool | None:
        self.clear()
        draw_rect_gradient(self.window.rect, GRADIENT[0], GRADIENT[1])
        self.spritelist.draw()
        self.splash_shadow.draw()
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
            nav.push(GameView(self.grid_size, self.depth))
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
        draw_rect_gradient(self.window.rect, DARK_GRADIENT[0], DARK_GRADIENT[1])
        self.spritelist.draw()
        self.text_batch.draw()
        if self.hovering_caution:
            self.caution_text.draw()

class HostView(View):

    def __init__(self, is_local: bool) -> None:
        super().__init__()
        self.is_local: bool = is_local
        # TODO: text input for name
        # TODO: Marker for who is Player1, Player2, and Host

        # TODO: Setup a Facilitator and local Client
        # TODO: Get own uid, set myself as player1
        # TODO: show roomcode based on is_local

        # TODO: remember player2 and spectators
        # TODO: add ability to swap which player is which

class JoinView(View):

    def __init__(self) -> None:
        super().__init__()

        # TODO: text input for room code
        # TODO: text input for name
        # TODO: Marker for who is Player1, Player2, and Host


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
        self.local.color = arcade.color.GRAY
        self.spritelist.append(self.local)

        self.online = Sprite("./resources/superttt/online.png")
        self.online.scale = 0.5
        self.online.center_x = self.center_x
        self.online.center_y = self.height * 0.25
        self.online.color = arcade.color.GRAY
        self.spritelist.append(self.online)

        self.back = Sprite("./resources/superttt/back.png")
        self.back.scale = 0.5
        self.back.bottom = 10
        self.back.left = 10
        self.spritelist.append(self.back)

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> bool | None:
        for button in [self.couch, self.back]:
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
        draw_rect_gradient(self.window.rect, DARK_GRADIENT[0], DARK_GRADIENT[1])
        self.spritelist.draw()
