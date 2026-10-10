"""Field names as the format defines them, from headers as workbooks write them.

Older templates starred required fields (`b_pos*`) and some headers carry stray
spaces (`col_ id**`), which would otherwise leave a field unread without a word.
"""

from __future__ import annotations

import re

import polars as pl

from . import notices


def clean_header(name) -> str:
    """`col_ id**` as `col_id`."""
    text = str(name).strip().rstrip("*").strip()
    return re.sub(r"\s*_\s*", "_", text)


def clean_headers(df: pl.DataFrame, sheet: str) -> pl.DataFrame:
    renames: dict[str, str] = {}
    for name in df.columns:
        clean = clean_header(name)
        if clean == name:
            continue
        if clean in df.columns or clean in renames.values():
            notices.warning(
                "ambiguous-columns",
                f"`{name}` and `{clean}` name the same field; `{name}` was ignored",
                sheet=sheet,
                column=name,
            )
            continue
        renames[name] = clean
    return df.rename(renames)
