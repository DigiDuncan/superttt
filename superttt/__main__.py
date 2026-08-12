from arcade import load_font

from superttt.main import StartView
from .context import nav
from .window import Window
from .lib import logging

def main():
    # Setup logging
    logging.setup()

    # Load debug font
    load_font("resources/generic/gohu.ttf")

    win = Window(title="Multi-Layer Tic-Tac-Toe")
    nav.setup(StartView(), win)
    win.run()


if __name__ == "__main__":
    main()
