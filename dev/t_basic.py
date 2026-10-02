import struct, sys, time
from session import *
disc = sys.argv[1]
s = Session(disc, gc_pad=False)
try:
    s.run(40)
    base = 0x80433168
    def show(tag):
        d = s.peek(base, 0x1e08)
        cnt = struct.unpack('>I', d[0:4])[0]
        st = d[4:4+0x88]
        w = lambda o: struct.unpack('>I', st[o:o+4])[0]
        fl = lambda o: struct.unpack('>f', st[o:o+4])[0]
        print(tag, 'cnt', cnt, 'hold %04x trig %04x rel %04x' % (w(0), w(4), w(8)), 'type', w(0x5c),
              'stick %.2f %.2f' % (fl(0x60), fl(0x64)), 'pos %.2f %.2f' % (fl(0x20), fl(0x24)), 'ir', st[0x84], 'state %08x' % w(0x7c))
    show('idle')
    s.feed_gc(buttons=0x100)           # A
    s.run(1); show('GC A')
    s.feed_gc(buttons=0x100|0x010, sx=250, sy=128, cx=250, cy=128)   # A + Z, stick right, cstick right
    s.run(1.0); show('GC A+Z stick right')
    s.feed_gc(buttons=0x40|0x20)  # L+R chord
    s.run(1); show('GC L+R')
    s.feed_off(); s.run(1); show('off')
    s.feed_cc(hold=0x0010|0x2000, lx=0.5, ly=-0.25, rx=1.0, ry=0.0)
    s.run(1); show('CC A+L stick')
    s.feed_off()
finally:
    s.close()
