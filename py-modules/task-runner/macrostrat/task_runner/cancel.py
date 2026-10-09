"""Cancelling a run the way Ctrl-C cancels a command.

In a terminal, Ctrl-C makes psycopg cancel the running statement and raises
`KeyboardInterrupt`, which unwinds through everything. Both halves are
reproduced here: `CancelWatcher` interrupts the task's main thread and cancels
its Postgres statements; `interruptible()` makes that interrupt raise
`TaskCancelled`, a `BaseException` no library `except Exception` swallows.
"""

import _thread
import signal
import threading
from contextlib import contextmanager
from typing import Callable

from sqlalchemy import create_engine, text

from .output import control_channel

CANCEL = b"cancel"


class TaskCancelled(BaseException):
    """The run was cancelled from outside, between or during statements."""


@contextmanager
def interruptible():
    """For the block, `_thread.interrupt_main()` raises `TaskCancelled` here.

    Must be entered from the main thread, where signal handlers live; under
    Celery that means the prefork or solo pool.
    """

    def handler(signum, frame):
        raise TaskCancelled()

    previous = signal.signal(signal.SIGINT, handler)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)


class CancelWatcher(threading.Thread):
    """Waits for `cancel` on the run's control channel, then interrupts the run.

    The interrupt is queued first, so it fires the moment the cancelled
    statement returns; `on_cancel` then cancels the statements themselves.
    """

    def __init__(self, redis, run_id: str, *, on_cancel: Callable[[], None]):
        super().__init__(name=f"cancel-watcher:{run_id}", daemon=True)
        self.redis = redis
        self.channel = control_channel(run_id)
        self.on_cancel = on_cancel
        self.cancelled = False
        self._stopping = threading.Event()

    def run(self):
        pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(self.channel)
        try:
            while not self._stopping.is_set():
                message = pubsub.get_message(timeout=0.5)
                if message is None or _bytes(message["data"]) != CANCEL:
                    continue
                if self._stopping.is_set():
                    return
                self.cancelled = True
                _thread.interrupt_main()
                self.on_cancel()
                return
        finally:
            pubsub.close()

    def stop(self):
        self._stopping.set()


def cancel_backends(db_url: str, application_name: str) -> int:
    """Cancel whatever the run's connections are executing, from a connection of our own.

    Every connection the run opens carries its `application_name`, so a second
    one the library opens is covered too.
    """
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT pg_cancel_backend(pid) FROM pg_stat_activity"
                    " WHERE application_name = :name AND state = 'active'"
                ),
                {"name": application_name},
            ).all()
        return len(rows)
    finally:
        engine.dispose()


def _bytes(value) -> bytes:
    if isinstance(value, str):
        return value.encode()
    return value
