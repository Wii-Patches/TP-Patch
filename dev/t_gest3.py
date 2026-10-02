import struct, sys, time
from session import *
s = Session(sys.argv[1], gc_pad=False)
try:
    s.run(40)
    def cnt(tag):
        d = s.peek(FEED + 0x40, 12)
        print(tag, 'swing/bash/spin requests', struct.unpack('>III', d))
    cnt('idle')
    s.feed_gc(buttons=0x10); s.run(0.4); cnt('Z pressed 0.4s')
    s.run(1.2); cnt('Z held 1.6s')
    s.feed_gc(buttons=0); s.run(0.3)
    s.feed_gc(buttons=0x20); s.run(0.4); cnt('R pressed')
    s.feed_cc(hold=0x0004); s.run(0.4); cnt('CC ZR')
    s.feed_cc(hold=0x0200); s.run(0.3); cnt('CC R')
finally:
    s.close()
