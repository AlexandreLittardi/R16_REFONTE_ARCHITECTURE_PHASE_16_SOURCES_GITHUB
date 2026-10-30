#!/usr/bin/env python3
"""List duplicate method-name ownership along the actual application MRO.

Run from source checkout: python tools/report_mro.py > docs/MRO_OWNERSHIP.csv
This inventories names, not confirmed bugs/dead code. No Tk GUI is created.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import PVLayoutRibbonApp


def colliding_methods(app_class=PVLayoutRibbonApp):
    owners = defaultdict(list)
    for cls in app_class.__mro__:
        if cls is object:
            continue
        for name, func in vars(cls).items():
            if callable(func) and not (name.startswith('__') and name.endswith('__')):
                owners[name].append(cls.__name__)
    return {name: classes for name, classes in sorted(owners.items()) if len(classes) > 1}


def main():
    writer=csv.writer(sys.stdout)
    writer.writerow(('method','definition_count','active_implementation','remaining_mro_implementations'))
    for method, owners in colliding_methods().items():
        writer.writerow((method,len(owners),owners[0],' -> '.join(owners[1:])))


if __name__ == '__main__':
    main()
