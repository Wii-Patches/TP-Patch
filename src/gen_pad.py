"""Build the controller feature (Classic Controller + GameCube pad) for one release.

The game's whole Wii-controller layer is one function (the per-frame pad update).  Four call
sites inside it are hooked:

  P  `bl WPADProbe`        report a Classic Controller / GameCube pad as a Nunchuk
  R  `bl KPADRead`         rewrite the returned samples into Wii Remote + Nunchuk form
  G1 `bl <remote gesture detector>`   add button-driven sword swings / spin attacks
  G2 `bl <nunchuk gesture detector>`  add button-driven shield bashes

The call sites are found by masked-signature search against the USA Rev 2 build; the callee
of every `bl` is decoded from the target DOL itself.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import asm
from layout import (FEED, GEST_BASE, GEST_END, PROBE_BASE, PROBE_END, READ_BASE, READ_END)
from ops import Feature, Hook
from sig import find_unique

# USA Rev 2 reference addresses (the others are found by signature search)
REF = {'P': 0x8000CCE0, 'R': 0x8000CDB4, 'G1': 0x8000CF60, 'G2': 0x8000D06C}
REF_SETBIT = 0x8000A5AC
REF_DOL = None

# ---- controls -----------------------------------------------------------------------
# Wii Remote / Nunchuk button bits as the game's KPAD reads them (remote held upright)
W_LEFT, W_RIGHT, W_DOWN, W_UP, W_PLUS = 0x0001, 0x0002, 0x0004, 0x0008, 0x0010
W_2, W_1, W_B, W_A, W_MINUS, W_Z, W_C, W_HOME = 0x0100, 0x0200, 0x0400, 0x0800, 0x1000, 0x2000, 0x4000, 0x8000
# spare bits used to ask hook G for a gesture (the game ignores them)
G_SWING, G_BASH, G_SPIN = 0x0020, 0x0040, 0x0080

CC_MAP = [  # Classic Controller hold bit -> Wii bit
    (0x0001, W_UP), (0x4000, W_DOWN), (0x0002, W_LEFT), (0x8000, W_RIGHT),
    (0x0010, W_A), (0x0040, W_B), (0x0008, W_1), (0x0020, W_2),
    (0x0400, W_PLUS), (0x1000, W_MINUS), (0x0800, W_HOME),
    (0x2000, W_Z),            # L   -> Z (target)
    (0x0080, W_C),            # ZL  -> C (camera)
    (0x0200, G_BASH),         # R   -> shield bash
    (0x0004, G_SWING),        # ZR  -> sword swing (hold: spin attack)
]
GC_MAP = [  # GameCube PAD button word -> Wii bit
    (0x0008, W_UP), (0x0004, W_DOWN), (0x0001, W_LEFT), (0x0002, W_RIGHT),
    (0x0100, W_A), (0x0200, W_B), (0x0400, W_1), (0x0800, W_2),
    (0x1000, W_PLUS),
    (0x0040, W_Z),            # L -> Z (target)
    (0x0020, G_BASH),         # R -> shield bash
    (0x0010, G_SWING),        # Z -> sword swing (hold: spin attack)
]
SPIN_FRAMES = 24


def _map_asm(table, src, dst, tmp, indent='    '):
    out = []
    for i, (s, d) in enumerate(table):
        out.append('%sandi.   %s, %s, 0x%04X' % (indent, tmp, src, s))
        out.append('%sbeq     1f' % indent)
        out.append('%sori     %s, %s, 0x%04X' % (indent, dst, dst, d))
        out.append('1:')
    return '\n'.join(out)


def _gc_chords():
    return '''
    andi.   r3, r5, 0x0060              # L+R together: C (camera); with Start: HOME
    cmpwi   r3, 0x0060
    bne     1f
    andi.   r6, r6, 0x%04X
    ori     r6, r6, 0x%04X
    andi.   r3, r5, 0x1000
    beq     1f
    andi.   r6, r6, 0x%04X
    ori     r6, r6, 0x%04X
1:
    andi.   r3, r5, 0x1010              # Z+Start: minus
    cmpwi   r3, 0x1010
    bne     1f
    andi.   r6, r6, 0x%04X
    ori     r6, r6, 0x%04X
1:''' % (0xFFFF & ~(W_Z | G_BASH), W_C, 0xFFFF & ~(W_C | W_PLUS), W_HOME,
         0xFFFF & ~(G_SWING | W_PLUS), W_MINUS)


def read_source():
    t = open(os.path.join(HERE, 'pad_read.s.in')).read()
    t = t.replace('@CC_MAP@', _map_asm(CC_MAP, 'r5', 'r6', 'r0'))
    t = t.replace('@GC_MAP@', _map_asm(GC_MAP, 'r5', 'r6', 'r0') + _gc_chords())
    return t


def gest_source(requests, gcnt=0x58):
    body = []
    for mask, bit, soff, cnt in requests:
        body += ['    andi.   r0, r31, 0x%04X' % mask, '    beq     1f',
                 '.if FEED', '    lis     r6, FEED@h', '    ori     r6, r6, FEED@l',
                 '    lwz     r7, 0x%X(r6)' % cnt, '    addi    r7, r7, 1', '    stw     r7, 0x%X(r6)' % cnt, '.endif',
                 '    addi    r3, r17, 0x%X' % soff,
                 '    li      r4, 0x%X' % bit,
                 '    li      r5, 1',
                 '    lis     r12, SETBIT@h', '    ori     r12, r12, SETBIT@l',
                 '    mtctr   r12', '    bctrl', '1:']
    t = open(os.path.join(HERE, 'pad_gest.s')).read().replace('GCNT', '0x%X' % gcnt)
    # the template's own mtctr/SETBIT lines are only documentation of the register use
    t = t.replace('    lis     r12, SETBIT@h\n    ori     r12, r12, SETBIT@l\n    mtctr   r12\n@REQUESTS@',
                  '\n'.join(body))
    return t


def _decode_bl(word, at):
    li = word & 0x03FFFFFC
    if li & 0x02000000:
        li -= 0x04000000
    return (at + li) & 0xFFFFFFFF


# gesture bits: detector bit meaning in the game (see docs/TECHNICAL.md)
BIT_SWING, BIT_SPIN, BIT_BASH = 0x01, 0x10, 0x01
S1_OFF, S2_OFF = 0x5E0, 0x11A4          # remote / nunchuk gesture state inside the channel struct


def build(region, dol, feed=False, padonly=True):
    ref = REF_DOL
    is_ref = region == 'RZDE01.2'
    sites = {k: (a if is_ref else find_unique(ref, dol, a, 8, 8)) for k, a in REF.items()}
    callee, orig = {}, {}
    for k, a in sites.items():
        w = struct.unpack('>I', dol.read(a, 4))[0]
        if (w >> 26) != 18 or not w & 1:
            raise SystemExit('%s: site %s 0x%08X is not a bl (0x%08X)' % (region, k, a, w))
        orig[k] = w
        callee[k] = _decode_bl(w, a)
    setbit = REF_SETBIT if is_ref else find_unique(ref, dol, REF_SETBIT, 0, 10)
    consts = {'FEED': FEED if feed else 0, 'PADONLY': 1 if padonly else 0, 'SPIN_FRAMES': SPIN_FRAMES}
    ops = []

    def add(site, base, end, source, syms, note):
        words = asm.words(asm.assemble(source, base, syms, consts)) + [0]
        if base + len(words) * 4 > end:
            raise SystemExit('%s: hook %s overflows its window (0x%X > 0x%X)' % (region, note, base + len(words) * 4, end))
        ops.append(Hook(site, orig_for[site], words, base, note=note))
        return base + len(words) * 4

    orig_for = {sites[k]: orig[k] for k in sites}
    add(sites['P'], PROBE_BASE, PROBE_END, open(os.path.join(HERE, 'pad_probe.s')).read(),
        {'PROBE': callee['P']}, 'WPADProbe call: Classic Controller / GameCube pad -> Nunchuk')
    cur = add(sites['G1'], GEST_BASE, GEST_END, gest_source([(G_SWING, BIT_SWING, S1_OFF, 0x40), (G_SPIN, BIT_SPIN, S1_OFF, 0x48)]),
              {'DETECT': callee['G1'], 'SETBIT': setbit}, 'remote gesture detector: sword swing / spin attack buttons')
    cur = (cur + 15) & ~15
    add(sites['G2'], cur, GEST_END, gest_source([(G_BASH, BIT_BASH, S2_OFF, 0x44)], 0x5C),
        {'DETECT': callee['G2'], 'SETBIT': setbit}, 'nunchuk gesture detector: shield bash button')
    add(sites['R'], READ_BASE, READ_END, read_source(),
        {'KPADREAD': callee['R']}, 'KPADRead call: controllers -> Wii Remote + Nunchuk samples')
    return Feature('pad', 'Classic Controller and GameCube controller', region, ops)
