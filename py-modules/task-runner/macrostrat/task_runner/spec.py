from dataclasses import dataclass
from importlib import import_module
from importlib.metadata import entry_points
from typing import Callable

from pydantic import BaseModel

# Packages register their tasks here, as CLI subsystems do in `macrostrat.subsystems`.
ENTRY_POINT_GROUP = "macrostrat.tasks"


@dataclass(frozen=True)
class TaskSpec:
    """A task the runner may be asked to run.

    `run` is the dotted path (`package.module:function`) of a callable
    `(db, params, ctx) -> result`, imported only when the task executes, so a
    process holding the catalog need not carry the task's dependencies.
    """

    name: str
    title: str
    description: str
    params: type[BaseModel]
    run: str

    def schema(self) -> dict:
        return self.params.model_json_schema()

    def parse(self, data: dict) -> BaseModel:
        return self.params.model_validate(data)

    def resolve(self) -> Callable:
        module, _, attr = self.run.partition(":")
        return getattr(import_module(module), attr)


def load_registry() -> dict[str, TaskSpec]:
    """Every registered task, by name."""
    registry: dict[str, TaskSpec] = {}
    for entry in entry_points(group=ENTRY_POINT_GROUP):
        for spec in entry.load():
            if spec.name in registry:
                raise ValueError(f"Task {spec.name!r} is registered twice")
            registry[spec.name] = spec
    return registry
