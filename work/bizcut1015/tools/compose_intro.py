"""SephirothForms.json with Bizarro's cutscene entrance: the BIZARRO form's "entrance" (shots from EV_FOREE_8630) and its
switch sounds without the line (the entrance says it now, before the switch).
    compose_intro.py <SephirothForms.json in> <entrance.json> <out>"""
import json, sys

ADDED = (" Switching to BIZARRO plays his transformation cutscene's ending: Sephiroth says \"Alone at last. Shall we?\" in the "
         "cutscene's close-up and camera, the darkness takes him, a white flash, and Bizarro Sephiroth rises into view with "
         "the cutscene's camera, animation, effects and sound (any ability skips it; the switch still happens).")


def main(src, entrance, out):
    d = json.load(open(src, encoding='utf-8'))
    row = d['animation_sets'][0]
    forms = row['forms']['list']
    biz = next(f for f in forms if f.get('name') == 'BIZARRO')
    e = json.load(open(entrance, encoding='utf-8'))
    biz['entrance'] = e
    before = len(biz.get('sounds', []))
    biz['sounds'] = [s for s in biz.get('sounds', []) if 'C3510_MAIN_3400_0400_00_sep' not in json.dumps(s)]
    if ADDED.strip() not in d['source']:
        d['source'] = d['source'] + ADDED
    json.dump(d, open(out, 'w', encoding='utf-8'), indent='\t', ensure_ascii=False)
    print('BIZARRO: entrance with %d shots (%.1f s); sounds %d -> %d' % (len(e['shots']), sum(s['seconds'] for s in e['shots']), before, len(biz['sounds'])))


if __name__ == '__main__':
    main(*sys.argv[1:4])
