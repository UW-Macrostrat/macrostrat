import _thread
import threading
import time

import pytest

from macrostrat.task_runner.cancel import CancelWatcher, TaskCancelled, interruptible


def test_interrupt_main_raises_task_cancelled_in_the_block():
    with pytest.raises(TaskCancelled):
        with interruptible():
            threading.Timer(0.05, _thread.interrupt_main).start()
            for _ in range(200):
                time.sleep(0.01)


def test_task_cancelled_escapes_except_exception():
    with pytest.raises(TaskCancelled):
        try:
            raise TaskCancelled()
        except Exception:
            pytest.fail("a cancel must not be caught as an ordinary error")


class FakePubSub:
    def __init__(self, messages):
        self.messages = list(messages)
        self.closed = False

    def subscribe(self, channel):
        self.channel = channel

    def get_message(self, timeout=None):
        if self.messages:
            return {"type": "message", "data": self.messages.pop(0)}
        time.sleep(timeout or 0)
        return None

    def close(self):
        self.closed = True


class FakeRedis:
    def __init__(self, messages):
        self.pubsub_instance = FakePubSub(messages)

    def pubsub(self, ignore_subscribe_messages=False):
        return self.pubsub_instance


def test_watcher_interrupts_then_cancels_backends(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "macrostrat.task_runner.cancel._thread.interrupt_main",
        lambda: calls.append("interrupt"),
    )
    redis = FakeRedis([b"noise", b"cancel"])
    watcher = CancelWatcher(redis, "r1", on_cancel=lambda: calls.append("cancel"))
    watcher.start()
    watcher.join(timeout=2)
    assert calls == ["interrupt", "cancel"]
    assert watcher.cancelled
    assert redis.pubsub_instance.channel == "task-run:r1:ctl"
    assert redis.pubsub_instance.closed


def test_watcher_ignores_a_cancel_after_stop():
    redis = FakeRedis([])
    calls = []
    watcher = CancelWatcher(redis, "r1", on_cancel=lambda: calls.append("cancel"))
    watcher.start()
    watcher.stop()
    redis.pubsub_instance.messages.append(b"cancel")
    watcher.join(timeout=2)
    assert calls == [] and not watcher.cancelled
