# macrostrat.task-ledger

Macrostrat's record of management task runs (`macrostrat_meta.task_run`) and
`execute_run`, which the worker calls to run one. Running a task, streaming its
terminal output and cancelling it are `macrostrat.task_runner`, from
python-libraries; tasks register through its `TaskSpec` in the `macrostrat.tasks`
entry-point group.

- `ledger.py` — the `macrostrat_meta.task_run` rows (`schema/_definitions/macrostrat_meta`).
- `run.py` — `execute_run`: look up the run's task, execute it, record how it ended.

The design and its rationale are in the workbench note *Management task runner*.
