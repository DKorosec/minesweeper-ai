from src.utils import dim2d
from src.game_window_snapshot import get_active_window_im
from src.game_parser import process_ref_to_state
from src.debug_tools import debug_print_state
from PIL import Image
import itertools
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


def list_intersection(l1, l2):
    return list(set(l1).intersection(set(l2)))


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

    print('cannot solve simply, deduction required. expect some computational time for next step.')
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

    # start solving with cells that already have most neighbors solved.
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
        for nv, nx, ny in get_condition_neighbors(game_mat, cx, cy, lambda cell: isinstance(cell, int) and cell > 0):
            flag_cnt = get_condition_neighbors_cnt(
                game_mat, nx, ny, lambda cell: cell == '!')
            if flag_cnt > nv:
                return False
        return True

    def deduct_cell_solution(cx, cy):
        if cx == 13 and cy == 2:
            dbg = True
        traverse_memo[(cx, cy)] = True
        recursion_lock[(cx, cy)] = True

        cell_value = game_mat[cy][cx]
        free_cells = get_condition_neighbors(
            game_mat, cx, cy, lambda cell: cell == '?')
        solved_cells = get_condition_neighbors(
            game_mat, cx, cy, lambda cell: cell == '!')
        must_guess_cells_cnt = cell_value - len(solved_cells)

        assert len(free_cells) >= must_guess_cells_cnt
        solutions = []
        # if must_guess_cells_cnt == 0 then no new bombs will be asserted.
        for picked_cells in itertools.combinations(free_cells, must_guess_cells_cnt):
            assert_bombs(picked_cells)
            neighbors_ok = all([neighbors_still_ok(px, py)
                                for _, px, py in picked_cells])

            if not neighbors_ok:
                revert_assert_bombs(picked_cells)
                continue
            # TODO only | or - neighbors, ignore diagonal? cx == nx or cy == ny <- But it doesnt matter because must_check_neighbor will skip
            bomb_indicator_neighbors = [
                n for n in get_condition_neighbors(game_mat, cx, cy, lambda cell: isinstance(cell, int) and cell > 0)
                if (n[1], n[2]) not in recursion_lock
            ]

            neighbors_solved = True
            neighbors_solutions = []
            for _, nx, ny in bomb_indicator_neighbors:
                revert_assert_bombs(picked_cells)
                # revert bombs so neighbor actually gets common cells
                neighbor_free_cells = get_condition_neighbors(
                    game_mat, nx, ny, lambda cell: cell == '?')
                assert_bombs(picked_cells)
                must_check_neighbor = len(list_intersection(
                    free_cells, neighbor_free_cells)) > 0
                if not must_check_neighbor:
                    continue

                solved = deduct_cell_solution(nx, ny)
                if solved is None:
                    neighbors_solved = False
                    break
                neighbors_solutions.extend(solved)

            revert_assert_bombs(picked_cells)

            if neighbors_solved:
                neighbors_solutions.extend(picked_cells)
                solutions.append(distinct(neighbors_solutions))
            # too many solutions.
            # TODO: what if we get many solutions. and in that case we do check where the bombs are not located and that means there are no bombs? OR what if we return all possible solutions and then SUBSTRACT THAT solution mines from all fields and we get non bomb ones?
            if len(solutions) > 1:
                break

        only_one_solution = len(solutions) == 1
        if not only_one_solution:
            del recursion_lock[(cx, cy)]
            return None

        del recursion_lock[(cx, cy)]
        return solutions[0]

    for ucell in unsolved_cells:
        cx, cy, neighbor_cnt = ucell
        if traversed(cx, cy):
            # this cell was already used in deduction from previous cells. If solution was found we wouldn't come here (we exit on success solution)
            # therefore this cell yields no solution.
            continue
        solution = deduct_cell_solution(cx, cy)
        if solution is not None:
            return [(cell[1], cell[2], FLAG_AS_BOMB) for cell in solution]

    print('Deduction unsuccessful. Take your guess human.')
    return []


while True:
    im, window_region = get_active_window_im()
    
    #im = Image.open('deduction_error.png')
    if im is None:
        continue

    #im.save('deduction_error.png')
    #exit(0)

    game_state = process_ref_to_state(im)
    game_mat = game_state['game_2d_state']
    debug_print_state(game_mat)
    print('\n')
    clicks = next_clicks(game_mat)
    print(clicks)
    for click in clicks:
        cx, cy, left_click = click
        click_cell_in_game(window_region, game_state, cx, cy, left_click)
        ag.moveTo(1,1)
        #time.sleep(0.05)
