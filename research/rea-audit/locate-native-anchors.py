"""Read-only PE string locations used to focus subsequent REA xref queries.

This is raw-byte provenance, not REA Evidence or proof of a function's behavior.
"""
import hashlib
import json
import struct
from pathlib import Path

source = Path('E:/SteamLibrary/steamapps/common/UNDEFEATED/UNDEFEATED/Binaries/Win64/UNDEFEATED-Win64-Shipping.exe')
data = source.read_bytes()
pe = struct.unpack_from('<I', data, 0x3c)[0]
assert data[pe:pe + 4] == b'PE\0\0'
sections_count = struct.unpack_from('<H', data, pe + 6)[0]
optional_size = struct.unpack_from('<H', data, pe + 20)[0]
optional = pe + 24
assert struct.unpack_from('<H', data, optional)[0] == 0x20b
base = struct.unpack_from('<Q', data, optional + 24)[0]
sections = []
for i in range(sections_count):
    offset = optional + optional_size + i * 40
    virtual_size, rva, raw_size, raw_offset = struct.unpack_from('<IIII', data, offset + 8)
    sections.append((raw_offset, raw_size, rva, data[offset:offset + 8].rstrip(b'\0').decode('ascii')))

matches = []
for anchor in ['ActivitySystemLibrary', 'UndefeatedGameInstance', 'GameActivitySubsystem', 'StartActivity', 'FinishActivity', 'GetActivityID', 'SetEnableActivity']:
    for encoding in ['ascii', 'utf-16le']:
        needle = anchor.encode(encoding)
        start = 0
        while (found := data.find(needle, start)) >= 0:
            start = found + len(needle)
            for raw_offset, raw_size, rva, section in sections:
                if raw_offset <= found < raw_offset + raw_size:
                    matches.append({'anchor': anchor, 'encoding': encoding, 'fileOffset': hex(found), 'address': hex(base + rva + found - raw_offset), 'section': section})
                    break
result = {'provenance': 'Auxiliary raw PE byte search; not REA Evidence. Addresses are query anchors, not identified procedures.', 'source': str(source), 'sha256': hashlib.sha256(data).hexdigest(), 'imageBase': hex(base), 'matches': matches}
destination = Path(__file__).with_name('native-string-anchors.json')
destination.write_text(json.dumps(result, indent=2), encoding='utf8')
print(json.dumps({'matches': len(matches), 'anchors': sorted(set(m['anchor'] for m in matches))}))
