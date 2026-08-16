from typing import Any

from arcade import Rect, Sprite, SpriteList

from superttt.game.board import Board, State, Tile
from superttt.game.drawing import TEXTURES, split_rect

class TileSprite(Sprite):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.id: tuple[int, ...] = ()

class Game():
    def __init__(self, board: Board, rect: Rect) -> None:
        self.board = board
        self.rect = rect
        self.spritelist = SpriteList()

        self.fill_sprite_list(self.board, self.rect, self.spritelist)

    @staticmethod
    def fill_sprite_list(board: Board, rect: Rect, spritelist: SpriteList, id: tuple[int, ...] = None) -> None:
        splits = split_rect(rect, board.size)
        id = id if id else tuple()

        if board.type == Tile:
            for n, split in enumerate(splits):
                tile = board.items[n]
                if tile.state == State.NONE:
                    tex = TEXTURES["empty"]
                elif tile.state == State.X:
                    tex = TEXTURES["x"] if board.state == State.X else TEXTURES["x_gray"]
                elif tile.state == State.O:
                    tex = TEXTURES["o"] if board.state == State.O else TEXTURES["o_gray"]

                sprite = TileSprite(tex)
                sprite.center_x = split.center_x
                sprite.center_y = split.center_y
                sprite.height = split.height
                sprite.width = split.width
                sprite.id = id + (n,)
                spritelist.append(sprite)

        elif board.type == Board:
            for n, split in enumerate(splits):
                Game.fill_sprite_list(board.items[n], split, spritelist, id + (n, ))

    def update_state(self):
        for s in self.spritelist:
            tile = self.board.get_item_from_id(s.id)
            board = self.board.get_item_from_id(s.id[:-1])
            if tile.state == State.NONE:
                tex = TEXTURES["empty"]
            elif tile.state == State.X:
                tex = TEXTURES["x"] if board.state == State.X else TEXTURES["x_gray"]
            elif tile.state == State.O:
                tex = TEXTURES["o"] if board.state == State.O else TEXTURES["o_gray"]
            s.texture = tex

    def get_tilesprite_from_id(self, id: tuple[int, ...]) -> TileSprite:
        return next(s for s in self.spritelist if s.id == id)
