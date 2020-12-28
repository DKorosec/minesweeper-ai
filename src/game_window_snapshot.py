from PIL import ImageChops
import pygetwindow as gw
import time
import mss
import mss.tools
from PIL import Image

NO_RESULT = (None, None)


def get_active_window_im():
    aw = gw.getActiveWindow()

    if not aw or 'Google - Google Chrome' not in aw.title:
        return NO_RESULT

    pad = 8
    window_region = (aw.left+pad, aw.top + pad,
                     aw.width-pad*2, aw.height-pad*2)
    bbox = (aw.left+pad, aw.top+pad, aw.right-pad, aw.bottom-pad)

    with mss.mss() as sct:
        def take_screenshot():
            sct_img = sct.grab(bbox)
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

        def equal(im1, im2):
            return ImageChops.difference(im1, im2).getbbox() is None

        im1 = take_screenshot()
        time.sleep(0.2)
        im2 = take_screenshot()
        # prevent mid animation snapshot taking.
        if not equal(im1, im2):
            return NO_RESULT
    return im2, window_region
