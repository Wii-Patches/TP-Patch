# hook G: replaces `bl <gesture detector>` in the game's pad update (one copy for the Wii
# Remote detector, one for the Nunchuk detector).  r17 = the channel struct (callee-saved).
#
# Runs the detector, then turns the gesture requests hook R left in the newest sample's
# trig word into the same "gesture happened" bits the detector itself would have set, by
# calling the game's own setter (set bit in hold, and in trig if it was newly set).
    stwu    r1, -0x30(r1)
    stw     r31, 0x2c(r1)
    lis     r12, DETECT@h
    ori     r12, r12, DETECT@l
    mtctr   r12
    bctrl
    lwz     r31, 8(r17)                 # newest sample's trig word
.if FEED
    lis     r6, FEED@h
    ori     r6, r6, FEED@l
    lwz     r7, GCNT(r6)
    addi    r7, r7, 1
    stw     r7, GCNT(r6)
.endif
    lis     r12, SETBIT@h
    ori     r12, r12, SETBIT@l
    mtctr   r12
@REQUESTS@
    lwz     r31, 0x2c(r1)
    addi    r1, r1, 0x30
