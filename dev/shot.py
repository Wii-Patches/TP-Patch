"""Screenshot of this session's Dolphin render window (macOS)."""
import subprocess
import Quartz


def windows(pid):
    out = []
    for w in Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID):
        if w.get('kCGWindowOwnerPID') == pid and w.get('kCGWindowLayer') == 0:
            b = w['kCGWindowBounds']
            out.append((w['kCGWindowNumber'], w.get('kCGWindowName', ''), b['Width'], b['Height']))
    return out


def shoot(pid, path):
    ws = [w for w in windows(pid) if w[2] > 200]
    if not ws:
        raise RuntimeError('no window for pid %d: %s' % (pid, windows(pid)))
    wid = max(ws, key=lambda w: w[2] * w[3])[0]
    subprocess.run(['screencapture', '-x', '-o', '-l', str(wid), path], check=True)
    return path
