from collections.abc import Iterable
from queue import Empty, Queue
from threading import Event as ThreadEvent
from threading import Thread
from typing import Self


def clear_queue[T](queue: Queue[T]) -> tuple[T, ...]:
    # ! WARNING IF THE QUEUE IS BEING ACTIVELY FILLED THIS WILL EITHER BLOCK OR BE INEFFECTIVE
    return tuple(QueueIter(queue))

class QueueIter[T](Iterable[T]):

    def __init__(self, queue: Queue[T]) -> None:
        self.q = queue

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> T:
        try:
            return self.q.get_nowait()
        except Empty:
            raise StopIteration

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
        # is_alive tracks the status of the actual thread
        return self._thread.is_alive()

    def has_started(self) -> bool:
        # has_started tracks whether the thread has started
        # i.e. you can't call thread.start() again.
        return self._has_started

    def start(self) -> bool:
        if self._has_started or self._thread.is_alive():
            # TODO: logging "This thread has been started and must be reset."
            return False
        self._has_started = True
        self._thread.start()
        return True

    def stop(self) -> bool:
        if not self._thread.is_alive():
            return False
        self._close_event.set()
        return True

    def reset(self) -> bool:
        if not self._has_started:
            return False

        if self._thread.is_alive():
            self._close_event.set()
            self._thread.join()

        self._has_started = False
        self._close_event.clear()
        name = self._thread.name
        self._thread = Thread(target=self._scope, name=name)
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
