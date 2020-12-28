import os
from src.utils import dim2d
from src.game_window_snapshot import get_active_window_im
from src.game_parser import process_ref_to_state
from src.debug_tools import debug_print_state
from PIL import Image
import itertools
import random
import time
import shutil


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


def list_intersection(l1, l2):
    return list(set(l1).intersection(set(l2)))


def next_clicks(game_mat):
    game_mat = copy_mat(game_mat)
    UNCOVER_AS_SAFE = True
    FLAG_AS_BOMB = False
    W, H = dim2d(game_mat)
    clicks = []
    # RULE1: if cell "N" has exactly N neighbors unrevealed (marked ? and !) then those two are bombs
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

    # RULE2: Because RULE1 flagged all 100% bombs, we can now check cells that
    # have all bombs found and the rest neighbor cells are safe cells (no bombs) revealed them, so the game can update and give us more information.
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

    # We got some solutions that 100% work from RULE 1 & RULE 2, use them so we get updated game state
    if len(clicks) > 0:
        return clicks

    print('cannot solve simply, deduction required. expect some computational time for next step.')

    # RULE 3: if rules 1 and 2 fail we must go hardcore.
    # https://www.youtube.com/watch?v=fQGbXmkSArs
    # Find cells with bomb count that still have unresolved bombs around them.
    # (4 has 5x ? and 1x ! --> 3 out of 5x ? are bombs but we don't know which)
    unsolved_cells = []
    for y in range(H):
        for x in range(W):
            cell_value = game_mat[y][x]
            is_bomb_cnt = isinstance(cell_value, int) and cell_value > 0
            if not is_bomb_cnt:
                continue

            solved_neighbors_cnt = get_condition_neighbors_cnt(
                game_mat, x, y, lambda cell: cell == '!')
            left_unsolved = cell_value - solved_neighbors_cnt

            assert left_unsolved >= 0
            if left_unsolved != 0:
                unsolved_cells.append((x, y, solved_neighbors_cnt))

    # start solving with cells that already have most neighbors solved. (this way we start solving those with least combinations required - greedy)
    unsolved_cells = sorted(unsolved_cells, key=lambda v: v[2], reverse=True)
    traverse_memo = dict()
    recursion_lock = dict()
    def traversed(x, y): (x, y) in traverse_memo

    def assert_bombs(picked_cells):
        for _, px, py in picked_cells:
            game_mat[py][px] = '!'

    def revert_assert_bombs(picked_cells):
        for _, px, py in picked_cells:
            game_mat[py][px] = '?'

    def neighbors_still_ok(cx, cy):
        # when TMP bomb is flaged, are states of neighbor cells still ok? N still has less or equal to N bomb flags?
        for nv, nx, ny in get_condition_neighbors(game_mat, cx, cy, lambda cell: isinstance(cell, int) and cell > 0):
            flag_cnt = get_condition_neighbors_cnt(
                game_mat, nx, ny, lambda cell: cell == '!')
            if flag_cnt > nv:
                return False
        return True

    def deduct_cell_solution(maybe_bomb_cells_checked, unknown_cells_checked, cx, cy):
        traverse_memo[(cx, cy)] = True
        recursion_lock[(cx, cy)] = True

        cell_value = game_mat[cy][cx]
        free_cells = get_condition_neighbors(
            game_mat, cx, cy, lambda cell: cell == '?')

        # a.k.a. visited cells
        for cell in free_cells:
            unknown_cells_checked.append(cell)

        solved_cells = get_condition_neighbors(
            game_mat, cx, cy, lambda cell: cell == '!')
        must_guess_cells_cnt = cell_value - len(solved_cells)

        assert len(free_cells) >= must_guess_cells_cnt
        solutions = []
        # if must_guess_cells_cnt == 0 then no new bombs will be asserted.
        # solution will be empty tuple, but it wont be added to final list (maybe bomb cells)
        # but if current position gets positive feedback from neighbors then we accept it (empty bomb tuple)

        # from all the free cells around current cell get all combination of bombs (pick k bombs from list of N free cells on every possible way)
        for picked_cells in itertools.combinations(free_cells, must_guess_cells_cnt):
            assert_bombs(picked_cells)
            neighbors_ok = all([neighbors_still_ok(px, py)
                                for _, px, py in picked_cells])

            if not neighbors_ok:
                revert_assert_bombs(picked_cells)
                continue

            # recursion lock is needed so we dont get into a loop.
            bomb_indicator_neighbors = [
                n for n in get_condition_neighbors(game_mat, cx, cy, lambda cell: isinstance(cell, int) and cell > 0)
                if (n[1], n[2]) not in recursion_lock
            ]

            neighbors_solved = True
            # check neighbor cells if our free cells intersect with theirs
            for _, nx, ny in bomb_indicator_neighbors:
                revert_assert_bombs(picked_cells)
                # revert bombs so neighbor actually gets common cells (because this bomb is only assumed to be)
                # but keep bombs planted from other frames. (so only revert those potential bombs to get free cells)
                neighbor_free_cells = get_condition_neighbors(
                    game_mat, nx, ny, lambda cell: cell == '?')
                assert_bombs(picked_cells)
                must_check_neighbor = len(list_intersection(
                    free_cells, neighbor_free_cells)) > 0
                # we check neighbors whose free cells intersect with ours. Our bomb flagging affects their position.
                # this condition is mostly true for diagonal neighbors we don't want to check them (they will be checked by indirectly)
                if not must_check_neighbor:
                    continue

                solved = deduct_cell_solution(
                    maybe_bomb_cells_checked, unknown_cells_checked, nx, ny)
                if not solved:
                    neighbors_solved = False
                    break

            revert_assert_bombs(picked_cells)

            if neighbors_solved:
                # if we solved neighbors from recursion (positive feedback), our solution is correct or accepted ;)
                solutions.append(picked_cells)

        no_solutions = len(solutions) == 0

        if no_solutions:
            del recursion_lock[(cx, cy)]
            return False

        for solution_bombs in solutions:
            # now each (potential but accepted) bomb for that tile
            for solution in solution_bombs:
                maybe_bomb_cells_checked.append(solution)

        del recursion_lock[(cx, cy)]
        return True

    for ucell in unsolved_cells:
        cx, cy, _ = ucell
        if traversed(cx, cy):
            # this cell was already used in deduction from previous cells. If solution was found we wouldn't come here (we exit on success solution)
            # therefore this cell yields no solution.
            continue

        cells_checked = []
        cells_maybe_bomb = []
        solution = deduct_cell_solution(
            cells_maybe_bomb, cells_checked, cx, cy)
        if solution:
            # out of all solutions (maybe bombs) find set of cells where no bomb was found. Those are 100% (if algorithm works) safe.
            danger_cells = distinct(cells_maybe_bomb)
            checked_cells = distinct(cells_checked)
            safe_cells = list(set(checked_cells) - set(danger_cells))
            # its also an option that the field is too ambiguous. Try with different unsolved cells - skip.
            if len(safe_cells) == 0:
                continue

            return [(cell[1], cell[2], UNCOVER_AS_SAFE) for cell in safe_cells]

    print('Deduction unsuccessful. Take your guess human.')
    #its up to the player. The algorithm wont take a random guess to lose the game ;)
    return []

os.mkdir('history')
os.rmdir
while True:
    im, window_region = get_active_window_im()
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
