# hook P: replaces `bl WPADProbe` in the game's pad update.
#   r3 = channel, r4 = &type out.  The caller keeps channel in r16, its per-channel struct in
#   r17 and &type in r18, all callee-saved, so they are still intact when we get control back.
#
# A Classic Controller (type 2) or a GameCube pad on the channel is reported as a Nunchuk
# (type 1) with result 0, which is the only combination the game accepts for play.
    lis     r12, PROBE@h
    ori     r12, r12, PROBE@l
    mtctr   r12
    bctrl
    cmpwi   r16, 0
    bne     9f                          # single player: only channel 0
    lwz     r5, 0(r18)                  # extension type the SDK reported
    cmpwi   r5, 2
    bne     2f
    li      r5, 1                       # classic -> nunchuk
    stw     r5, 0(r18)
    stw     r5, 0x1dec(r17)             # the type the extension callback recorded
    b       9f
2:
.if FEED
    lis     r4, FEED@h
    ori     r4, r4, FEED@l
    lwz     r6, 0(r4)
    cmpwi   r6, 1
    bne     3f
    lwz     r8, 4(r4)
    b       4f
3:
    cmpwi   r6, 2
    bne     5f
    li      r5, 1
    stw     r5, 0(r18)
    stw     r5, 0x1dec(r17)
    li      r3, 0
    b       9f
5:
.endif
    cmplwi  r16, 3
    bgt     9f
    mulli   r5, r16, 12
    lis     r6, 0xCD00
    add     r6, r6, r5
    lwz     r8, 0x6404(r6)              # SIC0INBUFH: the pad's last answer
4:
    cmpwi   r8, 0
    blt     9f                          # error / no pad
    andis.  r0, r8, 0x0080
    beq     9f                          # bit 23 is set in every real pad answer
    li      r3, 0                       # a controller is there...
    li      r5, 1
    stw     r5, 0(r18)                  # ...and it is a Nunchuk
    stw     r5, 0x1dec(r17)
.if PADONLY
    stb     r5, 0x1dd4(r17)             # connected: no Wii Remote needed
.endif
9:
    nop
