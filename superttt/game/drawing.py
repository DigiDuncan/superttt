from .board import Board, Tile, State
from arcade import Rect, LBWH, draw_texture_rect, load_texture, draw_rect_filled
from arcade.types import Point2, Color

from logging import getLogger

logger = getLogger("superttt")

TEXTURES = {name: load_texture(f"resources/superttt/{name}.png") for name in ('x', 'x_gray', 'o', 'o_gray', 'empty')}

def split_rect(rect: Rect, size: int) -> list[Rect]:
    new_rect_size = rect.scale(1 / size).size
    start_x, start_y = rect.bottom_left

    new_rects = []
    for i in range(size):
        for j in range(size):
            new_rects.append(LBWH(start_x + (new_rect_size.x * j), start_y + (new_rect_size.y * i), new_rect_size.x, new_rect_size.y))
    return new_rects

def draw_board(board: Board, rect: Rect):
    if rect.width != rect.height:
        logger.warning(f"Rect not a square! {rect.width}x{rect.height}")

    splits = split_rect(rect, board.size)

    if board.type == Tile:
        bg_rect = rect.scale(0.95)
        draw_rect_filled(bg_rect, Color.from_gray(50))

        for n, split in enumerate(splits):
            tile = board.items[n]
            if tile.state == State.NONE:
                draw_texture_rect(TEXTURES["empty"], split)
            elif tile.state == State.X:
                draw_texture_rect(TEXTURES["x"], split) if board.state == State.X else draw_texture_rect(TEXTURES["x_gray"], split)
            elif tile.state == State.O:
                draw_texture_rect(TEXTURES["o"], split) if board.state == State.O else draw_texture_rect(TEXTURES["o_gray"], split)
    else:
        for n, split in enumerate(splits):
            draw_board(board.items[n], split) # type: ignore -- it's always a Board at this point

def get_tile_from_position(point: Point2, board: Board, rect: Rect) -> Tile | None:
    splits = split_rect(rect, board.size)
    
    if board.type == Tile:
        for n, split in enumerate(splits):
            if point in split:
                return board.items[n] # type: ignore -- it's always a Tile at this point
    else:
        for n, split in enumerate(splits):
            if point in split:
                return get_tile_from_position(point, board.items[n], split) # type: ignore -- it's always a Board at this point
