import platform
import subprocess
import sys

def get_windows_explorer_paths():
    try:
        import win32com.client
        shell = win32com.client.Dispatch("Shell.Application")
        windows = shell.Windows()
        paths = []
        for window in windows:
            try:
                folder = window.Document.Folder
                if folder:
                    path = folder.Self.Path
                    if path: 
                        paths.append(path)
            except Exception:
                continue
        return [path for path in paths if not path.startswith("::")]
    except ImportError:
        print("import pywin32.")
        return []

def get_macos_finder_paths():
    script = '''
    tell application "Finder"
        set window_list to every Finder window
        set path_list to {}
        repeat with w in window_list
            set end of path_list to POSIX path of (target of w as alias)
        end repeat
    end tell
    return path_list
    '''
    try:
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        if result.returncode == 0:
            output = result.stdout.strip()
            if output:
                return output.split(", ")
        else:
            return []
    except Exception as e:
        return []
    return []

def get_open_explorer_paths():
    system = platform.system()
    if system == "Windows":
        return get_windows_explorer_paths()
    elif system == "Darwin":
        return get_macos_finder_paths()
    else:
        return []