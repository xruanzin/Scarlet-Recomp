"""Summarize observed consumers; these counts are sampled, not update rates."""
import collections
import json
import re
import sys
from pathlib import Path
rows = collections.defaultdict(lambda: {'samples':0, 'indices':set(), 'steps':set()})
for line in Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace').splitlines():
    if '[scarlet-timing-read]' not in line:
        continue
    fields = dict(re.findall(r'(\w+)=(\w+)', line))
    row = rows[fields['caller']]
    row['samples'] += 1
    row['indices'].add(int(fields['index']))
    row['steps'].add(int(fields['step_ns']))
print(json.dumps({caller:{k:sorted(v) if isinstance(v,set) else v for k,v in row.items()}
                  for caller,row in sorted(rows.items())}, indent=2))
