#!/usr/bin/env python
# Script to move table defs to the new directory-based format.
import sys
from os import makedirs, listdir, path
from textwrap import dedent

here = path.dirname(__file__)
dirname = path.join(here,"cli/commands")
sys.path.append(dirname)

from table_meta import tables

for tablename, table in tables.items():
    if tablename.startswith('measure'):
        continue
    print(tablename)
    table_dir = path.join(dirname,'table_meta',tablename)
    try:
        makedirs(table_dir)
    except OSError:
        pass
    for i, proc in enumerate(('dump','create','insert','index','process')):
        procedure = table[proc]
        if procedure.strip() == "":
            continue
        procedure = dedent(procedure)+'\n'
        fn = path.join(table_dir, str(i)+"-"+proc+'.sql')
        with open(fn,'w') as f:
            f.write(procedure)

