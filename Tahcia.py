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

def get_tahcia_config(fallback_path=None):
    window = sublime.active_window()
    if not window:
        return None, {}

    folders = window.folders()
    search_dirs = []

    # 0. If a specific path was targeted (via right-click sidebar kwargs)
    if fallback_path:
        if os.path.isdir(fallback_path):
            search_dirs.append(fallback_path)
        else:
            search_dirs.append(os.path.dirname(fallback_path))    
    # 1. Scan open window folders
    for folder in folders:
        config_path = os.path.join(folder, "tahcia-config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "api_key" in data:
                        return folder, data
            except Exception:
                pass

    # 2. Scan active view's folder
    view = window.active_view()
    if view:
        file_path = view.file_name()
        if file_path:
            dir_path = os.path.dirname(file_path)
            config_path = os.path.join(dir_path, "tahcia-config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, dict) and "api_key" in data:
                            return dir_path, data
                except Exception:
                    pass

    return None, {}

def run_async(func, on_success, on_error, loading_msg):
    progress = ProgressBar(loading_msg)
    progress.start()

    def worker():
        try:
            result = func()
            sublime.set_timeout(lambda: on_success(result), 0)
        except Exception as e:
            sublime.set_timeout(lambda: on_error(str(e)), 0)
        finally:
            progress.stop()

    threading.Thread(target=worker, daemon=True).start()



class TahciaScriptDownloadCommand(sublime_plugin.WindowCommand):
    def run(self, name=None, **kwargs):
        print (name);
        if name:
            self.download_and_open(name)
            return

        clicked_path = kwargs["paths"][0] if "paths" in kwargs and kwargs["paths"] else None
        
        # Pass that specific target path directly to the config finder
        tahcia_dir, config = get_tahcia_config(fallback_path=clicked_path)

        api_key = config.get("api_key", "").strip() if config else None
        if not api_key or not tahcia_dir:
            sublime.error_message("Tahcia: 'tahcia-config.json' was not found in any open folders.\n\nPlease open a folder containing 'tahcia-config.json' with your 'api_key' to download scripts.")
            return

        view = self.window.active_view()
        
        # If right-clicked a specific file from the sidebar, find its open view or use disk path
        if clicked_path and os.path.isfile(clicked_path):
            filename = clicked_path
        elif view:
            filename = view.file_name()
        else:
            filename = None

        if not filename:
            sublime.error_message("Tahcia: Current view must be saved to disk before uploading.")
            return

        basename = os.path.basename(filename)
        if not basename.endswith(".tahcia.json"):
            sublime.error_message("Tahcia: Filename must end with '.tahcia.json' to be uploaded.")
            return

        self.download_and_open(basename)


    def download_and_open(self, name):

        tahcia_dir, config = get_tahcia_config()

        api_key = config.get("api_key", "").strip() if config else None
        if not api_key or not tahcia_dir:
            sublime.error_message("Tahcia: 'tahcia-config.json' was not found.")
            return

        client = TahciaClient(api_key)
        
        def do_download():
            return client.download_script(name)

        def on_download_success(content):
            filepath = os.path.join(tahcia_dir, name)
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.window.open_file(filepath)
                sublime.status_message("Tahcia: Downloaded and opened {}".format(name))
            except Exception as io_err:
                sublime.error_message("Tahcia: Failed to write file locally: {}".format(io_err))

        def on_error(err):
            sublime.error_message("Tahcia Error: {}".format(err))

        run_async(do_download, on_download_success, on_error, "Downloading {}...".format(name))

class TahciaScriptUploadCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        # Extract the exact path clicked in the sidebar if it exists
        clicked_path = kwargs["paths"][0] if "paths" in kwargs and kwargs["paths"] else None
        
        # Pass that specific target path directly to the config finder
        tahcia_dir, config = get_tahcia_config(fallback_path=clicked_path)
        
        api_key = config.get("api_key", "").strip() if config else None
        if not api_key or not tahcia_dir:
            sublime.error_message("Tahcia: 'tahcia-config.json' was not found.\n\nPlease open a folder containing 'tahcia-config.json' with your 'api_key' to upload scripts.")
            return

        # Figure out which file buffer to read
        view = self.window.active_view()
        
        # If right-clicked a specific file from the sidebar, find its open view or use disk path
        if clicked_path and os.path.isfile(clicked_path):
            filename = clicked_path
        elif view:
            filename = view.file_name()
        else:
            filename = None

        if not filename:
            sublime.error_message("Tahcia: Current view must be saved to disk before uploading.")
            return

        basename = os.path.basename(filename)
        if not basename.endswith(".tahcia.json"):
            sublime.error_message("Tahcia: Filename must end with '.tahcia.json' to be uploaded.")
            return

        # Grab the script code text buffer
        if view and view.file_name() == filename:
            region = sublime.Region(0, view.size())
            code = view.substr(region)
        else:
            # If the file isn't actively focused/open in an editor tab, read it off the disk
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    code = f.read()
            except Exception as e:
                sublime.error_message("Tahcia: Failed to read file context.\n\nDetails: {}".format(e))
                return

        client = TahciaClient(api_key)

        try:
            json.loads(code)
        except ValueError as json_err:
            error_msg = (
                "Tahcia: Invalid JSON detected!\n\n"
                "Upload aborted to protect your remote script.\n\n"
                "Details: {}".format(json_err)
            )
            sublime.error_message(error_msg)
            return

        def do_upload():
            return client.upload_script(basename, code)

        def on_upload_success(res):
            sublime.status_message("Tahcia: Successfully uploaded '{}'!".format(basename))
            if isinstance(res, dict) and "name" in res:
                server_name = res["name"]
                sublime.status_message("TahciaCurrent Name '{}'!".format(server_name))
                if server_name != basename:
                    sublime.set_timeout(lambda: self.rename_local_file(filename, server_name), 0)

        def on_error(err):
            sublime.error_message("Tahcia Error: {}".format(err))

        run_async(do_upload, on_upload_success, on_error, "Uploading {}...".format(basename))


    def rename_local_file(self, old_filepath, new_basename):
        # Ensure the server name keeps the required suffix
        if not new_basename.endswith(".tahcia.json"):
            new_basename += ".tahcia.json"

        directory = os.path.dirname(old_filepath)
        new_filepath = os.path.join(directory, new_basename)

        if old_filepath == new_filepath:
            return

        try:
            # If target filename already exists on disk, clear it or notify user
            if os.path.exists(new_filepath):
                os.remove(new_filepath)

            os.rename(old_filepath, new_filepath)
            
            # Point Sublime's current tab buffer context to the new file path
            self.view.retarget(new_filepath)
            sublime.status_message("Tahcia: Updated local filename to '{}'".format(new_basename))
        except Exception as e:
            print("[Tahcia] Local file rename failed: {}".format(e))

class TahciaScriptDeleteCommand(sublime_plugin.WindowCommand):
    def run(self, name=None, **kwargs):
        if name:
            confirm = sublime.ok_cancel_dialog(
                "Are you sure you want to permanently delete '{}' from the Tahcia server?".format(name),
                "Delete"
            )
            if confirm:
                self.delete_script(name)
            return


        clicked_path = kwargs["paths"][0] if "paths" in kwargs and kwargs["paths"] else None
        tahcia_dir, config = get_tahcia_config(fallback_path=clicked_path)

        api_key = config.get("api_key", "").strip() if config else None
        if not api_key or not tahcia_dir:
            sublime.error_message("Tahcia: 'tahcia-config.json' was not found in any open folders.\n\nPlease open a folder containing 'tahcia-config.json' with your 'api_key' to delete scripts.")
            return

        client = TahciaClient(api_key)

        def on_list_success(scripts):
            if not scripts:
                sublime.message_dialog("Tahcia: No remote scripts found to delete.")
                return

            def on_select(index):
                if index == -1:
                    return
                selected_name = scripts[index]
                
                confirm = sublime.ok_cancel_dialog(
                    "Are you sure you want to permanently delete '{}' from the Tahcia server?".format(selected_name),
                    "Delete"
                )
                if confirm:
                    self.delete_script(selected_name)

            self.window.show_quick_panel(scripts, on_select)

        def on_error(err):
            sublime.error_message("Tahcia Error: {}".format(err))

        run_async(client.list_scripts, on_list_success, on_error, "Fetching remote scripts list...")

    def delete_script(self, name):
        tahcia_dir, config = get_tahcia_config()
        api_key = config.get("api_key", "").strip() if config else None
        if not api_key:
            return

        client = TahciaClient(api_key)

        def do_delete():
            return client.delete_script(name)

        def on_delete_success(res):
            sublime.message_dialog("Tahcia: Successfully deleted '{}' from the server.".format(name))

        def on_error(err):
            sublime.error_message("Tahcia Error: {}".format(err))

        run_async(do_delete, on_delete_success, on_error, "Deleting {}...".format(name))

class TahciaScriptBrowseCommand(sublime_plugin.WindowCommand):
    def run(self):
        tahcia_dir, config = get_tahcia_config()
        api_key = config.get("api_key", "").strip() if config else None
        if not api_key or not tahcia_dir:
            sublime.error_message("Tahcia: 'tahcia-config.json' was not found in any open folders.\n\nPlease open a folder containing 'tahcia-config.json' with your 'api_key' to browse scripts.")
            return

        client = TahciaClient(api_key)

        def on_list_success(scripts):
            if not scripts:
                sublime.message_dialog("Tahcia: No remote scripts found.")
                return

            def on_select(index):
                if index == -1:
                    return
                selected_name = scripts[index]
                self.show_actions(selected_name)

            self.window.show_quick_panel(scripts, on_select)

        def on_error(err):
            sublime.error_message("Tahcia Error: {}".format(err))

        run_async(client.list_scripts, on_list_success, on_error, "Fetching remote scripts list...")

    def show_actions(self, name):
        actions = ["Download and Open Script", "Delete Script", "Cancel"]

        def on_select(index):
            if index == 0:
                self.window.run_command("tahcia_script_download", {"name": name})
            elif index == 1:
                self.window.run_command("tahcia_script_delete", {"name": name})

        self.window.show_quick_panel(actions, on_select)

class TahciaScriptInitCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        # 1. Sidebar right-click (highest priority)
        if "paths" in kwargs and kwargs["paths"]:
            clicked_path = kwargs["paths"][0]
            if os.path.isdir(clicked_path):
                target_dir = clicked_path
            else:
                target_dir = os.path.dirname(clicked_path)
        # 2. Active view
        elif self.window.active_view() and self.window.active_view().file_name():
            target_dir = os.path.dirname(self.window.active_view().file_name())
        # 3. First open folder
        else:
            folders = self.window.folders()
            target_dir = folders[0] if folders else None

        if not target_dir:
            sublime.error_message("Tahcia: Cannot determine target folder.\nOpen a folder or a file first.")
            return

        config_path = os.path.join(target_dir, "tahcia-config.json")

        default_config = {
            "api_key": "PASTE_YOUR_TAHCIA_API_KEY_HERE",
            "uploadOnSave": 1
        }
        try:
            print(os.path.basename(target_dir))
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
            
            self.window.open_file(config_path)
            sublime.status_message("Tahcia: Created 'tahcia-config.json' in {}".format(os.path.basename(target_dir)))
            
        except Exception as e:
            sublime.error_message("Tahcia: Failed to create configuration file.\n\nDetails: {}".format(e))


class TahciaEventListener(sublime_plugin.EventListener):
    def on_post_save_async(self, view):
        tahcia_dir, config = get_tahcia_config()
        if not tahcia_dir or not config:
            return

        upload_on_save = config.get("uploadOnSave", 1)
        if not upload_on_save:
            return

        filename = view.file_name()
        if not filename:
            return

        basename = os.path.basename(filename)
        if basename.endswith(".tahcia.json"):
            filename = os.path.realpath(filename)
            tahcia_dir = os.path.realpath(tahcia_dir)
            if filename.startswith(tahcia_dir):
                window = view.window()
                window.run_command("tahcia_script_upload")