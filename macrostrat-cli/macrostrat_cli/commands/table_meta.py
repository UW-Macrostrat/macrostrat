from collections import OrderedDict

tables = OrderedDict({})

from os import path, listdir

__here__ = path.dirname(__file__)
__table_meta__ = path.join(__here__, "table_meta")

# Walk a directory tree and assemble a listing of SQL files
# Note: this is inefficient and should eventually be replaced with
# a function supporting the on-demand loading of SQL
for dirname in listdir(__table_meta__):
    __dirpath__ = path.join(__table_meta__, dirname)
    if not path.isdir(__dirpath__):
        continue
    table_name = dirname
    if table_name not in tables:
        tables[table_name] = OrderedDict({"process": ""})
    for fn in listdir(__dirpath__):
        (base, ext) = path.splitext(fn)
        # ix is a prefix that shows ordering,
        (ix, operation) = base.split("-")
        # Only accept SQL files (this way we can keep notes, etc.)
        if ext != ".sql":
            continue
        fp = path.join(__dirpath__, fn)
        with open(fp, "r") as f:
            sqltext = f.read()
        tables[table_name][operation] = sqltext
