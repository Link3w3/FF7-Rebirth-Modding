"""After run_dnt_form.cmd on the PC: the DISSIDIA NT form (Battle12) and the CRISIS CORE skins' field set (Neutral10) into
Fully Playable Young Sephiroth, staged for one install .cmd:
  1. the moves container (Saved/RebirthSkelCompat/DissidiaNTForm/_work/Container/DissidiaNTFormMoves.utoc/.ucas, copied
     here as <moves dir>);
  2. the data container: the installed FullyPlayableYoungSephirothDataAssets_P with the 22 moves added and Battle12 on
     Sephiroth's CharaSpec rows (build_form_data.py: the installed blocks kept, a tail appended);
  3. YoungSephirothForms.json: the DISSIDIA NT form (his PC0010_19_DNT_1p1c model as a look, the REMAKE form's change
     effects) and the field set Neutral10 (patch_form_json.py), made from the installed one;
  4. <stage>: the new .utoc, the .ucas tail, the forms file, install_data_rebase.py, install_forms_json.py and
     install_forms_1027.cmd (CRLF), with every MD5 the .cmd checks.
    finish_forms_1027.py <moves dir> <installed .utoc> <installed build's .tail> <installed forms .json> <plan.json> <stage dir>"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INSTALLERS = {'install_data_rebase.py': os.path.join(HERE, 'pc_install', 'install_data_rebase.py'),
              'install_forms_json.py': os.path.join(HERE, 'pc_install', 'install_forms_json.py')}
FORM_NAME = 'DISSIDIA NT'
MODEL = '/Game/Character/Player/PC0010_19_DissidiaNT_Sephiroth/Model/PC0010_19_DNT_1p1c.PC0010_19_DNT_1p1c'
NOTE = ("DISSIDIA NT (Battle12): Dissidia NT Sephiroth in his own model, fighting with his own Dissidia NT motions: his four "
        "ground Bravery attacks as the combo, the lunge stance and its release (hold Square), the crouch, dash and cut "
        "(Triangle), his whirling wind-up, dash and cuts as the limit, his cast, idle, damage and victory, with Sephiroth's "
        "combo, cancel and dodge windows and damage on his blows, the Masamune's trail and swing on every slash; the rest of "
        "his moves are Sephiroth's. Neutral10: the CRISIS CORE skins' field idle, walk, run and dash. The moves are in the "
        "data container.")
NAME = 'FullyPlayableYoungSephirothDataAssets_P'
# the installed .ucas (all of it is the base: 267039472 bytes), its MD5 read on the PC on 2026-10-27; the new .ucas's MD5
# (base + tail) is filled in on the PC (@NEW_UCAS_MD5@: finish step 2, device side) once the tail is there
BASE_UCAS_MD5 = '70f560cbabd6637b9ce829a756cbc129'


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main(moves_dir, utoc, tail, forms, plan, stage):
    assert not os.path.exists(stage), stage + ' exists (use a new folder)'
    build = stage + '_build'
    assert not os.path.exists(build), build + ' exists'
    moves = os.path.join(moves_dir, 'DissidiaNTFormMoves.utoc')
    subprocess.check_call([sys.executable, os.path.join(HERE, 'build_form_data.py'), utoc, tail, moves, build, 'Battle12', 'Neutral10'])
    sums = json.load(open(os.path.join(build, 'build.json')))
    out_json = stage + '_json'
    subprocess.check_call([sys.executable, os.path.join(HERE, 'patch_form_json.py'), plan, forms, out_json, FORM_NAME, MODEL, NOTE, 'Neutral10'])
    os.makedirs(stage)
    for f in (NAME + '.utoc', NAME + '.ucas.tail'):
        shutil.copyfile(os.path.join(build, f), os.path.join(stage, f))
    shutil.copyfile(os.path.join(out_json, os.path.basename(forms)), os.path.join(stage, 'YoungSephirothForms.json'))
    for f, src in INSTALLERS.items():
        shutil.copyfile(src, os.path.join(stage, f))
    accepted = sums['base_utoc_md5']
    cmd = open(os.path.join(HERE, 'install_forms_1027.cmd.in')).read()
    for k, v in {'@BASE_SIZE@': str(sums['base_size']), '@BASE_MD5@': BASE_UCAS_MD5, '@UTOC_MD5@': sums['utoc_md5'],
                 '@UCAS_SIZE@': str(sums['ucas_size']), '@ACCEPTED@': accepted,
                 '@FORMS_OLD_MD5@': md5(forms), '@FORMS_NEW_MD5@': md5(os.path.join(stage, 'YoungSephirothForms.json'))}.items():
        cmd = cmd.replace(k, v)
    sums['forms_old_md5'] = md5(forms)
    sums['forms_new_md5'] = md5(os.path.join(stage, 'YoungSephirothForms.json'))
    json.dump(sums, open(os.path.join(stage, 'build.json'), 'w'), indent=1)
    open(os.path.join(stage, 'install_forms_1027.cmd'), 'w', newline='\r\n').write(cmd)
    for f in sorted(os.listdir(stage)):
        print('  %-48s %10d %s' % (f, os.path.getsize(os.path.join(stage, f)), md5(os.path.join(stage, f))))


if __name__ == '__main__':
    main(*sys.argv[1:7])
