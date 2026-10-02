#!/bin/bash
# usage: rebuild.sh <fstdir> <regionkey> <origdol> <out.wbfs> [--feed]
set -e
cd "$(dirname "$0")/.."
python3 dev/mkdol.py "$2" "$3" "$1/sys/main.dol" $5
wit copy "$1" --dest "$4" --wbfs --overwrite -q
