from PIL import ImageChops
import pygetwindow as gw
import pyautogui as ag
import clipboard
import time


def get_active_window_im():
    aw = gw.getActiveWindow()
    if not aw:
        return None
    if 'Google - Google Chrome' not in aw.title:
        return None
    
    # focus url
    ag.hotkey('F6')
    # copy url
    ag.hotkey('ctrl', 'c')
    # get url from clipboard
    url = clipboard.paste()
    # check if in actual game.
    if 'fbx=minesweeper' not in url and 'search?q=minesweeper&oq=minesweeper' not in url:
        return None
    pad = 8

    def take_screenshot(): return ag.screenshot(region=(aw.left+pad, aw.top +
                                                        pad, aw.width-pad*2, aw.height-pad*2))

    def equal(im1, im2):
        return ImageChops.difference(im1, im2).getbbox() is None
    im1 = take_screenshot()
    time.sleep(0.1)
    im2 = take_screenshot()

    # prevent mid animation snapshot taking.
    if not equal(im1, im2):
        return None

    return im2
