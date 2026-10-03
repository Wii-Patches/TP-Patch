#!/usr/bin/env python3
"""Regenerate tools/prebuilt/*.json from src/ (needs devkitPPC and the retail DOLs).

    TP_DOLS=<dir with RZDE01.0.dol RZDE01.2.dol RZDP01.0.dol RZDJ01.0.dol>  python3 tools/gen_prebuilt.py [pad ...]

Each retail DOL can instead be given as TP_DOL_<region key> (e.g. TP_DOL_RZDE01.2).  The JSON is what the
patcher ships and reads; end users do not need devkitPPC or any game files here.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
from dol import Dol
from features import PREBUILT, dump
from regions import REGIONS


def dol_for(region):
    env = os.environ.get('TP_DOL_' + region)
    if env:
        return Dol(env)
    base = os.environ.get('TP_DOLS')
    if base:
        p = os.path.join(base, region + '.dol')
        if os.path.exists(p):
            return Dol(p)
    sys.exit('set TP_DOLS=<dir with %s.dol> or TP_DOL_%s=<path>' % (region, region))


def main(argv):
    which = argv or ['pad']
    os.makedirs(PREBUILT, exist_ok=True)
    for name in which:
        mod = __import__('gen_' + name)
        mod.REF_DOL = dol_for('RZDE01.2')
        for region in REGIONS:
            f = mod.build(region, dol_for(region))
            path = os.path.join(PREBUILT, '%s_%s.json' % (name, region))
            with open(path, 'w') as fh:
                json.dump(dump(f), fh, indent=1)
                fh.write('\n')
            print('%-3s %s  %d ops -> %s' % (name, region, len(f.ops), os.path.relpath(path)))


if __name__ == '__main__':
    main(sys.argv[1:])
