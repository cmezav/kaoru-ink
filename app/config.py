"""Local settings and user-scoped Windows startup registration."""
import json
import os
import sys
from pathlib import Path

DEFAULTS = {
    'start_at_login': True,
    'close_to_tray': True,
    'volume': 76,
    'speed': 65,
    'short_id': 'auto',
    'medium_id': 'pencil_medium_fav_01',
    'long_id': 'pencil_fav_long_01',
    'brush_id': 'auto',
}


def config_path():
    base = Path(os.getenv('APPDATA', str(Path.home() / '.config'))) / 'KaoruInk'
    base.mkdir(parents=True, exist_ok=True)
    return base / 'settings.json'


def load():
    settings = DEFAULTS.copy()
    try:
        data = json.loads(config_path().read_text(encoding='utf-8'))
        if isinstance(data, dict):
            for k in DEFAULTS:
                if k in data and isinstance(data[k], type(DEFAULTS[k])):
                    settings[k] = data[k]
    except (FileNotFoundError, ValueError, OSError):
        pass
    settings['volume'] = max(0, min(100, settings['volume']))
    settings['speed'] = max(45, min(120, settings['speed']))
    return settings


def save(settings):
    path = config_path()
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding='utf-8')
    tmp.replace(path)


def set_startup(enabled):
    """Uses HKCU Run; no administrator rights or system-wide installation."""
    if os.name != 'nt':
        return False
    # Never add a transient dev checkout to Windows startup.
    if enabled and not getattr(sys, 'frozen', False):
        return False
    import winreg
    subkey = r'Software\Microsoft\Windows\CurrentVersion\Run'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, subkey) as key:
        if enabled:
            # Windows Registry Run command needs full quotes around the path.
            winreg.SetValueEx(key, 'KaoruInk', 0, winreg.REG_SZ,
                              f'"{sys.executable}" --background')
        else:
            try:
                winreg.DeleteValue(key, 'KaoruInk')
            except FileNotFoundError:
                pass
    return True
