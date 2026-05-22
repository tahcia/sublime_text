import sublime
import sublime_plugin
import threading
import time
import json
import os
try:
    from .tahcia_client import TahciaClient
except (ImportError, ValueError, SystemError):
    from tahcia_client import TahciaClient

class ProgressBar:
    def __init__(self, message):
        self.message = message
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._animate)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)
        sublime.status_message("")

    def _animate(self):
        chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0
        while not self.stop_event.is_set():
            sublime.status_message("Tahcia: {} {}".format(chars[i % len(chars)], self.message))
            i += 1
            time.sleep(0.1)

def _get_target_path(kwargs, window):
    """
    Prioritizes the absolute side menu paths array provided by the click context.
    Falls back to the editor view context only if the sidebar wasn't used.
    """
    p = kwargs.get("paths")
    if p:
        return p[0]
    v = window.active_view()
    return v.file_name() if v else None

def _find_config_upwards(start_path):
    """
    Replicates VS Code's findConfigUpwards logic.
    Recursively checks parents up to the root folder.
    """
    if not start_path:
        return None, {}
    
    curr = start_path if os.path.isdir(start_path) else os.path.dirname(start_path)
    while True:
        cfg = os.path.join(curr, "tahcia-config.json")
        if os.path.exists(cfg):
            try:
                with open(cfg, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "api_key" in data:
                        return curr, data
            except:
                pass # Continue searching upward if JSON is unreadable
        
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent
    return None, {}

def _has_valid_config(start_path):
    tdir, _ = _find_config_upwards(start_path)
    return tdir is not None

def get_tahcia_config(fallback_path=None):
    """
    Multi-tier configuration scanner mirroring the VS Code hierarchy.
    """
    # Tier 0: Direct explicit targeted context item (sidebar selection path)
    if fallback_path:
        tdir, data = _find_config_upwards(fallback_path)
        if tdir:
            return tdir, data

    window = sublime.active_window()
    if not window:
        return None, {}

    # Tier 1: Fallback via currently active/focused documentation window 
    v = window.active_view()
    if v and v.file_name():
        tdir, data = _find_config_upwards(v.file_name())
        if tdir:
            return tdir, data
        
    # Tier 2: Search multi-root workspaces folder trees
    for d in window.folders():
        tdir, data = _find_config_upwards(d)
        if tdir:
            return tdir, data

    return None, {}

def run_async(func, on_success, on_error, loading_msg):
    progress = ProgressBar(loading_msg)
    progress.start()
    def worker():
        try:
            res = func()
            sublime.set_timeout(lambda: on_success(res), 0)
        except Exception as e:
            sublime.set_timeout(lambda: on_error(str(e)), 0)
        finally:
            progress.stop()
    threading.Thread(target=worker, daemon=True).start()

class TahciaScriptDownloadCommand(sublime_plugin.WindowCommand):
    def is_visible(self, **kwargs):
        p = _get_target_path(kwargs, self.window)
        if not p or os.path.isdir(p) or not p.endswith(".tahcia.json"):
            return False
        return _has_valid_config(p)

    def run(self, name=None, **kwargs):
        p = _get_target_path(kwargs, self.window)
        if name:
            self.download_and_open(name, p)
            return
        tdir, cfg = get_tahcia_config(fallback_path=p)
        key = cfg.get("api_key", "").strip() if cfg else None
        if not key or not tdir or not p:
            return
        self.download_and_open(os.path.basename(p), p)

    def download_and_open(self, name, target_path):
        tdir, cfg = get_tahcia_config(fallback_path=target_path)
        key = cfg.get("api_key", "").strip() if cfg else None
        if not key or not tdir:
            return
        def do_dl(): return TahciaClient(key).download_script(name)
        def on_ok(res):
            fp = os.path.join(tdir, name)
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(res)
            self.window.open_file(fp)
        run_async(do_dl, on_ok, lambda e: sublime.error_message(e), "Downloading...")

class TahciaScriptUploadCommand(sublime_plugin.WindowCommand):
    def is_visible(self, **kwargs):
        p = _get_target_path(kwargs, self.window)
        if not p or os.path.isdir(p) or not p.endswith(".tahcia.json"):
            return False
        return _has_valid_config(p)

    def run(self, **kwargs):
        p = _get_target_path(kwargs, self.window)
        tdir, cfg = get_tahcia_config(fallback_path=p)
        key = cfg.get("api_key", "").strip() if cfg else None
        if not key or not tdir or not p:
            return

        bn = os.path.basename(p)
        v = self.window.active_view()
        if v and v.file_name() == p:
            code = v.substr(sublime.Region(0, v.size()))
        else:
            with open(p, 'r', encoding='utf-8') as f:
                code = f.read()

        try:
            json.loads(code)
        except ValueError as je:
            sublime.error_message("Tahcia: Invalid JSON!\n\n{}".format(je))
            return

        def do_ul(): return TahciaClient(key).upload_script(bn, code)
        def on_ok(res):
            sublime.status_message("Tahcia: Uploaded {}!".format(bn))
            if isinstance(res, dict) and "name" in res:
                sn = res["name"] if res["name"].endswith(".tahcia.json") else res["name"] + ".tahcia.json"
                if sn != bn:
                    sublime.set_timeout(lambda: self.rename_file(p, sn), 0)
        run_async(do_ul, on_ok, lambda e: sublime.error_message(e), "Uploading...")

    def rename_file(self, old, new_bn):
        new_fp = os.path.join(os.path.dirname(old), new_bn)
        if os.path.exists(new_fp): os.remove(new_fp)
        os.rename(old, new_fp)
        v = self.window.active_view()
        if v and v.file_name() == old: v.retarget(new_fp)

class TahciaScriptDeleteCommand(sublime_plugin.WindowCommand):
    def is_visible(self, **kwargs):
        p = _get_target_path(kwargs, self.window)
        if not p or os.path.isdir(p) or not p.endswith(".tahcia.json"):
            return False
        return _has_valid_config(p)

    def run(self, name=None, **kwargs):
        p = _get_target_path(kwargs, self.window)
        if name:
            if sublime.ok_cancel_dialog("Permanently delete '{}'?".format(name), "Delete"):
                self.delete_script(name, p)
            return

        tdir, cfg = get_tahcia_config(fallback_path=p)
        key = cfg.get("api_key", "").strip() if cfg else None
        if not key or not p: return

        if sublime.ok_cancel_dialog("Permanently delete '{}'?".format(os.path.basename(p)), "Delete"):
            self.delete_script(os.path.basename(p), p)

    def delete_script(self, name, target_path):
        _, cfg = get_tahcia_config(fallback_path=target_path)
        key = cfg.get("api_key", "").strip() if cfg else None
        if key: run_async(lambda: TahciaClient(key).delete_script(name), lambda r: sublime.message_dialog("Deleted!"), lambda e: sublime.error_message(e), "Deleting...")

class TahciaScriptBrowseCommand(sublime_plugin.WindowCommand):
    def is_visible(self, **kwargs):
        p = _get_target_path(kwargs, self.window)
        if not p:
            return bool(self.window.folders() and _has_valid_config(self.window.folders()[0]))
        return _has_valid_config(p)

    def run(self, **kwargs):
        p = _get_target_path(kwargs, self.window)
        _, cfg = get_tahcia_config(fallback_path=p)
        key = cfg.get("api_key", "").strip() if cfg else None
        if not key: return

        def on_list(scripts):
            if not scripts: return
            def on_sel(idx):
                if idx != -1:
                    opts = ["Download and Open", "Delete", "Cancel"]
                    def on_opt(oidx):
                        if oidx == 0: self.window.run_command("tahcia_script_download", {"name": scripts[idx], "paths": [p] if p else []})
                        elif oidx == 1: self.window.run_command("tahcia_script_delete", {"name": scripts[idx], "paths": [p] if p else []})
                    self.window.show_quick_panel(opts, on_opt)
            self.window.show_quick_panel(scripts, on_sel)
        run_async(TahciaClient(key).list_scripts, on_list, lambda e: sublime.error_message(e), "Listing...")

class TahciaScriptInitCommand(sublime_plugin.WindowCommand):
    def is_visible(self, **kwargs):
        p = _get_target_path(kwargs, self.window)
        if not p:
            return bool(self.window.folders() and not _has_valid_config(self.window.folders()[0]))
        if os.path.isfile(p) and not p.endswith(".tahcia.json"):
            return False
        return not _has_valid_config(p)

    def run(self, **kwargs):
        p = _get_target_path(kwargs, self.window)
        tdir = p if (p and os.path.isdir(p)) else (os.path.dirname(p) if p else None)
        if not tdir:
            tdir = self.window.folders()[0] if self.window.folders() else None
        
        if not tdir: return
        cfg_path = os.path.join(tdir, "tahcia-config.json")
        try:
            with open(cfg_path, 'w', encoding='utf-8') as f:
                json.dump({"api_key": "PASTE_YOUR_TAHCIA_API_KEY_HERE", "uploadOnSave": True}, f, indent=4)
            self.window.open_file(cfg_path)
        except Exception as e:
            sublime.error_message(str(e))

class TahciaEventListener(sublime_plugin.EventListener):
    def on_post_save_async(self, view):
        filename = view.file_name()
        if not filename or not filename.endswith(".tahcia.json"):
            return
        tdir, cfg = get_tahcia_config(fallback_path=filename)
        if tdir and cfg.get("uploadOnSave", True):
            if os.path.realpath(filename).startswith(os.path.realpath(tdir)):
                view.window().run_command("tahcia_script_upload", {"paths": [filename]})