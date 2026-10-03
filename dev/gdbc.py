"""Tiny GDB-remote client for Dolphin's GDB stub (dev/test only).

    g = Gdb(23159); g.cont(); time.sleep(5); g.stop(); g.read(0x80000000, 6); g.cont()

Dolphin halts at boot until a debugger attaches; `Gdb()` attaches and leaves the
CPU stopped.  Memory reads/writes need the CPU stopped (stop()/cont()).
"""
import socket
import struct
import time


class Gdb:
    def __init__(self, port, timeout=60):
        t0 = time.time()
        while True:
            try:
                self.s = socket.create_connection(('127.0.0.1', port), timeout=5)
                break
            except OSError:
                if time.time() - t0 > timeout:
                    raise
                time.sleep(0.5)
        self.s.settimeout(30)
        self.buf = b''
        self.running = False
        self.send('?') if False else None

    # ---- packet layer
    def _raw(self):
        d = self.s.recv(65536)
        if not d:
            raise EOFError('gdb closed')
        self.buf += d

    def _packet(self):
        while True:
            i = self.buf.find(b'$')
            if i >= 0:
                j = self.buf.find(b'#', i)
                if j >= 0 and len(self.buf) >= j + 3:
                    body = self.buf[i + 1:j]
                    self.buf = self.buf[j + 3:]
                    self.s.sendall(b'+')
                    return body.decode('latin1')
            self._raw()

    def send(self, cmd):
        cs = sum(cmd.encode()) & 0xFF
        self.s.sendall(('$%s#%02x' % (cmd, cs)).encode())

    def txn(self, cmd):
        self.send(cmd)
        while True:
            p = self._packet()
            if cmd not in ('c', 's') and (p == '' or (p[:1] in 'TS' and len(p) > 2 and p[1:3].isdigit())):
                continue            # stray stop-reply / empty packets after an interrupt
            return p

    # ---- control
    def cont(self):
        self.send('c')
        self.running = True

    def stop(self):
        if not self.running:
            return
        self.s.sendall(b'\x03')
        self._packet()          # stop reply (S05/T05)
        self.running = False
        time.sleep(0.3)
        self.s.settimeout(0.2)
        try:
            while True:
                self._raw()
        except (socket.timeout, OSError):
            pass
        self.buf = b''
        self.s.settimeout(30)

    def step(self):
        r = self.txn('s')
        return r

    # ---- memory (CPU must be stopped)
    def read(self, addr, n):
        out = b''
        while n:
            k = min(n, 0x400)
            r = self.txn('m%x,%x' % (addr, k))
            if len(r) == 3 and r[0] == 'E':
                raise IOError('read 0x%08X failed: %s' % (addr, r))
            out += bytes.fromhex(r)
            addr += k
            n -= k
        return out

    def write(self, addr, data):
        r = self.txn('M%x,%x:%s' % (addr, len(data), data.hex()))
        if r != 'OK':
            raise IOError('write 0x%08X failed: %s' % (addr, r))

    def u32(self, addr):
        return struct.unpack('>I', self.read(addr, 4))[0]

    def w32(self, addr, v):
        self.write(addr, struct.pack('>I', v & 0xFFFFFFFF))

    def f32(self, addr):
        return struct.unpack('>f', self.read(addr, 4))[0]

    def regs(self):
        r = bytes.fromhex(self.txn('g'))
        return struct.unpack('>%dI' % (len(r) // 4), r)

    # ---- breakpoints (software, 4-byte instructions)
    def bp_set(self, addr):
        return self.txn('Z0,%x,4' % addr)

    def bp_clear(self, addr):
        return self.txn('z0,%x,4' % addr)

    def wait_stop(self, timeout=5):
        """After cont(): wait for a stop reply (breakpoint hit); None on timeout."""
        self.s.settimeout(timeout)
        try:
            p = self._packet()
            self.running = False
            return p
        except socket.timeout:
            return None
        finally:
            self.s.settimeout(30)

    def close(self):
        try:
            self.s.close()
        except OSError:
            pass
