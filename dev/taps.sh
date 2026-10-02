#!/bin/bash
# taps.sh N [button-word=0x100] : tap a GC button N times (2.4 s apart), screenshot "taps_last" at the end
cd "$(dirname "$0")"
for i in $(seq 1 $1); do python3 cmd.py gc:${2:-0x100} sleep:0.25 off sleep:2.0 > /dev/null; done
python3 cmd.py shot:taps_last > /dev/null
