"""Local settings and user-scoped Windows startup registration."""
import json
import os
import sys
from pathlib import Path

DEFAULTS={
    'start_at_login':True,
    'close_to_tray':True,
    'volume':76,
    'speed':100,
    'pitch':0,
    'brightness':0,
    'natural_audio_v1':True,
    'dynamics':70,
    'pencil_volume':100,
    'brush_volume':100,
    'eraser_volume':100,
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
    migrate=False
    try:
        saved=json.loads(config_path().read_text(encoding='utf8'))
        if isinstance(saved,dict):
            migrate=(saved.get('natural_audio_v1') is not True)
            for key in DEFAULTS:
                if key in saved and isinstance(saved[key],type(DEFAULTS[key])):
                    settings[key]=saved[key]
    except (OSError,ValueError):pass
    if migrate:
        # Old 0.55x processing destroyed the original sound color. Reset once.
        settings.update(speed=100,pitch=0,brightness=0,natural_audio_v1=True)
    settings['volume']=max(0,min(100,settings['volume']))
    settings['speed']=max(45,min(120,settings['speed']))
    settings['pitch']=max(-8,min(8,settings['pitch']))
    settings['brightness']=max(-100,min(100,settings['brightness']))
    settings['dynamics']=max(0,min(100,settings['dynamics']))
    for key in ('pencil_volume','brush_volume','eraser_volume'):
        settings[key]=max(0,min(100,settings[key]))
    # User selections from removed libraries fall back to valid v0.4 defaults.
    for key in ('pencil_id','brush_id','eraser_id'):
        if not (settings[key]=='auto' or settings[key].startswith(key[:-3]+'_')):
            settings[key]=DEFAULTS[key]
    if migrate:
        save(settings)
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
