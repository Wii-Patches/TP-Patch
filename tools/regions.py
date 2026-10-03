"""The retail releases of The Legend of Zelda: Twilight Princess (Wii) and their main.dol.

A release is identified by the six-character disc id plus the disc version byte (offset 7
of the disc header); USA has two retail revisions (version 0 and version 2) under one id.
"""
REGIONS = {
    'RZDE01.0': dict(id='RZDE01', version=0, label='Twilight Princess (USA)', short='USA',
                     dol_size=4513888),
    'RZDE01.2': dict(id='RZDE01', version=2, label='Twilight Princess (USA, Rev 2)', short='USA Rev 2',
                     dol_size=4412736),
    'RZDP01.0': dict(id='RZDP01', version=0, label='Twilight Princess (Europe / Australia)', short='Europe',
                     dol_size=4414720),
    'RZDJ01.0': dict(id='RZDJ01', version=0, label='Zelda no Densetsu: Twilight Princess (Japan)', short='Japan',
                     dol_size=4404096),
}


def key_for(disc_id, version):
    k = '%s.%d' % (disc_id, version)
    return k if k in REGIONS else None
