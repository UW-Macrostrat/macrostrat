# macrostrat.task-runner

Management tasks — `topo update` and its relatives — as **registered tasks with
typed parameters**, run on the Celery worker with their terminal output
streamed live and a cancel that behaves like Ctrl-C. Never a shell: a task is a
`TaskSpec` (name, title, pydantic `params`, dotted path of the `run` function)
registered through the `macrostrat.tasks` entry-point group, so the API can
serve the catalog and validate parameters without importing the code that runs
them.

Pieces, in `macrostrat/task_runner/`:

- `spec.py` — `TaskSpec` and `load_registry()`.
- `output.py` — `OutputStream`, a text sink that `XADD`s every flushed chunk,
  ANSI intact, to the run's Redis stream; `read_all` for archiving.
- `tail.py` — the async replay-then-tail the API's SSE route serves.
- `cancel.py` — `TaskCancelled`, `interruptible()` and `CancelWatcher`: a
  cancel published on the run's control channel interrupts the task's main
  thread and cancels its Postgres statements, as Ctrl-C does in a terminal.
- `ledger.py` — the `tasks.run` rows (`schema/_definitions/tasks`).
- `run.py` — `execute_run`, what the worker task calls.

The design and its rationale are in the workbench note *Management task runner*.
