#!/usr/bin/env python3
"""Persistent Dolphin test session controlled over a unix socket (dev only).

    srv.py <disc> [--video Metal] [--speed 1] [--ext Nunchuk|Classic|none] [--gc]

Commands (one JSON object per line):  {"op": "gc", "buttons": 256, "sx": 128 ...}
  gc / cc / off / shot <name> / peek <addr> <n> / sleep <s> / quit
"""
import argparse
import json
import os
import socket
import struct
import sys
import time

from session import Session
from shot import shoot

WORK = os.environ.get('TP_WORK', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'work'))
SOCK = os.path.join(WORK, 'srv.sock')
SHOTS = os.path.join(WORK, 'shots')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('disc')
    ap.add_argument('--video', default='Metal')
    ap.add_argument('--speed', default='1')
    ap.add_argument('--ext', default='Nunchuk')
    ap.add_argument('--gc', action='store_true')
    a = ap.parse_args()
    os.makedirs(SHOTS, exist_ok=True)
    s = Session(a.disc, video=a.video, wiimote_ext=None if a.ext == 'none' else a.ext, gc_pad=a.gc,
                speed=0 if a.speed == '0' else float(a.speed))
    if os.path.exists(SOCK):
        os.unlink(SOCK)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(SOCK)
    srv.listen(1)
    print('ready', flush=True)
    try:
        while True:
            c, _ = srv.accept()
            f = c.makefile('rw')
            for line in f:
                try:
                    m = json.loads(line)
                    op = m['op']
                    r = 'ok'
                    if op == 'gc':
                        s.feed_gc(**{k: v for k, v in m.items() if k != 'op'})
                    elif op == 'cc':
                        s.feed_cc(**{k: v for k, v in m.items() if k != 'op'})
                    elif op == 'off':
                        s.feed_off()
                    elif op == 'shot':
                        r = shoot(s.proc.pid, '%s/%s.png' % (SHOTS, m['name']))
                    elif op == 'peek':
                        r = s.peek(int(m['addr'], 0), int(m['n'])).hex()
                    elif op == 'poke':
                        s.poke(int(m['addr'], 0), bytes.fromhex(m['data']))
                    elif op == 'sleep':
                        time.sleep(float(m['s']))
                    elif op == 'quit':
                        f.write('bye\n'); f.flush(); c.close(); return
                    else:
                        r = 'unknown op'
                except Exception as e:
                    r = 'ERR %s' % e
                f.write(r + '\n')
                f.flush()
            c.close()
    finally:
        s.close()


if __name__ == '__main__':
    main()
