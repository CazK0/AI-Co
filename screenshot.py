import mss
import mss.tools

class ScreenCapturer:
    def __init__(self, output_filename="screenshot.png"):
        self.output_filename = output_filename

    def capture(self):
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=self.output_filename)
            return self.output_filename