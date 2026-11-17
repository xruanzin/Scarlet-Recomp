"""Integration guard test against the user's original Scarlet NSO."""
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nso import Nso
from scarlet.native_timing import patches, SITES

n = Nso(sys.argv[1])
m = SimpleNamespace(nso=n, base=0x7000000000)
assert len(patches(m)) == 7
def rejected():
    try:
        patches(m)
    except ValueError:
        return
    raise AssertionError('Modified input accepted')
original_id = n.build_id
n.build_id = '0' * len(original_id)
rejected()
n.build_id = original_id
for offset in [0x3c2fba8, 0x92dd14, 0x92dd18, 0x92dd1c] + [0x19756f0+4*i for i in range(7)] + [0xc92cd8+4*i for i in range(5)] + [0xd07a4c+4*i for i in range(6)] + [0xd07ab4+4*i for i in range(10)] + [site-12+4*i for site in SITES for i in range(6)]:
    n.image[offset] ^= 1
    rejected()
    n.image[offset] ^= 1
original_relocs = n.relocs
for off in (0x46d8bc0, 0x44c2a78, 0x44c2a68):
    n.relocs = [r for r in original_relocs if r[0] != off]
    rejected()
n.relocs = original_relocs
assert len(patches(m)) == 7
print('PASS: original Scarlet accepted; wrong identity, table, registrations and all 49 instruction mutations rejected')
