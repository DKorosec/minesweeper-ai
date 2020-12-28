import numpy as np

NOT_INTERESETED_PX = (255, 255, 255)
ZERO_COLOR1 = (229, 194, 159)  # light brown
ZERO_COLOR2 = (215, 184, 153)  # dark brown
ONE_COLOR = (25, 118, 210)
TWO_COLOR = (56, 142, 60)
THREE_COLOR = (211, 47, 47)
FOUR_COLOR = (123, 31, 162)
FIVE_COLOR = (255, 143, 0)
SIX_COLOR = (0, 151, 167)
FLAG_COLOR = (242, 54, 7)
UNCHECKED_COLOR1 = (170, 215, 81)  # light green
UNCHECKED_COLOR2 = (162, 209, 73)  # dark green
NUMBERS = [ONE_COLOR, TWO_COLOR, THREE_COLOR, FOUR_COLOR, FIVE_COLOR, SIX_COLOR]
UNCHECKED_COLORS = [UNCHECKED_COLOR1, UNCHECKED_COLOR2]
ZERO_COLORS = [ZERO_COLOR1, ZERO_COLOR2]
BG_TILE_COLORS = [UNCHECKED_COLOR1, UNCHECKED_COLOR2, ZERO_COLOR1, ZERO_COLOR2]


def process_ref_to_state(im):
    im = im.copy()
    border_im = im.copy()
    game_top = None
    game_bottom = None
    game_right = None
    game_left = None

    # Filter out colors that are not in the game tiles.
    # Basically keep only tiles. GREENISH / BROWNISH
    for y in range(border_im.height):
        for x in range(border_im.width):
            if border_im.getpixel((x, y)) not in BG_TILE_COLORS:
                border_im.putpixel((x, y), NOT_INTERESETED_PX)
            else:
                if game_left is None:
                    game_left = x

                if game_top is None:
                    game_top = y
                else:
                    game_bottom = y
                    game_right = x

    border_im.save('test.png')
    ppx = None
    borders_x = []
    # FIND all borders based on first pixel row.
    # Idea if previous pixel != current pixel -> border!
    # BUT: pixel can be filtered (not interested) in those cases skip. Because we dont count those as any values or 'borders'
    for x in range(game_left, game_right-1):
        cpx = border_im.getpixel((x, game_top))
        if cpx == NOT_INTERESETED_PX:
            continue
        if ppx is not None and ppx != cpx:
            borders_x.append(x)
        ppx = cpx

    # when we have all borders, diff them (length of cell) and take the median because of errors (pixel offsets / antialiasing etc...)
    # take the most common one basically
    cell_width = int(np.median([borders_x[i]-borders_x[i-1]
                                for i in range(1, len(borders_x))]))

    game_width = game_right - game_left
    game_height = game_bottom - game_top

    matrix_width = round(game_width / cell_width)
    matrix_height = round(game_height / cell_width)

    # when we scanned the gaming grid, crop the image so we only have the pixels of the game.
    # it will be easier to manipulate without offsets.
    game_bbox = (game_left, game_top, game_right, game_bottom)
    game_im = im.crop(game_bbox)

    def most_common_in_list(l: list):
        return max(set(l), key=l.count)

    # given center pixel of a game cell check retangular area of third of its width and
    # analyze the most common appearing pixel color
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
            return 0

        most_common_px = most_common_in_list(state_pxs)
        if most_common_px == FLAG_COLOR:
            return '!'

        if most_common_px in NUMBERS:
            return NUMBERS.index(most_common_px) + 1

        raise Exception('unhandled px color / symbol state')

    """
    # DEBUG GAME
    for y in range(game_im.height):
        for x in range(game_im.width):
            px = game_im.getpixel((x, y))
            if px not in [*NUMBERS, FLAG_COLOR, *BG_TILE_COLORS]:
                game_im.putpixel((x, y), (255, 255, 255))
    game_im.save('game.png')
    """

    game_state = []
    for y in range(matrix_height):
        row = []
        for x in range(matrix_width):
            ix = x * cell_width + cell_width // 2
            iy = y * cell_width + cell_width // 2
            cell_state = get_im_area_cell_state(game_im, ix, iy)
            row.append(cell_state)
        game_state.append(row)

    return {
        'game_2d_state': game_state,
        'game_bbox': game_bbox,
        'game_cell_width': cell_width
    }
