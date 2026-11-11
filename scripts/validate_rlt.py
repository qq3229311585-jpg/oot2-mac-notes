#!/usr/bin/env python3
"""Check a decompressed BNTX's relocation table (_RLT): every relocated 8-byte value must be < file size and no
position may repeat. A stand-in texture whose table is wrong crashes the game (the pointer gets the base added twice).
Usage: python -I validate_rlt.py <file.bntx.zs>   (Python 3.14+: needs compression.zstd)
"""
import sys, struct
from compression import zstd
d = zstd.decompress(open(sys.argv[1], 'rb').read())
rlt = struct.unpack_from('<I', d, 0x18)[0]; assert d[rlt:rlt+4] == b'_RLT'
nsec = struct.unpack_from('<I', d, rlt+8)[0]; ents = rlt + 0x10 + nsec*0x18
seen = []; bad = 0
for s in range(nsec):
    _, _, _, ei, ec = struct.unpack_from('<QIIII', d, rlt+0x10+s*0x18)
    for e in range(ei, ei+ec):
        p, sc, oc, pc = struct.unpack_from('<IHBB', d, ents+e*8)
        for _ in range(sc):
            for _ in range(oc):
                bad += struct.unpack_from('<Q', d, p)[0] >= len(d); seen.append(p); p += 8
            p += pc*8
print('pointers', len(seen), 'invalid', bad, 'duplicate', len(seen)-len(set(seen)))
