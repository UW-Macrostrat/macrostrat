"""
Tests for Macrostrat's tileserver v2
"""
import pytest


def test_mapnik_available():
    import mapnik
    assert mapnik
