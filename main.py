from src.utils import dim2d
from src.game_window_snapshot import get_active_window_im
from src.game_parser import process_ref_to_state
from src.debug_tools import debug_print_state
from PIL import Image
import random
import time


import pyautogui as ag


def click_cell_in_game(window_region, game_state, x, y, left_click=True):
    wleft, wtop = window_region[:2]
    gleft, gtop = game_state['game_bbox'][:2]
    game_cell_dim = game_state['game_cell_width']
    center_w = game_cell_dim // 2
    click_fn = ag.leftClick if left_click else ag.rightClick

    click_fn(wleft+gleft+x*game_cell_dim+center_w,
             wtop+gtop+y*game_cell_dim+center_w)


NEIGHBOR8_VECTORS = [(1, 0), (1, 1), (0, 1), (-1, 1),
                     (-1, 0), (-1, -1), (0, -1), (1, -1)]


def copy_mat(mat):
    return [row[:] for row in mat]


def get2d(mat, x, y):
    W, H = dim2d(mat)
    if 0 <= x < W and 0 <= y < H:
        return mat[y][x]
    return None


def get_condition_neighbors(game_mat, x, y, condition):
    lookups = [(get2d(game_mat, x+dx, y+dy), x+dx, y+dy)
               for (dx, dy) in NEIGHBOR8_VECTORS]
    return [el for el in lookups if condition(el[0])]


def get_condition_neighbors_cnt(game_mat, x, y, condition):
    return len(get_condition_neighbors(game_mat, x, y, condition))


def distinct(l):
    return list(set(l))


def next_clicks(game_mat):
    game_mat = copy_mat(game_mat)
    UNCOVER_AS_SAFE = True
    FLAG_AS_BOMB = False
    W, H = dim2d(game_mat)
    clicks = []
    # RULE1: if cell "N" has exactly N neighbors unrevealed (? and !) then those two are bombs
    def cnd_unrevealed(cell): return cell in ['?', '!']
    for y in range(H):
        for x in range(W):
            cell_value = game_mat[y][x]
            is_bomb_cnt = isinstance(cell_value, int) and cell_value > 0
            unrevealed_neighbors = get_condition_neighbors(
                game_mat, x, y, cnd_unrevealed)
            if is_bomb_cnt and len(unrevealed_neighbors) == cell_value:
                # FLAG only those that are not flagged already.
                for neighbor in unrevealed_neighbors:
                    nv, nx, ny = neighbor
                    if nv != '?':
                        continue
                    game_mat[ny][nx] = '!'
                    clicks.append((nx, ny, FLAG_AS_BOMB))
    # Now we have clicked all easy to guess bombs.
    # Lets try to click where we know that there are definitely no bombs.
    def cnd_marked_bombs(cell): return cell == '!'
    def cnd_unmarked(cell): return cell == '?'
    for y in range(H):
        for x in range(W):
            cell_value = game_mat[y][x]
            is_bomb_cnt = isinstance(cell_value, int) and cell_value > 0
            bomb_marked_neighbors = get_condition_neighbors(
                game_mat, x, y, cnd_marked_bombs)
            unmarked_neighbors = get_condition_neighbors(
                game_mat, x, y, cnd_unmarked)
            # this cell has no more bombs around.
            if is_bomb_cnt and len(bomb_marked_neighbors) == cell_value:
                for _, nx, ny in unmarked_neighbors:
                    game_mat[ny][nx] = '_'
                    clicks.append((nx, ny, UNCOVER_AS_SAFE))

    if len(clicks) > 0:
        return clicks

    # ITS TIME FOR DEDUCTION!    
    print('cannot solve, deduction required.')
    return []



while True:
    im, window_region = get_active_window_im()
    #im = Image.open('gold_ref.png')
    if im is None:
        continue

    game_state = process_ref_to_state(im)
    game_mat = game_state['game_2d_state']
    debug_print_state(game_mat)
    print('\n')
    clicks = next_clicks(game_mat)
    print(clicks)
    for click in clicks:
        cx, cy, left_click = click
        click_cell_in_game(window_region, game_state, cx, cy, left_click)
