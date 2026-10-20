from dataclasses import dataclass
from typing import TextIO


@dataclass
class RunContext:
    """What a task may ask of its run.

    Output written to `stdout` while the task runs reaches the stream already;
    `write` is for a task that wants to address the stream explicitly.
    """

    run_id: str
    output: TextIO

    def write(self, text: str) -> None:
        self.output.write(text)
        self.output.flush()
