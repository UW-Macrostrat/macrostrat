"""
Tests for Macrostrat's tileserver v2
"""
import pytest


def test_mapnik_available():
    import mapnik

    assert mapnik


# x: 1554 y: 3078 z: 13
# x: 194 y: 384 z: 10
# source id: 251
# large

# tile 0, 0, 1
# North america
