import sys, json
plan = json.load(open('plan.json'))
# the device script: read the listed block ranges into one blob
ranges = []
for e in plan:
    for b in e['blocks']:
        ranges.append((e['container'], b[0], b[1]))
ranges = sorted(set(map(tuple, ranges)))
json.dump(ranges, open('ranges.json', 'w'))
print(len(ranges), 'ranges', sum(r[2] for r in ranges), 'bytes')
