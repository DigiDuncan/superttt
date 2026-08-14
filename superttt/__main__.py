from arcade import load_font

from superttt.views import StartView
from .context import nav
from .window import Window
from .lib import logging

def main():
    # Setup logging
    logging.setup()

    # Load debug font
    fonts = ["gohu.ttf", "Static Bold Italic.otf", "Static Bold.otf", "Static Italic.otf", "Static.otf"]
    for font in fonts:
        load_font(f"resources/superttt/{font}")

    win = Window(title="Multi-Layer Tic-Tac-Toe")
    nav.setup(StartView(), win)
    win.run()


if __name__ == "__main__":
    main()
