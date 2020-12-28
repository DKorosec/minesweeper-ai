import os
import pyautogui as ag
from src.ai import next_clicks
from src.game_control import click_cell_in_game
from src.game_window_snapshot import get_active_window_im
from src.game_parser import process_ref_to_state
from src.debug_tools import debug_print_state
import shutil


# Switch to true if you want to memo the images of game. (Note it's slow.)
DEBUG_REWATCH = False
snapshot_dir = 'minesweeper_snapshots'
if DEBUG_REWATCH:
    if os.path.exists(snapshot_dir):
        shutil.rmtree(snapshot_dir)
    os.mkdir(snapshot_dir)

# uncomment for speed, but it can fuckup presses with OS not buffering enough.
#import pyautogui as ag
#ag.PAUSE = 0.1

it_cnt = 0
while True:
    im, window_region = get_active_window_im()

    # example of debugging state: for instance if debugger was open and 14.png was causing issue.
    #from PIL import Image
    #im = Image.open('minesweeper_snapshots/0.png') 

    if im is None:
        continue

    if DEBUG_REWATCH:
        im.save(os.path.join(snapshot_dir, str(it_cnt)+'.png'))
        it_cnt += 1

    game_state = process_ref_to_state(im)
    game_mat = game_state['game_2d_state']
    debug_print_state(game_mat)
    print('\n')
    clicks = next_clicks(game_mat)
    print(clicks)
    for click in clicks:
        cx, cy, left_click = click
        click_cell_in_game(window_region, game_state, cx, cy, left_click)

    ag.moveTo(1, 1)
