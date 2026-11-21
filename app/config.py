"""Local settings and user-scoped Windows startup registration."""
import json
import os
import sys
from pathlib import Path

DEFAULTS={
    'start_at_login':True,
    'close_to_tray':True,
    'volume':76,
    'speed':55,
    'pencil_id':'pencil_pencil_draw',
    'brush_id':'brush_marker_draw',
    'eraser_id':'eraser_eraser',
}

def config_path():
    base=Path(os.getenv('APPDATA',str(Path.home()/'.config')))/'KaoruInk'
    base.mkdir(parents=True,exist_ok=True)
    return base/'settings.json'

def load():
    settings=DEFAULTS.copy()
    try:
        saved=json.loads(config_path().read_text(encoding='utf8'))
        if isinstance(saved,dict):
            for key in DEFAULTS:
                if key in saved and isinstance(saved[key],type(DEFAULTS[key])):
                    settings[key]=saved[key]
    except (OSError,ValueError):pass
    settings['volume']=max(0,min(100,settings['volume']))
    settings['speed']=max(45,min(120,settings['speed']))
    # User selections from removed libraries fall back to valid v0.4 defaults.
    for key in ('pencil_id','brush_id','eraser_id'):
        if not (settings[key]=='auto' or settings[key].startswith(key[:-3]+'_')):
            settings[key]=DEFAULTS[key]
    return settings

def save(settings):
    path=config_path()
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(settings,indent=2,ensure_ascii=False),encoding='utf8')
    tmp.replace(path)

def set_startup(enabled):
    if os.name!='nt':return False
    if enabled and not getattr(sys,'frozen',False):return False
    import winreg
    subkey=r'Software\Microsoft\Windows\CurrentVersion\Run'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,subkey) as key:
        if enabled:
            winreg.SetValueEx(key,'KaoruInk',0,winreg.REG_SZ,f'"{sys.executable}" --background')
        else:
            try:winreg.DeleteValue(key,'KaoruInk')
            except FileNotFoundError:pass
    return True
