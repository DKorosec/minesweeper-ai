import pyautogui as ag


def click_cell_in_game(window_region, game_state, x, y, left_click=True):
    wleft, wtop = window_region[:2]
    gleft, gtop = game_state['game_bbox'][:2]
    game_cell_dim = game_state['game_cell_width']
    center_w = game_cell_dim // 2
    click_fn = ag.leftClick if left_click else ag.rightClick

    px = wleft+gleft+x*game_cell_dim+center_w
    py = wtop+gtop+y*game_cell_dim+center_w
    click_fn(px, py)
