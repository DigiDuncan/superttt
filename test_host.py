from arcade import Window

from networking import host


def main():
    win = Window(fixed_rate=1 / 20.0)
    view, close = host()
    win.run(view)
    close.set()


if __name__ == "__main__":
    main()
