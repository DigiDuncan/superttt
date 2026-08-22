from arcade import load_font

from superttt.multiplayer import multiplayer
from superttt.views import StartView

from .context import nav
from .lib import logging
from .window import Window


def main():
    try:
        # Setup logging
        logging.setup()

        # Load debug font
        fonts = ["gohu.ttf", "Static Bold Italic.otf", "Static Bold.otf", "Static Italic.otf", "Static.otf"]
        for font in fonts:
            load_font(f"resources/superttt/{font}")

        win = Window(title="Multi-Layer Tic-Tac-Toe")
        nav.setup(StartView(), win)
        win.run()
    finally:
        multiplayer.disconnect() # Make sure the multiplayer threads actually close


if __name__ == "__main__":
    main()
