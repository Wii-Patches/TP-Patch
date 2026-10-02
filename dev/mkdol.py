#!/usr/bin/env python3
"""Dev helper: build a patched main.dol straight from src/ (needs devkitPPC).

    dev/mkdol.py <region key> <in.dol> <out.dol> [--feed]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
from dol import Dol
from ops import apply_static
import gen_pad

REFDOL = os.environ.get('TP_REF_DOL', os.path.join(HERE, '..', 'work', 'dols', 'RZDE01_v02.dol'))


def main(region, src, dst, feed=False, padonly=True):
    gen_pad.REF_DOL = Dol(REFDOL)
    d = Dol(src)
    f = gen_pad.build(region, d, feed=feed, padonly=padonly)
    apply_static(d, [f])
    d.save(dst)
    print('patched', region, '->', dst, '(feed)' if feed else '')


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    main(a[0], a[1], a[2], feed='--feed' in sys.argv, padonly='--nopadonly' not in sys.argv)
