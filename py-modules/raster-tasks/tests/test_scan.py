"""`rasters.scan`: registered where the catalog looks, and layer-less."""

import sys
import types
from dataclasses import dataclass

import pytest

from macrostrat.raster_tasks import TASKS, ScanParams, run_scan
from macrostrat.task_runner import load_registry


@dataclass
class FakeObject:
    href: str
    size: int = 1_000_000


class FakeIndex:
    calls: list = []

    def __init__(self, engine):
        pass

    def add_raster(self, href, layer=None, **kwargs):
        if "bad" in href:
            raise ValueError("unreadable")
        FakeIndex.calls.append((href, layer, kwargs))


class FakeDatabase:
    engine = object()


@pytest.fixture
def raster_index(monkeypatch):
    """Stands in for the library, which the base install does not carry."""
    module = types.ModuleType("macrostrat.raster_index")
    module.RasterIndex = FakeIndex
    module.found = []
    module.scan_prefix = lambda url: iter(module.found)
    monkeypatch.setitem(sys.modules, "macrostrat.raster_index", module)
    FakeIndex.calls = []
    return module


def test_registered_with_the_task_runner():
    assert load_registry()["rasters.scan"] is TASKS[0]


def test_scan_has_no_layer_parameter():
    assert "layer" not in ScanParams.model_json_schema()["properties"]


def test_registers_without_a_layer(raster_index):
    raster_index.found = [FakeObject("https://x/a.tif"), FakeObject("https://x/b.tif")]
    result = run_scan(FakeDatabase(), ScanParams(url="https://x/"), None)
    assert result == {"found": 2, "registered": 2, "failed": 0}
    assert [(href, layer) for href, layer, _ in FakeIndex.calls] == [
        ("https://x/a.tif", None),
        ("https://x/b.tif", None),
    ]


def test_dry_run_registers_nothing(raster_index):
    raster_index.found = [FakeObject("https://x/a.tif")]
    result = run_scan(FakeDatabase(), ScanParams(url="https://x/", dry_run=True), None)
    assert result["registered"] == 0
    assert FakeIndex.calls == []


def test_a_failure_does_not_stop_the_rest_but_fails_the_run(raster_index):
    raster_index.found = [
        FakeObject("https://x/bad.tif"),
        FakeObject("https://x/a.tif"),
    ]
    with pytest.raises(RuntimeError, match="1 of 2"):
        run_scan(FakeDatabase(), ScanParams(url="https://x/"), None)
    assert len(FakeIndex.calls) == 1
