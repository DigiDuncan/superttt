import arcade

from .board import Board, Tile, State
from arcade import Rect, LBWH, draw_rect_outline, draw_texture_rect, load_texture, draw_rect_filled
from arcade.types import Point2, Color
import arcade.color

from logging import getLogger

logger = getLogger("superttt")

TEXTURES = {name: load_texture(f"resources/superttt/{name}.png") for name in ('x', 'x_gray', 'o', 'o_gray', 'empty', 'stalemate')}

DEPTH_COLORS = {
    0: arcade.color.RED,
    1: arcade.color.GREEN,
    2: arcade.color.BLUE,
    3: arcade.color.YELLOW,
    4: arcade.color.PINK
}

def split_rect(rect: Rect, grid_size: int) -> list[Rect]:
    new_rect_size = rect.scale(1 / grid_size).size
    start_x, start_y = rect.bottom_left

    new_rects = []
    for i in range(grid_size):
        for j in range(grid_size):
            new_rects.append(LBWH(start_x + (new_rect_size.x * j), start_y + (new_rect_size.y * i), new_rect_size.x, new_rect_size.y))
    return new_rects

def draw_board(board: Board, rect: Rect):
    if rect.width != rect.height:
        logger.warning(f"Rect not a square! {rect.width}x{rect.height}")

    splits = split_rect(rect, board.size)
    bg_rect = rect.scale(0.95)

    if board.type == Tile:
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
        bg_rect = rect.scale(1)
        draw_rect_outline(bg_rect, arcade.color.WHITE)
        for n, split in enumerate(splits):
            draw_board(board.items[n], split) # type: ignore -- it's always a Board at this point

    if board.state != State.NONE:
        draw_rect_filled(bg_rect, (0, 0, 0, 200))
        if board.state == State.X:
            draw_texture_rect(TEXTURES["x"], bg_rect, alpha = 128)
        elif board.state == State.O:
            draw_texture_rect(TEXTURES["o"], bg_rect, alpha = 128)

    if board.stalemate:
        draw_texture_rect(TEXTURES["stalemate"], bg_rect, alpha = 128)

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

def get_rect_from_coordinate(coord: tuple[int, ...], rect: Rect, grid_size: int) -> Rect:
    current_rect = rect
    for n, i in enumerate(coord):
        splits = split_rect(current_rect, grid_size)
        current_rect = splits[i]
    return current_rect
