import mss
import mss.tools
from PIL import Image
import os

def capture_screen(output_filename="screenshot.png"):
    """Captures the primary monitor and saves it to a file."""
    try:
        with mss.mss() as sct:
            # Monitor 1 is typically the primary monitor
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=output_filename)
        return output_filename
    except Exception as e:
        print(f"Error capturing screen: {e}")
        return None

def get_image(filename="screenshot.png"):
    if os.path.exists(filename):
        return Image.open(filename)
    return None
