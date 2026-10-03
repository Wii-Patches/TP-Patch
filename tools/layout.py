"""Where the hook routines live in the injected low-memory section.

Every patch is a set of hooks: one instruction in the game is replaced by a branch to a small
self-contained routine.  A Gecko code handler stores those routines itself (C2 codes); the
patched DOL and the Riivolution patch need somewhere to put them, so the patcher adds one text
section at CAVE_BASE.

0x80001800-0x80003000 is the Wii's boot-time scratch area; the first 0x20 bytes are skipped (the
word at 0x80001800 is overwritten by the OS early on).  The routines hold no variables of their
own: their per-controller state lives in spare words of the game's own pad structures.
"""
CAVE_BASE = 0x80001820
CAVE_LIMIT = 0x80003000

PROBE_BASE = 0x80001820       # WPADProbe call-site hook
PROBE_END = 0x80001900
GEST_BASE = 0x80001900        # the two gesture hooks
GEST_END = 0x80001B00
READ_BASE = 0x80001B00        # KPADRead call-site hook
READ_END = 0x80002C00
WINDOWS = {'pad': (PROBE_BASE, READ_END)}
FEED = 0x80002F00             # dev builds only: scripted input block (never in a release)
