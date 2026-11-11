#!/usr/bin/env python3
"""Find .zs files in a nxnative romfs.img whose head is zeroed (the damage that made OoT2 slow down and crash).

Usage: find_damaged_zs.py <path to nxnative checkout> <romfs.img>
Only reads. A healthy .zs starts with the zstd magic 28 b5 2f fd (or a skippable frame 50 2a 4d 18).
"""
import sys
from pathlib import Path

if len(sys.argv) != 3:
    sys.exit(__doc__)
sys.path.insert(0, str(Path(sys.argv[1]) / 'dm/tools'))
import romfs_image as ri

img = sys.argv[2]
OK = (b'\x28\xb5\x2f\xfd', b'\x50\x2a\x4d\x18')
bad = []
with open(img, 'rb') as f:
    for path, (isdir, off, size) in ri.read_index(img).items():
        if isdir or not path.endswith('.zs'):
            continue
        f.seek(off)
        head = f.read(16)
        if head[:4] not in OK:
            bad.append((path, off, size, head[:8].hex()))
for p, off, size, head in bad:
    print(f'{p}\toffset {off}\tsize {size}\thead {head}')
print(f'{len(bad)} damaged .zs file(s)')
