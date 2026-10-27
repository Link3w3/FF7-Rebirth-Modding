"""Remake Importer: a FINAL FANTASY VII REMAKE character into the End project, for remake_character.py.

The End editor's Rebirth FX > Import FF7 Remake Character... runs this with your own Python 3 (py -3) and imports the job
it makes. By hand:
    py -3 remake_importer.py                   the window: the Remake folder, your AES key, the character
    py -3 remake_importer.py --console         the same questions in the console (no window)
    py -3 remake_importer.py --check           what this Python has: numpy, AES, the Oodle decompressor (ooz.dll)
    py -3 remake_importer.py --list            the characters in the paks (asks for the key)
    py -3 remake_importer.py --character PC0002_00_Tifa_Standard     that character's job (asks for the key)
Then, in the editor (Output Log, Cmd):  py "C:/FF7R2UProj/Tools/RemakeMaterials/remake_character.py" "<the job>"

Your AES key is asked for in the window (or the console, without echo) and kept in memory for that run only: it is never
written to a file, a log, the settings or a command line, and there is no option to pass it in.
First run: numpy is installed for your Python (pip install --user numpy) if it is missing, and ooz.dll (the Oodle
decompressor Remake's paks need) is built once with build_ooz.cmd (Visual Studio 2022's C++ compiler).
"""
import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import remake_paks as rp

VERSION = '1.0'
TITLE = 'Import FF7 Remake Character'
DEFAULT_GAME = r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REMAKE'
DEFAULT_PROJECT = os.path.normpath(os.path.join(HERE, '..', '..'))      # Tools/RemakeImporter -> the End project
BUILD_OOZ = os.path.join(HERE, 'build_ooz.cmd')
NO_WINDOW = 0x08000000 if os.name == 'nt' else 0                         # CREATE_NO_WINDOW


# ---------------------------------------------------------------------------------------------------------------------
# settings (the game folder only), numpy, the result file for the editor
# ---------------------------------------------------------------------------------------------------------------------

def _settings_path(project):
    return os.path.join(project, 'Saved', 'RemakeImporter', 'importer_settings.json')


def load_settings(project):
    try:
        with open(_settings_path(project), encoding='utf-8') as f:
            s = json.load(f)
        if not isinstance(s, dict):
            return {}
        if s.get('game') and not os.path.isdir(s['game']):
            s.pop('game')                                 # (a folder that is not there any more)
        return s
    except Exception:
        return {}


def save_settings(project, game_dir):
    try:
        path = _settings_path(project)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'game': game_dir}, f, indent=1)        # (the folder only: never the key)
    except Exception:
        pass


def have_numpy():
    try:
        import numpy  # noqa: F401
        return True
    except Exception:
        return False


def ensure_numpy(log):
    """numpy for this Python; installs it with pip --user (once) if it is missing."""
    if have_numpy():
        return True
    log('numpy is not installed for this Python (%s): installing it now with "pip install --user numpy" (once; a '
        'minute or two)...' % sys.executable)

    def pip(args):
        p = subprocess.Popen([sys.executable, '-m'] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             universal_newlines=True, creationflags=NO_WINDOW)
        for line in p.stdout:
            line = line.rstrip()
            if line:
                log('  ' + line)
        return p.wait()
    rc = pip(['pip', 'install', '--user', '--disable-pip-version-check', 'numpy'])
    if rc != 0:
        log('pip did not work (exit %d): trying to set up pip first (ensurepip)...' % rc)
        pip(['ensurepip', '--user'])
        rc = pip(['pip', 'install', '--user', '--disable-pip-version-check', 'numpy'])
    try:
        import importlib
        import site
        user_site = site.getusersitepackages()
        if os.path.isdir(user_site) and user_site not in sys.path:
            site.addsitedir(user_site)
        importlib.invalidate_caches()
    except Exception:
        pass
    if have_numpy():
        log('numpy is installed.')
        return True
    log('numpy could not be installed (pip exit %d). Install it yourself: "%s" -m pip install --user numpy' % (rc, sys.executable))
    return False


def write_result(path, data):
    """The editor's hand-off file (written whole, then renamed into place)."""
    if not path:
        return
    data = dict(data, tool='Remake Importer ' + VERSION, time=time.strftime('%Y-%m-%d %H:%M:%S'))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, path)


def check(log=print, oodle_path=None):
    """What this Python has for the importer. True if it can import."""
    ok = True
    log('Remake Importer %s, Python %s (%s)' % (VERSION, sys.version.split()[0], sys.executable))
    log('numpy: %s' % ('yes' if have_numpy() else 'NO (the importer installs it on its first run)'))
    try:
        import tkinter  # noqa: F401
        log('tkinter (the window): yes')
    except Exception:
        log('tkinter (the window): no (use --console)')
    for cls in rp.aes_backends():
        try:
            probe = cls(rp._TEST_KEY)
            good = probe.decrypt(rp._TEST_CT) == rp._TEST_PT
            probe.close()
            log('AES %s: %s' % (cls.name, 'works' if good else 'WRONG RESULT'))
        except Exception as ex:
            log('AES %s: not available (%s)' % (cls.name, str(ex).splitlines()[0] if str(ex) else type(ex).__name__))
    try:
        oo = rp.Oodle(oodle_path)
        log('Oodle: %s (%s): its self-test decompressed correctly' % (oo.path, oo.symbol))
    except rp.PakError as ex:
        ok = False
        log('Oodle: %s' % ex)
    return ok


# ---------------------------------------------------------------------------------------------------------------------
# a run: the paks opened with the user's key, the character converted
# ---------------------------------------------------------------------------------------------------------------------

class Session(object):
    def __init__(self, game_dir, key_text, project, log=print, oodle_path=None, aes_backends=None):
        import remake_convert as rc
        self.rc = rc
        self.project = project
        key = rp.parse_key(key_text)
        aes = rp.make_aes(key, aes_backends)
        del key
        self.aes_name = aes.name
        self.oodle, self.oodle_error = None, None
        try:
            self.oodle = rp.Oodle(oodle_path)
        except rp.PakError as ex:
            self.oodle_error = str(ex)
        log('Reading the paks\' file lists (AES: %s)...' % aes.name)
        t0 = time.time()
        self.index = rp.GameIndex(game_dir, aes, self.oodle)
        self.characters = rc.list_characters(self.index, project=project)
        log('%d files in %d paks (%.0f s); %d character folders (Player, Enemy)' % (
            self.index.count, len(self.index.paks), time.time() - t0, len(self.characters)))

    def reload_oodle(self, oodle_path=None):
        self.oodle = rp.Oodle(oodle_path)
        self.index.oodle = self.oodle
        self.oodle_error = None

    def convert(self, character, log=print, progress=None, out_root=None, editor_root=None):
        if self.oodle is None:
            raise rp.PakError(self.oodle_error or 'no Oodle decompressor')
        conv = self.rc.Converter(self.index, character, self.project, log, out_root=out_root, editor_root=editor_root)
        return conv.run(progress)


def run_headless(game_dir, key_provider, character, project=DEFAULT_PROJECT, log=print, out_root=None, editor_root=None,
                 oodle_path=None, aes_backends=None, result=None):
    """No window: key_provider() returns the key text; character is a folder name (or a unique part of one)."""
    if not ensure_numpy(log):
        raise RuntimeError('numpy is needed')
    s = Session(game_dir, key_provider(), project, log, oodle_path, aes_backends)
    c = s.rc.find_character(s.characters, character)
    log('Character: %s (%s, models: %s)' % (c['folder'], c['category'], ', '.join(c['models'])))
    summary = s.convert(c, log, out_root=out_root, editor_root=editor_root)
    write_result(result, dict(ok=True, job=summary['job'], name=summary['name'], folder=c['folder'], summary=summary))
    return summary


def editor_command(job):
    return 'py "%s" "%s"' % (os.path.join(DEFAULT_PROJECT, 'Tools', 'RemakeMaterials', 'remake_character.py').replace('\\', '/'),
                             job.replace('\\', '/'))


# ---------------------------------------------------------------------------------------------------------------------
# console
# ---------------------------------------------------------------------------------------------------------------------

def console(args):
    """The same questions in the console. Started by the editor (--result) in a console window of its own: that window
    waits for Enter before it closes, so what happened can be read."""
    try:
        return _console(args)
    except KeyboardInterrupt:
        write_result(args.result, dict(ok=False, cancelled=True))
        return 1
    except Exception as ex:
        print('The importer stopped: %s\n%s' % (ex, traceback.format_exc()), flush=True)
        write_result(args.result, dict(ok=False, error=str(ex)))
        return 1
    finally:
        if os.name == 'nt' and args.result:
            try:
                input('Press Enter to close this window.')
            except Exception:
                pass


def _console(args):
    import getpass
    project = args.project
    log = lambda t: print(t, flush=True)
    log('%s (Remake Importer %s)' % (TITLE, VERSION))
    if not ensure_numpy(log):
        write_result(args.result, dict(ok=False, error='numpy could not be installed for %s' % sys.executable))
        return 1
    game = args.game or load_settings(project).get('game') or DEFAULT_GAME
    answer = input('FINAL FANTASY VII REMAKE folder [%s]: ' % game).strip().strip('"')
    game = answer or game
    while True:
        try:
            key_text = getpass.getpass('Your FINAL FANTASY VII REMAKE AES key (hex; not shown, not saved): ')
            s = Session(game, key_text, project, log)
            del key_text
            break
        except rp.KeyError_ as ex:
            log('That key does not work: %s' % ex)
        except rp.PakError as ex:
            log(str(ex))
            write_result(args.result, dict(ok=False, error=str(ex)))
            return 1
    save_settings(project, game)
    chars = s.characters
    if args.list:
        for c in chars:
            log('%-46s %-7s %s%s' % (c['folder'], c['category'], ', '.join(c['models'][:6]), '  [in the project]' if c['imported'] else ''))
        return 0
    if s.oodle_error:
        log(s.oodle_error)
        if os.name == 'nt' and os.path.isfile(BUILD_OOZ) and input('Build ooz.dll now (Visual Studio 2022 C++)? [y/N] ').strip().lower() == 'y':
            subprocess.call(['cmd', '/c', BUILD_OOZ, 'nopause'])
            try:
                s.reload_oodle()
            except rp.PakError as ex:
                log(str(ex))
                write_result(args.result, dict(ok=False, error=str(ex)))
                return 1
        else:
            write_result(args.result, dict(ok=False, error=s.oodle_error))
            return 1
    c = None
    if args.character:
        c = s.rc.find_character(chars, args.character)
    while c is None:
        text = input('Character (part of a folder name, e.g. Tifa, PC0003, Sephiroth; empty: stop): ').strip()
        if not text:
            write_result(args.result, dict(ok=False, cancelled=True))
            return 0
        hits = [x for x in chars if text.lower() in x['folder'].lower()]
        if not hits:
            log('  no folder has "%s"' % text)
            continue
        for k, x in enumerate(hits[:40]):
            log('  %2d  %-46s %-7s %d files in Model%s' % (k + 1, x['folder'], x['category'], len(x['models']), '  [in the project]' if x['imported'] else ''))
        pick = input('Number (1-%d): ' % min(40, len(hits))).strip()
        if pick.isdigit() and 1 <= int(pick) <= min(40, len(hits)):
            c = hits[int(pick) - 1]
    if c['imported'] and not args.character:
        if input('%s is already in the project: import it again (in place)? [y/N] ' % c['folder']).strip().lower() != 'y':
            write_result(args.result, dict(ok=False, cancelled=True))
            return 0
    try:
        summary = s.convert(c, log)
    except Exception as ex:
        log('The conversion failed: %s' % ex)
        log(traceback.format_exc())
        write_result(args.result, dict(ok=False, error=str(ex), folder=c['folder']))
        return 1
    write_result(args.result, dict(ok=True, job=summary['job'], name=summary['name'], folder=c['folder'], summary=summary))
    if args.result:
        log('\nDone: the End editor imports %s now.' % summary['name'])
    else:
        log('\nDone. In the End editor (Output Log, Cmd):\n  ' + editor_command(summary['job']))
    return 0


# ---------------------------------------------------------------------------------------------------------------------
# the window
# ---------------------------------------------------------------------------------------------------------------------

class App(object):
    def __init__(self, args):
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
        self.tk, self.ttk, self.filedialog, self.messagebox = tk, ttk, filedialog, messagebox
        self.args = args
        self.project = args.project
        self.q = queue.Queue()
        self.session = None
        self.busy = False
        self.finished = None                    # the result written for the editor
        self.shown = []
        self.root = root = tk.Tk()
        root.title(TITLE)
        root.geometry('860x700')
        root.minsize(680, 520)
        frm = ttk.Frame(root, padding=10)
        frm.pack(fill='both', expand=True)
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text='FINAL FANTASY VII REMAKE folder').grid(row=0, column=0, sticky='w')
        self.game = tk.StringVar(value=args.game or load_settings(self.project).get('game') or DEFAULT_GAME)
        self.game_entry = ttk.Entry(frm, textvariable=self.game)
        self.game_entry.grid(row=0, column=1, sticky='ew', padx=6)
        self.browse_btn = ttk.Button(frm, text='Browse...', command=self.browse)
        self.browse_btn.grid(row=0, column=2, sticky='ew')

        ttk.Label(frm, text='Your AES key (hex)').grid(row=1, column=0, sticky='w', pady=(8, 0))
        self.key = ttk.Entry(frm, show='\u2022')          # (no Tk variable holds it)
        self.key.grid(row=1, column=1, sticky='ew', padx=6, pady=(8, 0))
        self.key.bind('<Return>', lambda e: self.load())
        self.load_btn = ttk.Button(frm, text='Load characters', command=self.load)
        self.load_btn.grid(row=1, column=2, sticky='ew', pady=(8, 0))
        self.key_note = ttk.Label(frm, text='FINAL FANTASY VII REMAKE\'s pak key: kept in memory for this run only, never saved '
                                  'or written anywhere.', foreground='#666666')
        self.key_note.grid(row=2, column=1, columnspan=2, sticky='w', padx=6)

        ttk.Label(frm, text='Find').grid(row=3, column=0, sticky='w', pady=(10, 0))
        self.filter = tk.StringVar()
        self.filter.trace_add('write', lambda *a: self.refill())
        self.filter_entry = ttk.Entry(frm, textvariable=self.filter)
        self.filter_entry.grid(row=3, column=1, sticky='ew', padx=6, pady=(10, 0))
        ttk.Label(frm, text='(e.g. Tifa, PC0003, Enemy)', foreground='#666666').grid(row=3, column=2, sticky='w', pady=(10, 0))

        box = ttk.Frame(frm)
        box.grid(row=4, column=0, columnspan=3, sticky='nsew', pady=(6, 0))
        frm.rowconfigure(4, weight=3)
        box.columnconfigure(0, weight=1)
        box.rowconfigure(0, weight=1)
        self.listbox = tk.Listbox(box, height=12, exportselection=False, activestyle='dotbox', font=('Consolas', 10))
        self.listbox.grid(row=0, column=0, sticky='nsew')
        sb = ttk.Scrollbar(box, orient='vertical', command=self.listbox.yview)
        sb.grid(row=0, column=1, sticky='ns')
        self.listbox.configure(yscrollcommand=sb.set)
        self.listbox.bind('<<ListboxSelect>>', lambda e: self.on_select())
        self.listbox.bind('<Double-Button-1>', lambda e: self.start_import())

        self.info = ttk.Label(frm, text='Type your key and press Load characters.', wraplength=820, justify='left')
        self.info.grid(row=5, column=0, columnspan=3, sticky='w', pady=(6, 0))

        bar = ttk.Frame(frm)
        bar.grid(row=6, column=0, columnspan=3, sticky='ew', pady=(8, 0))
        bar.columnconfigure(1, weight=1)
        self.import_btn = ttk.Button(bar, text='Import', command=self.start_import, state='disabled')
        self.import_btn.grid(row=0, column=0, sticky='w')
        self.progress = ttk.Progressbar(bar, mode='determinate', maximum=1000)
        self.progress.grid(row=0, column=1, sticky='ew', padx=8)
        self.ooz_btn = ttk.Button(bar, text='Build ooz.dll', command=self.build_ooz)
        self.close_btn = ttk.Button(bar, text='Close', command=self.close)
        self.close_btn.grid(row=0, column=3, sticky='e')
        self.status = ttk.Label(frm, text='', foreground='#444444')
        self.status.grid(row=7, column=0, columnspan=3, sticky='w')

        logf = ttk.Frame(frm)
        logf.grid(row=8, column=0, columnspan=3, sticky='nsew', pady=(6, 0))
        frm.rowconfigure(8, weight=2)
        logf.columnconfigure(0, weight=1)
        logf.rowconfigure(0, weight=1)
        self.logw = tk.Text(logf, height=10, wrap='word', state='disabled', font=('Consolas', 9))
        self.logw.grid(row=0, column=0, sticky='nsew')
        sb2 = ttk.Scrollbar(logf, orient='vertical', command=self.logw.yview)
        sb2.grid(row=0, column=1, sticky='ns')
        self.logw.configure(yscrollcommand=sb2.set)

        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(100, self.poll)
        try:                                     # in front of the editor that started it
            root.lift()
            root.attributes('-topmost', True)
            root.after(800, lambda: root.attributes('-topmost', False))
            root.focus_force()
            self.key.focus_set()
        except Exception:
            pass
        self.set_busy(True, 'Checking numpy...')
        threading.Thread(target=self._startup, daemon=True).start()

    # (worker threads talk to the window only through the queue)
    def post(self, *item):
        self.q.put(item)

    def log(self, text):
        self.post('log', text)

    def poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                getattr(self, '_on_' + item[0])(*item[1:])
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def _on_log(self, text):
        self.logw.configure(state='normal')
        self.logw.insert('end', text + '\n')
        self.logw.see('end')
        self.logw.configure(state='disabled')

    def _on_progress(self, frac, text):
        self.progress['value'] = int(1000 * max(0.0, min(1.0, frac)))
        self.status.configure(text=text)

    def _on_idle(self, text):
        self.set_busy(False, text)

    def _on_loaded(self, session):
        self.session = session
        self.key.configure(state='normal')              # (a disabled entry ignores delete)
        self.key.delete(0, 'end')
        self.key.configure(state='disabled')
        self.load_btn.configure(state='disabled')
        self.game_entry.configure(state='disabled')
        self.browse_btn.configure(state='disabled')
        self.key_note.configure(text='Key accepted (%s): in memory for this run only.' % session.aes_name)
        save_settings(self.project, self.game.get())
        self.refill()
        self.filter_entry.focus_set()
        if session.oodle_error:
            self._oodle_missing()
        self.set_busy(False, 'Pick a character and press Import (or double-click it).')

    def _oodle_missing(self):
        self.log('The Oodle decompressor is missing: %s' % self.session.oodle_error)
        if os.name == 'nt' and os.path.isfile(BUILD_OOZ):
            self.ooz_btn.grid(row=0, column=2, sticky='e', padx=(0, 8))
            self.log('Press "Build ooz.dll" (once; it needs Visual Studio 2022\'s C++ tools), then Import.')

    def _on_ooz(self, ok):
        if ok:
            self.ooz_btn.grid_remove()
        self.set_busy(False, 'ooz.dll is ready: pick a character and press Import.' if ok else 'ooz.dll was not built (see above).')

    def _on_done(self, summary, character):
        self.finished = dict(ok=True, job=summary['job'], name=summary['name'], folder=character['folder'], summary=summary)
        write_result(self.args.result, self.finished)
        self.progress['value'] = 1000
        lines = ['', 'Done: %s' % summary['name'],
                 '  %d textures, %d material instances, %d models, %d Bonamik' % (summary['textures'], summary['instances'],
                                                                                 len(summary['models']), len(summary['bonamik'])),
                 '  job: %s' % summary['job']]
        if summary['warnings']:
            lines.append('  %d notes (above, and in the editor\'s summary)' % len(summary['warnings']))
        if self.args.result:
            lines.append('The End editor imports it now (its window says when it is done). You can close this window.')
            self.import_btn.configure(state='disabled')
            self.set_busy(False, 'Done: the End editor imports %s now.' % summary['name'], keep_import_off=True)
        else:
            lines.append('In the End editor (Output Log, Cmd):  ' + editor_command(summary['job']))
            self.set_busy(False, 'Done.')
        for line in lines:
            self._on_log(line)

    def _on_failed(self, text):
        self._on_log(text)
        self.set_busy(False, 'Stopped: see the log.')

    def _on_keyfail(self, text):
        self._on_log(text)
        self.set_busy(False, 'The key or the folder did not work.')
        self.key.configure(state='normal')
        self.key.select_range(0, 'end')
        self.key.focus_set()

    def set_busy(self, busy, text='', keep_import_off=False):
        self.busy = busy
        self.status.configure(text=text)
        if busy:
            self.progress.configure(mode='indeterminate')
            self.progress.start(15)
        else:
            self.progress.stop()
            self.progress.configure(mode='determinate')
        loaded = self.session is not None
        for w in (self.load_btn, self.browse_btn):
            w.configure(state='disabled' if busy or loaded else 'normal')
        self.import_btn.configure(state='normal' if (loaded and not busy and not keep_import_off and not self.finished
                                                     and self.selected()) else 'disabled')

    # the steps
    def _startup(self):
        ensure_numpy(self.log)
        self.post('idle', 'Type your key and press Load characters.' if have_numpy() else
                  'numpy is missing: the importer cannot convert anything (see the log).')

    def browse(self):
        d = self.filedialog.askdirectory(title='The FINAL FANTASY VII REMAKE folder (with ff7remake.exe)',
                                         initialdir=self.game.get() if os.path.isdir(self.game.get()) else None)
        if d:
            self.game.set(os.path.normpath(d))

    def load(self):
        if self.busy or self.session is not None:
            return
        if not have_numpy():
            self.messagebox.showerror(TITLE, 'numpy is not installed for this Python (see the log).')
            return
        key_text = self.key.get()
        game = self.game.get().strip().strip('"')
        try:
            rp.parse_key(key_text)
        except rp.KeyError_ as ex:
            self.messagebox.showerror(TITLE, 'The key: %s.' % ex)
            return
        self.set_busy(True, 'Opening the paks...')
        self.key.configure(state='disabled')
        threading.Thread(target=self._load, args=(game, key_text), daemon=True).start()
        del key_text

    def _load(self, game, key_text):
        try:
            s = Session(game, key_text, self.project, self.log)
            del key_text
            self.post('loaded', s)
        except rp.KeyError_ as ex:
            self.post('keyfail', 'The key does not open the paks: %s' % ex)
        except rp.PakError as ex:
            self.post('keyfail', str(ex))
        except Exception:
            self.post('keyfail', 'Opening the paks failed:\n' + traceback.format_exc())

    def visible(self):
        if not self.session:
            return []
        t = self.filter.get().strip().lower()
        out = []
        for c in self.session.characters:
            if not t or all(w in (c['folder'] + ' ' + c['category']).lower() for w in t.split()):
                out.append(c)
        return out

    def refill(self):
        self.shown = self.visible()
        self.listbox.delete(0, 'end')
        for c in self.shown:
            n = len(c['models'])
            self.listbox.insert('end', '%-44s %-6s %3d file%s in Model%s' % (c['folder'], c['category'], n, '' if n == 1 else 's',
                                                                          '   [in the project]' if c['imported'] else ''))
        if len(self.shown) == 1:
            self.listbox.selection_set(0)
        self.on_select()

    def selected(self):
        sel = self.listbox.curselection()
        return self.shown[sel[0]] if sel and sel[0] < len(self.shown) else None

    def on_select(self):
        c = self.selected()
        if c:
            self.info.configure(text='%s  (%s)  ->  %s\nModel folder: %s%s' % (
                c['folder'], c['category'], c['game_path'], ', '.join(c['models']),
                '\nAlready in the project: importing it again replaces it in place.' if c['imported'] else ''))
        elif self.session:
            self.info.configure(text='%d of %d character folders shown.' % (len(self.shown), len(self.session.characters)))
        if not self.busy:
            self.set_busy(False, self.status.cget('text'), keep_import_off=bool(self.finished))

    def start_import(self):
        c = self.selected()
        if self.busy or not c or self.finished:
            return
        if self.session.oodle is None:
            self.messagebox.showinfo(TITLE, 'The Oodle decompressor (ooz.dll) is not built yet.\n\nPress "Build ooz.dll" (once), '
                                     'or run build_ooz.cmd in\n%s' % HERE)
            return
        if c['imported'] and not self.messagebox.askyesno(TITLE, '%s is already in the project.\n\nImport it again? Its textures, '
                                                          'instances, models and Bonamik are replaced in place.' % c['folder']):
            return
        self.set_busy(True, 'Importing %s...' % c['folder'])
        self.progress.stop()
        self.progress.configure(mode='determinate', value=0)
        self._on_log('')
        threading.Thread(target=self._convert, args=(c,), daemon=True).start()

    def _convert(self, c):
        try:
            summary = self.session.convert(c, self.log, lambda f, t: self.post('progress', f, t))
            self.post('done', summary, c)
        except Exception as ex:
            self.post('failed', 'The conversion of %s failed: %s\n%s' % (c['folder'], ex, traceback.format_exc()))

    def build_ooz(self):
        if self.busy:
            return
        self.set_busy(True, 'Building ooz.dll (a minute)...')
        threading.Thread(target=self._build_ooz, daemon=True).start()

    def _build_ooz(self):
        ok = False
        try:
            p = subprocess.Popen(['cmd', '/c', BUILD_OOZ, 'nopause'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 universal_newlines=True, creationflags=NO_WINDOW, cwd=HERE)
            for line in p.stdout:
                if line.strip():
                    self.log('  ' + line.rstrip())
            p.wait()
            self.session.reload_oodle()
            self.log('ooz.dll works.')
            ok = True
        except Exception as ex:
            self.log('ooz.dll: %s' % ex)
        self.post('ooz', ok)

    def close(self):
        if self.busy and not self.messagebox.askyesno(TITLE, 'The importer is still working. Stop and close?'):
            return
        if self.finished is None:
            write_result(self.args.result, dict(ok=False, cancelled=True))
        self.session = None
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# ---------------------------------------------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=TITLE + ' (Remake Importer %s). Your AES key is asked for at run time; it '
                                 'cannot be passed in.' % VERSION)
    ap.add_argument('--game', help='the FINAL FANTASY VII REMAKE folder (default: the last one used, or the Steam one)')
    ap.add_argument('--project', default=DEFAULT_PROJECT, help='the End project folder (default: %(default)s)')
    ap.add_argument('--result', help='(the editor\'s menu entry) where to write what was made, for the editor to import')
    ap.add_argument('--console', action='store_true', help='ask in the console instead of a window')
    ap.add_argument('--list', action='store_true', help='list the character folders (console)')
    ap.add_argument('--character', help='convert this character folder (console)')
    ap.add_argument('--check', action='store_true', help='what this Python has for the importer')
    args = ap.parse_args(argv)
    args.project = os.path.abspath(args.project)
    if args.check:
        return 0 if check() else 1
    if args.console or args.list or args.character:
        return console(args)
    try:
        import tkinter  # noqa: F401
    except Exception:
        print('No tkinter for this Python: asking in the console instead.')
        return console(args)
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    try:
        App(args).run()
    except Exception:
        write_result(args.result, dict(ok=False, error='the window failed:\n' + traceback.format_exc()))
        raise
    return 0


if __name__ == '__main__':
    sys.exit(main())
