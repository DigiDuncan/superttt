from threading import Event as ThreadEvent
from threading import Thread


class ThreadScope:
    """
    A Simple class which provides a simple threaded loop that can be closed using the
    passed in close_event. The methods _enter, _run, and _exit are to be overwritten in subclasses.
    It is unsafe to call any of the public ThreadScope methods from within the thread.
    """

    def __init__(self, close_event: ThreadEvent, name: str | None = None) -> None:
        name = self.__class__.__name__ if name is None else name
        self._thread: Thread = Thread(target=self._scope, name=name)
        self._close_event: ThreadEvent = close_event
        self._has_started: bool = False

    def join(self, timeout: float | None = None):
        return self._thread.join(timeout)

    def is_alive(self) -> bool:
        return self._thread.is_alive()

    def has_started(self) -> bool:
        return self._has_started

    def start(self) -> bool:
        if self._thread.is_alive() or self._has_started:
            # TODO: logging "This thread is currently alive and cannot be started again."
            # TODO: logging "Cannot restart a thread. The close event has been set."
            return False
        self._has_started = True
        self._thread.start()
        return True

    def stop(self) -> bool:
        if not self._thread.is_alive():
            return False
        self._close_event.set()
        return True

    def watch(self):
        try:
            while self._thread.is_alive():
                self._thread.join(0.1)
        except KeyboardInterrupt:
            # TODO: logging f"Received KeyboardInterrupt. Closing thread `{self._thread.name}`."
            pass
        finally:
            self._close_event.set()

    def _scope(self):
        self._enter()
        while not self._close_event.is_set():
            self._run()
        self._exit()

    def _enter(self):
        pass

    def _run(self):
        pass

    def _exit(self):
        pass
