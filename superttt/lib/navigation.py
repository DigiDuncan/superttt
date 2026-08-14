from arcade import View, Window, get_window

# TODO pop_until(t: Type[View])

class NavigationStack:
    def __init__(self) -> None:
        self._stack: list[View]
        self._window: Window

    def setup(self, root: View, window: Window | None = None):
        self._stack = [root]
        self._window = window if window is not None else get_window()
        self._window.show_view(root)

    @property
    def is_empty(self) -> bool:
        return not self._stack

    def push(self, view: View):
        self._stack.append(view)
        self._window.show_view(view)

    def pop(self, n: int = 1) -> View:
        for _ in range(n):
            view = self._stack.pop()
        self._window.show_view(self.peek())
        return view

    def peek(self) -> View:
        if self.is_empty:
            raise ValueError("The navigation stack has run out of views.")
        return self._stack[-1]

    def previous(self) -> View | None:
        if len(self._stack) <= 1:
            return None
        return self._stack[-2]

    def swap(self, view: View) -> None:
        if self.is_empty:  # Should never happen
            self.push(view)
            return
        self._stack[-1] = view
        self._window.show_view(view)

    def pop_to_start(self) -> None:
        while len(self._stack) > 1:
            self.pop()
