#!/usr/bin/env python3
"""Send commands to srv.py.  Each argument is a JSON object, or shorthand:
   gc:<buttons>[,sx=..,sy=..,cx=..,cy=..]   cc:<hold>[,lx=..]   off   shot:<name>   sleep:<s>   peek:<addr>,<n>   quit"""
import json
import os
import socket
import sys

WORK = os.environ.get('TP_WORK', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'work'))
SOCK = os.path.join(WORK, 'srv.sock')


def parse(a):
    if a.startswith('{'):
        return json.loads(a)
    op, _, rest = a.partition(':')
    m = {'op': op}
    if op in ('gc', 'cc'):
        parts = rest.split(',')
        if parts and parts[0] and '=' not in parts[0]:
            m['buttons' if op == 'gc' else 'hold'] = int(parts[0], 0)
            parts = parts[1:]
        for p in parts:
            if p:
                k, v = p.split('=')
                m[k] = float(v) if op == 'cc' else int(v, 0)
    elif op == 'shot':
        m['name'] = rest
    elif op == 'sleep':
        m['s'] = rest
    elif op == 'peek':
        ad, n = rest.split(',')
        m['addr'], m['n'] = ad, n
    return m


def main():
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(SOCK)
    f = s.makefile('rw')
    for a in sys.argv[1:]:
        f.write(json.dumps(parse(a)) + '\n')
        f.flush()
        r = f.readline().strip()
        print(a, '->', r)


if __name__ == '__main__':
    main()
