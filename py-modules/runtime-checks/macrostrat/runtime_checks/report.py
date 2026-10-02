"""Render results: a Rich list, JSON, or a JUnit XML file."""

import json
from dataclasses import asdict
from pathlib import Path
from xml.etree import ElementTree as ET

from rich.console import Console

from .model import Result

_MARKS = {"ok": "[green]✓[/]", "warn": "[yellow]![/]", "fail": "[red]✗[/]"}

_TITLES = {"local": "Local setup"}


def summary(results: list[Result]) -> str:
    failed = sum(r.status == "fail" for r in results)
    warned = sum(r.status == "warn" for r in results)
    return f"{failed} failed, {warned} warnings, {len(results)} checks"


def print_results(console: Console, results: list[Result]):
    for service, group in _grouped(results):
        console.print(f"[bold]{_TITLES.get(service, service)}[/]")
        for r in group:
            console.print(f"  {_MARKS[r.status]} {r.name} [dim]{r.detail}[/]")
    console.print(f"\n{summary(results)}")


def to_json(results: list[Result]) -> str:
    return json.dumps([asdict(r) for r in results], indent=2)


def write_junit(results: list[Result], path: Path):
    suites = ET.Element("testsuites", name="macrostrat check")
    for service, group in _grouped(results):
        suite = ET.SubElement(
            suites,
            "testsuite",
            name=service or "",
            tests=str(len(group)),
            failures=str(sum(r.status == "fail" for r in group)),
        )
        for r in group:
            case = ET.SubElement(
                suite,
                "testcase",
                name=r.name,
                classname=service or "",
                time=str(r.elapsed or 0),
            )
            if r.status == "fail":
                ET.SubElement(case, "failure", message=r.detail)
            # JUnit has no warning state, so a warning passes with its detail.
            if r.status == "warn":
                ET.SubElement(case, "system-out").text = f"warning: {r.detail}"
    ET.indent(suites)
    ET.ElementTree(suites).write(path, encoding="unicode", xml_declaration=True)


def _grouped(results: list[Result]):
    """Results by service, in order of first appearance."""
    groups: dict = {}
    for r in results:
        groups.setdefault(r.service, []).append(r)
    return groups.items()
