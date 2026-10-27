"""The DISSIDIA NT form's PC scripts, made from the CRISIS CORE form's (pc_cc/) with its names, folders and set."""
import os, re
SRC, DST = 'pc_cc', 'pc_dnt'

def conv(name, out, reps, crlf=False):
    s = open(os.path.join(SRC, name), 'rb').read().decode('utf-8').replace('\r\n', '\n')
    for a, b, n in reps:
        c = s.count(a)
        assert c == n, (name, a, c, n)
        s = s.replace(a, b)
    for bad in ('CrisisCore', 'Crisis Core', 'CRISIS CORE', 'cc_', 'Battle10', 'PC0010_16', 'CCRoot', 'keys3'):
        left = [l for l in s.split('\n') if bad in l and 'made from' not in l and 'Made from' not in l]
        assert not left, (name, bad, left[:3])
    if crlf:
        s = s.replace('\n', '\r\n')
    open(os.path.join(DST, out), 'wb').write(s.encode('utf-8'))

conv('build_cc_form.py', 'build_dnt_form.py', [
    ("# CRISIS CORE (Battle10), the editor step of run_cc_form.cmd: builds every move of\n# Saved/RebirthSkelCompat/CrisisCoreForm/cmd/plan.json",
     "# DISSIDIA NT (Battle12), the editor step of run_dnt_form.cmd (made from the CRISIS CORE form's): builds every move of\n# Saved/RebirthSkelCompat/DissidiaNTForm/cmd/plan.json", 1),
    ("trails and swing sounds from each move's carrier (cc_build.py). make_container_cc.py cooks and packs them after.",
     "trails and swing sounds from each move's carrier (dnt_form_build.py). make_container_dnt.py cooks and packs them after.", 1),
    ("editor is left out when run_cc_form.ps1 runs this again", "editor is left out when run_dnt_form.ps1 runs this again", 1),
    ("# Results in Saved/RebirthSkelCompat/CrisisCoreForm: build_result.json, progress.json, built.json.",
     "# Results in Saved/RebirthSkelCompat/DissidiaNTForm: build_result.json, progress.json, built.json.", 1),
    ("# (2026-10-26) First, Crisis Core's animations (CCRoot) are made anew from the key animations in keys3.",
     "# First, Dissidia NT's animations (DNTRoot) are made anew from the key animations in keys (dnt_anim.py's .cacanim).", 1),
    ("OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'CrisisCoreForm')", "OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'DissidiaNTForm')", 1),
    ("CRISIS CORE FORM BUILD", "DISSIDIA NT FORM BUILD", 2),
    ("'cmd', 'cc_build.py'", "'cmd', 'dnt_form_build.py'", 1),
    ("'/Game/Motion/Player/PC0010_16_CrisisCore_Sephiroth'", "'/Game/Motion/Player/PC0010_19_DissidiaNT_Sephiroth'", 2),
    ("    # (2026-10-26) Crisis Core's animations made anew from the key animations in keys3 (the body upright under the root,\n    # as the game's own animations have it: the first go's moves lay on their side in game), once a go, before anything\n    # loads them (Import Key Animations makes each anew; one that is loaded is not replaced)\n    keys_dir = os.path.join(OUT, 'keys3')",
     "    # Dissidia NT's animations made anew from the key animations in keys (the body upright under the root, as the game's\n    # own animations have it), once a go, before anything loads them (Import Key Animations makes each anew; one that is\n    # loaded is not replaced)\n    keys_dir = os.path.join(OUT, 'keys')", 1),
    ("'/Game/Motion/Player/PC0010_16_CrisisCore_Sephiroth/CCRoot'", "'/Game/Motion/Player/PC0010_19_DissidiaNT_Sephiroth/DNTRoot'", 1),
    ("NOT ALL IMPORTED (the report comes back only when every one went in: see the log)", "NOT ALL IMPORTED (the report comes back only when every one went in: see the log)", 1),
    ("raise RuntimeError('the Crisis Core key animations (keys3) did not all import')", "raise RuntimeError('the Dissidia NT key animations (keys) did not all import')", 1),
])
conv('cc_build.py', 'dnt_form_build.py', [
    ("# CRISIS CORE (Battle10): Crisis Core Reunion Sephiroth's battle animations (retargeted onto Rebirth Sephiroth's skeleton,\n# /Game/Motion/Player/PC0010_16_CrisisCore_Sephiroth/CCRoot) as his player moves, built in the End editor with Create a\n# Character System's Build Moves, in an editor commandlet (build_cc_form.py): setup(), then build([...]) per move.\n# (Made from the REMAKE forms' rf_build.py: the same steps, its own data object, folders and plan.)",
     "# DISSIDIA NT (Battle12): Dissidia NT Sephiroth's motions (retargeted onto Rebirth Sephiroth's skeleton,\n# /Game/Motion/Player/PC0010_19_DissidiaNT_Sephiroth/DNTRoot) as his player moves, built in the End editor with Create a\n# Character System's Build Moves, in an editor commandlet (build_dnt_form.py): setup(), then build([...]) per move.\n# (Made from the CRISIS CORE form's cc_build.py: the same steps, its own data object, folders and plan.)", 1),
    ("# Each move is built twice from the same Crisis Core animation:", "# Each move is built twice from the same Dissidia NT animation:", 1),
    ("its damage re-timed onto Crisis Core's blows;", "its damage re-timed onto Dissidia NT's blows;", 1),
    ("#   row 1, a carrier (Built/CrisisCoreFormCarriers/<set>/<name>)", "#   row 1, a carrier (Built/DissidiaNTFormCarriers/<set>/<name>)", 1),
    ("OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'CrisisCoreForm')", "OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'DissidiaNTForm')", 1),
    ("DATA_PATH = '/Game/RebirthSkelCompat/CrisisCoreForm/CrisisCoreForm_Data'", "DATA_PATH = '/Game/RebirthSkelCompat/DissidiaNTForm/DissidiaNTForm_Data'", 1),
    ("CARRIER_FOLDER = '/Game/RebirthSkelCompat/Built/CrisisCoreFormCarriers'", "CARRIER_FOLDER = '/Game/RebirthSkelCompat/Built/DissidiaNTFormCarriers'", 1),
    ("SOURCES = [('/Game/Motion/Player/PC0010_Sephiroth/Battle00.Battle00', 'Battle10')]", "SOURCES = [('/Game/Motion/Player/PC0010_Sephiroth/Battle00.Battle00', 'Battle12')]", 1),
    ("the Crisis Core key animations have no notifies", "the Dissidia NT key animations have no notifies", 1),
    ("(\"Battle10/B_NAttack01_0\", ...)", "(\"Battle12/B_NAttack01_0\", ...)", 1),
])
conv('run_cc_form.ps1', 'run_dnt_form.ps1', [
    ("# The editor step of run_cc_form.cmd: runs build_cc_form.py in an editor commandlet (End editor closed).",
     "# The editor step of run_dnt_form.cmd: runs build_dnt_form.py in an editor commandlet (End editor closed).", 1),
    ("Log: build\\cc_editor.log", "Log: build\\dnt_editor.log", 1),
    ("$Status = Join-Path $Build 'cc_status.txt'", "$Status = Join-Path $Build 'dnt_status.txt'", 1),
    ("$Script = Join-Path $Here 'build_cc_form.py'", "$Script = Join-Path $Here 'build_dnt_form.py'", 1),
    ("'C:\\FF7R2UProj\\Saved\\RebirthSkelCompat\\CrisisCoreForm\\build_result.json'", "'C:\\FF7R2UProj\\Saved\\RebirthSkelCompat\\DissidiaNTForm\\build_result.json'", 1),
    ("'C:\\FF7R2UProj\\Saved\\RebirthSkelCompat\\CrisisCoreForm\\progress.json'", "'C:\\FF7R2UProj\\Saved\\RebirthSkelCompat\\DissidiaNTForm\\progress.json'", 1),
    ("$Log = Join-Path $Build 'cc_editor.log'", "$Log = Join-Path $Build 'dnt_editor.log'", 1),
    ("('cc_editor_{0:yyyyMMdd_HHmmss}.log' -f (Get-Date))", "('dnt_editor_{0:yyyyMMdd_HHmmss}.log' -f (Get-Date))", 1),
    ("see build\\cc_editor*.log", "see build\\dnt_editor*.log", 1),
])
conv('run_cc_form.cmd', 'run_dnt_form.cmd', [
    ("title CRISIS CORE form - building Sephiroth's Crisis Core moves, please leave this window open",
     "title DISSIDIA NT form - building Sephiroth's Dissidia NT moves, please leave this window open", 1),
    ("rem CRISIS CORE (close the End editor and the game first):", "rem DISSIDIA NT (close the End editor and the game first):", 1),
    ("rem   1. builds the form's 18 moves from Crisis Core Reunion Sephiroth's animations in an editor commandlet, with Rebirth\nrem      Sephiroth's damage and timing on Crisis Core's blows",
     "rem   1. imports Dissidia NT Sephiroth's animations (keys) and builds the form's 18 moves from them in an editor\nrem      commandlet, with Rebirth Sephiroth's damage and timing on Dissidia NT's blows", 1),
    ("rem   2. cooks them with the engine's cook commandlet and packs them with IoStore into CrisisCoreFormMoves.utoc/.ucas",
     "rem   2. cooks them with the engine's cook commandlet and packs them with IoStore into DissidiaNTFormMoves.utoc/.ucas", 1),
    ("rem Status: build\\cc_status.txt. Results: C:\\FF7R2UProj\\Saved\\RebirthSkelCompat\\CrisisCoreForm\\",
     "rem Status: build\\dnt_status.txt. Results: C:\\FF7R2UProj\\Saved\\RebirthSkelCompat\\DissidiaNTForm\\", 1),
    ("set \"STATUS=%~dp0build\\cc_status.txt\"", "set \"STATUS=%~dp0build\\dnt_status.txt\"", 1),
    ("echo CRISIS CORE form, started %DATE% %TIME%> \"%STATUS%\"", "echo DISSIDIA NT form, started %DATE% %TIME%> \"%STATUS%\"", 1),
    ("for %%F in (build_cc_form.py run_cc_form.ps1 make_container_cc.py) do (", "for %%F in (build_dnt_form.py run_dnt_form.ps1 make_container_dnt.py) do (", 1),
    ("\"C:\\FF7R2UProj\\Saved\\RebirthSkelCompat\\CrisisCoreForm\\cmd\\plan.json\"", "\"C:\\FF7R2UProj\\Saved\\RebirthSkelCompat\\DissidiaNTForm\\cmd\\plan.json\"", 1),
    ("echo FAILED: Saved\\RebirthSkelCompat\\CrisisCoreForm\\cmd\\plan.json is missing", "echo FAILED: Saved\\RebirthSkelCompat\\DissidiaNTForm\\cmd\\plan.json is missing", 1),
    ("powershell -NoProfile -ExecutionPolicy Bypass -File \"%~dp0run_cc_form.ps1\"", "powershell -NoProfile -ExecutionPolicy Bypass -File \"%~dp0run_dnt_form.ps1\"", 1),
    ("echo FAILED: the editor step ^(build\\cc_editor.log, Saved\\RebirthSkelCompat\\CrisisCoreForm\\build_result.json and progress.json^)",
     "echo FAILED: the editor step ^(build\\dnt_editor.log, Saved\\RebirthSkelCompat\\DissidiaNTForm\\build_result.json and progress.json^)", 1),
    ("%PY% \"%~dp0make_container_cc.py\"", "%PY% \"%~dp0make_container_dnt.py\"", 1),
    ("echo FAILED: the cook or the container ^(Saved\\RebirthSkelCompat\\CrisisCoreForm\\_work\\cook.log and iostore.log^)",
     "echo FAILED: the cook or the container ^(Saved\\RebirthSkelCompat\\DissidiaNTForm\\_work\\cook.log and iostore.log^)", 1),
    ("echo CRISIS CORE FORM STEP COMPLETE %DATE% %TIME%", "echo DISSIDIA NT FORM STEP COMPLETE %DATE% %TIME%", 1),
], crlf=True)
conv('make_container_cc.py', 'make_container_dnt.py', [
    ("\"\"\"CRISIS CORE, the container step of run_cc_form.cmd: the moves build_cc_form.py built (the ones in\nSaved/RebirthSkelCompat/CrisisCoreForm/built.json)",
     "\"\"\"DISSIDIA NT, the container step of run_dnt_form.cmd (made from the CRISIS CORE form's): the moves build_dnt_form.py\nbuilt (the ones in Saved/RebirthSkelCompat/DissidiaNTForm/built.json)", 1),
    ("commandlet into _work/Container/CrisisCoreFormMoves.utoc/.ucas", "commandlet into _work/Container/DissidiaNTFormMoves.utoc/.ucas", 1),
    ("OUT = r'C:\\FF7R2UProj\\Saved\\RebirthSkelCompat\\CrisisCoreForm'", "OUT = r'C:\\FF7R2UProj\\Saved\\RebirthSkelCompat\\DissidiaNTForm'", 1),
    ("NAME = 'CrisisCoreFormMoves'", "NAME = 'DissidiaNTFormMoves'", 1),
])
print('ok')
