# Technical notes

## The pad layer

Twilight Princess runs all Wii controller input through one per-frame function (`FUN_8000ca10` in
USA Rev 2). For each channel it calls `WPADProbe`, then `KPADRead` into a per-channel struct
(base `0x80433168`, stride `0x1E08` on USA Rev 2). Everything downstream (menus, movement, targeting,
the pointer, sword gestures) reads that struct. So the patch only has to make the data look like a
Wii Remote + Nunchuk; no game logic is edited.

`KPADStatus` (0x88 bytes) fields used: hold `+0`, trig `+4`, release `+8`, pointer `+0x20/+0x24`,
extension type `+0x5C`, Nunchuk stick `+0x60/+0x64`, IR-valid `+0x84`.

## Hooks

Four call sites inside that function are replaced by a branch to a small routine in an injected
section at `0x80001820` (the static build adds it as a text section; Gecko uses `C2` codes):

| Hook | Replaces | Purpose |
|---|---|---|
| P | `bl WPADProbe` | report a Classic Controller or GameCube pad as a Nunchuk (type 1), connected |
| R | `bl KPADRead` | run the real read, then rewrite the samples (see below) |
| G1 | `bl <remote gesture detector>` | add button-driven swing / spin gestures |
| G2 | `bl <nunchuk gesture detector>` | add button-driven shield bash |

Each routine calls the original function by absolute address and then post-processes, so the original
behaviour is preserved when no alternate pad is present. Sites in other releases are found by masked
byte-signature search against USA Rev 2 (`tools/sig.py`), and callees are decoded from the target DOL.

### Hook R

* Classic Controller: the sample's classic button word is mapped to Wii/Nunchuk bits, the left stick is copied
  to the Nunchuk stick.
* GameCube: read straight from the SI registers (`0xCD006400`, +12 per port). Buttons are mapped, sticks are
  converted to floats.
* The C-stick drives a synthetic pointer (deadzone, integration, clamped) and sets the IR-valid byte.
* Trig/release are recomputed against the previous frame so edges are correct.
* ZR/Z held for 24 frames requests a spin attack; a tap requests a swing. These go to hook G as spare button
  bits, which the game ignores, and hook G sets the matching gesture bits through the game's own bit setter.

Per-controller state lives in spare words of the game's own pad struct, so the routines need no data area.

## Data model

`tools/ops.py` defines `Patch`, `Blob` and `Hook`. A `Feature` is a list of them and renders to a patched
DOL, Gecko codes or a Riivolution XML. `tools/gen_prebuilt.py` assembles `src/` with devkitPPC and writes
`tools/prebuilt/*.json`; end users never need the toolchain or any game files for the patcher.

```
python3 tools/gen_prebuilt.py   # needs devkitPPC + retail DOLs (TP_DOLS=<dir with RZDE01.2.dol ...>)
python3 tools/build.py          # codes/ and riivolution/
python3 tools/check.py          # consistency checks, no game files
python3 tools/verify.py         # against retail DOLs
```

## Dev rig

`dev/` drives Dolphin through its GDB stub with a scripted input block, for checking behaviour in-game.

## Verification

USA Rev 2 was played through in Dolphin with a scripted GameCube pad: menus, movement, targeting, camera
reset, sword swing (Z), shield (R) and the spin-attack charge pose (Z held). Europe and Japan were booted
with the patched DOL and driven past the title screen with the GameCube pad. USA v0 only has its hook sites
found by signature search and checked by `tools/verify.py` against the retail DOL (not yet played).

Handy addresses on USA Rev 2 for the dev rig: save status struct `0x80479F30` (maxLife, life, ...), the
equipment bytes start at `0x80479F43` (clothes), sword `0x80479F44`, shield `0x80479F45`.
