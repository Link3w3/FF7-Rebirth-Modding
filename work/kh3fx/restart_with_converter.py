"""Turns on Epic's Cascade To Niagara Converter plugin for the End project and restarts this editor so it loads (the
plugin's binaries come with the engine). Nothing happens if anything is unsaved."""
import json
import os
import shutil
import subprocess
import sys
import time
import unreal

result = {}
proj = unreal.Paths.convert_relative_path_to_full(unreal.Paths.get_project_file_path()).replace('/', '\\')
dirty = ([str(p.get_name()) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()] +
         [str(p.get_name()) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
if dirty:
    raise RuntimeError('unsaved work in the editor, not restarting: %s' % dirty)

saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
backups = os.path.join(saved, 'ModExtract', 'backups')
os.makedirs(backups, exist_ok=True)
backup = os.path.join(backups, 'End.uproject.%s' % time.strftime('%Y%m%d-%H%M%S'))
shutil.copy2(proj, backup)
with open(proj, encoding='utf-8-sig') as f:
    data = json.load(f)
plugins = data.setdefault('Plugins', [])
entry = next((p for p in plugins if p.get('Name') == 'CascadeToNiagaraConverter'), None)
if entry is None:
    plugins.append({'Name': 'CascadeToNiagaraConverter', 'Enabled': True})
else:
    entry['Enabled'] = True
with open(proj, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent='\t')
    f.write('\n')

exe = sys.executable
pid = os.getpid()
ps = ("Wait-Process -Id %d -Timeout 240 -ErrorAction SilentlyContinue; "
      "Start-Sleep -Seconds 3; "
      "if (-not (Get-Process -Id %d -ErrorAction SilentlyContinue)) { Start-Process -FilePath '%s' -ArgumentList '\"%s\"' }"
      % (pid, pid, exe, proj))
subprocess.Popen(['powershell', '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden', '-Command', ps],
                 creationflags=0x00000008 | 0x00000200, close_fds=True)
result = dict(backup=backup, project=proj, exe=exe, pid=pid, plugins=len(plugins))
unreal.SystemLibrary.quit_editor()
