from game_window_snapshot import get_active_window_im
from game_parser import process_ref_to_state
from debug_tools import debug_print_state
from PIL import Image


import time

while True:
    #im = get_active_window_im()
    im = Image.open('gold_ref.png')
    if im is None:
        time.sleep(0.1)
        continue
    state = process_ref_to_state(im)
    debug_print_state(state)
    print('\n')
    time.sleep(2)
