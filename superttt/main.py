from arcade import Camera2D, View, XYWH

from superttt.game import board
from superttt.game.drawing import draw_board, get_tile_from_position

class SuperTTTView(View):
    def __init__(self):
        super().__init__()
        self.camera = Camera2D(projection=XYWH(0, 0, *self.window.size))

        self.game = board.create_board(3, 2)
        self.game_rect = XYWH(*self.center, self.height * 0.9, self.height * 0.9)

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> bool | None:
        tile = get_tile_from_position((x, y), self.game, self.game_rect)
        if tile:
            if tile.state == board.State.NONE:
                tile.state = board.State.X
            elif tile.state == board.State.X:
                tile.state = board.State.O
            else:
                tile.state = board.State.NONE

    def on_draw(self) -> bool | None:
        self.clear()
        with self.camera.activate():
            draw_board(self.game, self.game_rect)
