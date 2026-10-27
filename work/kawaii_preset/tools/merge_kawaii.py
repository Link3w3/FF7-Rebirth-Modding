"""Put several preset entries (make_kawaii_preset.py's files) into one compat file for Create a Character System.
    merge_kawaii.py <out.json> <note> <entry.json> ..."""
import json, sys
out, note, files = sys.argv[1], sys.argv[2], sys.argv[3:]
entries = []
for f in files:
    entries += json.load(open(f, encoding='utf-8'))['kawaii']
doc = {'schema': 'RebirthSkelCompat/1', 'note': note, 'kawaii': entries}
with open(out, 'w', encoding='utf-8', newline='\r\n') as f:
    json.dump(doc, f, indent=1)
    f.write('\n')
print(out, len(entries), 'entries,', sum(len(e['nodes']) for e in entries), 'nodes')
