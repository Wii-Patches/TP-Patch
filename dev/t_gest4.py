import struct, sys, time
from session import *
s = Session(sys.argv[1], gc_pad=False)
try:
    s.run(40)
    base = 0x80433168
    def show(i):
        d = s.peek(base, 0x90); f = s.peek(FEED+0x40, 0x20)
        w = lambda o: struct.unpack('>I', d[o:o+4])[0]
        c = struct.unpack('>8I', f)
        print(i, 'cnt', w(0), 'hold %04x trig %04x state %08x' % (w(4), w(8), w(0x80)), 'swing/bash/spin %d %d %d  Rtrig %d Rcalls %d G1calls %d G2calls %d' % (c[0],c[1],c[2],c[4],c[5],c[6],c[7]))
    show('idle')
    s.feed_gc(buttons=0x10)
    for i in range(8):
        time.sleep(0.1); show(i)
finally:
    s.close()
