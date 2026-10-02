"""Dev/test harness: run a (patched) disc in Dolphin with the GDB stub and a scripted input feed.

Uses a private Dolphin user dir so it never touches the real one.  Only for development; none
of this ships.
"""
import os
import struct
import subprocess
import time

from gdbc import Gdb

DOLPHIN = '/Applications/Dolphin.app/Contents/MacOS/Dolphin'
WORK = os.environ.get('TP_WORK', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'work'))
USER = os.environ.get('TP_DOLPHIN_USER', os.path.join(WORK, 'dolphin-user'))
PORT = 23159
FEED = 0x80002F00


def f32(x):
    return struct.unpack('>I', struct.pack('>f', x))[0]


def pad_words(buttons=0, sx=128, sy=128, cx=128, cy=128, l=0, r=0):
    """SI answer words (INBUFH, INBUFL) for a GameCube pad.  `buttons` is the PAD button word
    (A 0x100 B 0x200 X 0x400 Y 0x800 Start 0x1000 L 0x40 R 0x20 Z 0x10 Up 8 Down 4 Right 2 Left 1)."""
    h = 0x00800000 | ((buttons & 0x3FFF) << 16) & 0x3FFF0000 | (sx << 8) | sy
    h = (h & ~0x00800000) | 0x00800000
    lo = (cx << 24) | (cy << 16) | (l << 8) | r
    return h, lo


class Session:
    def __init__(self, disc, video='Null', wiimote_ext='Nunchuk', gc_pad=False, speed=0, breakpoints=()):
        self.disc = disc
        os.makedirs(USER + '/Config', exist_ok=True)
        with open(USER + '/Config/WiimoteNew.ini', 'w') as f:
            f.write('[Wiimote1]\nSource = 1\nExtension = %s\n' % wiimote_ext if wiimote_ext else
                    '[Wiimote1]\nSource = 0\n')
        ini = open(USER + '/Config/Dolphin.ini').read().splitlines()
        out, sec = [], None
        for l in ini:
            if l.startswith('['):
                sec = l
            if sec == '[Core]' and (l.startswith('SIDevice0') or l.startswith('EmulationSpeed') or l.startswith('EnableDebugging')):
                continue
            out.append(l)
            if l == '[Core]':
                out.append('SIDevice0 = %d' % (6 if gc_pad else 0))
                out.append('EnableDebugging = %s' % ('True' if breakpoints else 'False'))
                out.append('EmulationSpeed = %s' % ('0' if speed == 0 else speed))
        open(USER + '/Config/Dolphin.ini', 'w').write('\n'.join(out) + '\n')
        self.log = open(os.path.join(WORK, 'dolphin.log'), 'w')
        self.proc = subprocess.Popen([DOLPHIN, '-u', USER, '-b', '-v', video, '-e', disc],
                                     stdout=self.log, stderr=self.log)
        self.g = Gdb(PORT)
        self.g.s.settimeout(30)
        for b in breakpoints:
            self.g.bp_set(b)
        self.g.cont()

    # ---- running state
    def pause(self):
        self.g.stop()

    def go(self):
        self.g.cont()

    def run(self, seconds):
        time.sleep(seconds)

    # ---- memory (pauses briefly)
    def peek(self, addr, n):
        self.g.stop()
        try:
            return self.g.read(addr, n)
        finally:
            self.g.cont()

    def u32(self, addr):
        return struct.unpack('>I', self.peek(addr, 4))[0]

    def poke(self, addr, data):
        self.g.stop()
        try:
            self.g.write(addr, data)
        finally:
            self.g.cont()

    # ---- feed
    def feed_gc(self, buttons=0, sx=128, sy=128, cx=128, cy=128, l=0, r=0):
        h, lo = pad_words(buttons, sx, sy, cx, cy, l, r)
        self.poke(FEED, struct.pack('>III', 1, h, lo))

    def feed_cc(self, hold=0, lx=0.0, ly=0.0, rx=0.0, ry=0.0):
        self.poke(FEED, struct.pack('>IIIIIIIII', 2, 0, 0, 0, hold, f32(lx), f32(ly), f32(rx), f32(ry)))

    def feed_off(self):
        self.poke(FEED, b'\0' * 36)

    def close(self):
        try:
            self.g.close()
        finally:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except Exception:
                self.proc.kill()
