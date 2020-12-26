from skimage import filters
from PIL import Image
import matplotlib.pyplot as plt
from numpy.core.shape_base import block
import pygetwindow as gw
import pyautogui as ag
import numpy as np
import math
import time
import os


def process_active_window():
    ag.screenshot()
    aw = gw.getActiveWindow()
    if not aw:
        return
    pad = 8
    ag.screenshot('ref.png', region=(aw.left+pad, aw.top +
                                     pad, aw.width-pad*2, aw.height-pad*2))


ZERO_COLOR1 = (229, 194, 159)  # light brown
ZERO_COLOR2 = (215, 184, 153)  # dark brown
ONE_COLOR = (25, 118, 210)
TWO_COLOR = (56, 142, 60)
THREE_COLOR = (211, 47, 47)
FOUR_COLOR = (123, 31, 162)
FIVE_COLOR = (255, 143, 0)
FLAG_COLOR = (242, 54, 7)
UNCHECKED_COLOR1 = (170, 215, 81)  # light green
UNCHECKED_COLOR2 = (162, 209, 73)  # dark green

# should always follow: number = index+1
# numbers[2] = number 3
NUMBERS = [ONE_COLOR,
           TWO_COLOR, THREE_COLOR, FOUR_COLOR, FIVE_COLOR]
UNCHECKED_COLORS = [UNCHECKED_COLOR1, UNCHECKED_COLOR2]
ZERO_COLORS = [ZERO_COLOR1, ZERO_COLOR2]
BG_TILE_COLORS = [
    UNCHECKED_COLOR1,
    UNCHECKED_COLOR2,
    ZERO_COLOR1,
    ZERO_COLOR2
]


def process_ref_to_state(ref_img_path):
    im = Image.open(ref_img_path)
    border_im = im.copy()
    game_top = None
    game_bottom = None
    game_right = None
    game_left = 0

    NOT_INTERESETED_PX = (255, 255, 255)
    # GET TOP_LEFT_XY START OF GAME AND DELETE PIXELS THAT ARE NOT POI.
    for y in range(border_im.height):
        for x in range(border_im.width):
            if border_im.getpixel((x, y)) not in BG_TILE_COLORS:
                border_im.putpixel((x, y), NOT_INTERESETED_PX)
            elif game_top is None:
                game_top = y
            else:
                game_bottom = y
                game_right = x
    #border_im.save('border_ref.png')
    # SCAN ROW AND GET MEDIAN CELL DIMENSION.
    ppx = None
    borders_x = []
    for x in range(game_left, game_right-1):
        cpx = border_im.getpixel((x, game_top))
        if cpx == NOT_INTERESETED_PX:
            continue
        if ppx is not None and ppx != cpx:
            borders_x.append(x)
        ppx = cpx
    cell_width = int(np.median([borders_x[i]-borders_x[i-1]
                                for i in range(1, len(borders_x))]))

    print('I ASSERT THE BORDER DIMENSION IS', cell_width, 'PIXELS!')

    game_width = game_right - game_left
    game_height = game_bottom - game_top

    matrix_width = round(game_width / cell_width)
    matrix_height = round(game_height / cell_width)

    print(matrix_width, 'x', matrix_height)
    game_im = im.crop((game_left, game_top, game_right, game_bottom))

    def most_common_in_list(l: list):
        return max(set(l), key=l.count)

    def get_im_area_cell_state(game_im, cx, cy):
        dw = cell_width // 3
        requires_user_input = True
        SYMBOL_PXS = [*NUMBERS, FLAG_COLOR]
        state_pxs = []
        for y in range(-dw, dw):
            for x in range(-dw, dw):
                ix = x + cx
                iy = y + cy
                px = game_im.getpixel((ix, iy))
                if px in ZERO_COLORS:
                    requires_user_input = False
                elif px in SYMBOL_PXS:
                    requires_user_input = False
                    state_pxs.append(px)

        if requires_user_input:
            return '?'

        if len(state_pxs) == 0:
            return '0'

        most_common_px = most_common_in_list(state_pxs)
        if most_common_px == FLAG_COLOR:
            return '!'

        if most_common_px in NUMBERS:
            return NUMBERS.index(most_common_px) + 1

        raise Exception('unhandled px color / symbol state')

    for y in range(matrix_height):
        row = ''
        for x in range(matrix_width):
            ix = x * cell_width + cell_width // 2
            iy = y * cell_width + cell_width // 2
            row += str(get_im_area_cell_state(game_im, ix, iy))
        print(row)

    for y in range(game_im.height):
        for x in range(game_im.width):
            px = game_im.getpixel((x, y))
            if px not in [*NUMBERS, FLAG_COLOR, *BG_TILE_COLORS]:
                game_im.putpixel((x, y), (255, 255, 255))

    game_im.save('game.png')

while True:
    #process_active_window()
    process_ref_to_state(ref_img_path='gold_ref.png')
    time.sleep(1)
