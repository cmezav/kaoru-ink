"""Local settings and user-scoped Windows startup registration."""
import json
import os
import sys
from pathlib import Path

MODES=('pencil','brush','eraser')
PARAMETERS={'volume':(0,100,100),'speed':(45,120,100),'pitch':(-8,8,0),
            'brightness':(-100,100,0),'dynamics':(0,100,70)}
DEFAULTS={
    'start_at_login':True,
    'close_to_tray':True,
    'volume':76,  # overall safety volume; each tool has independent controls
    'per_tool_controls_v1':True,
    'pencil_id':'auto',
    'brush_id':'brush_pair_A',
    'eraser_id':'auto',
}
for mode in MODES:
    for param,(_,_,initial) in PARAMETERS.items():
        DEFAULTS[f'{mode}_{param}']=initial


def config_path():
    base=Path(os.getenv('APPDATA',str(Path.home()/'.config')))/'KaoruInk'
    base.mkdir(parents=True,exist_ok=True)
    return base/'settings.json'

def load():
    settings=DEFAULTS.copy()
    saved={}
    try:
        value=json.loads(config_path().read_text(encoding='utf8'))
        if isinstance(value,dict):saved=value
    except (OSError,ValueError):pass
    for key,initial in DEFAULTS.items():
        if key in saved and type(saved[key]) is type(initial):
            settings[key]=saved[key]
    # Migrate previous volume choices, and keep any deliberate tone edits.
    # New tools can then be adjusted independently without cross-talk.
    if saved and saved.get('per_tool_controls_v1') is not True:
        for mode in MODES:
            for param in PARAMETERS:
                key=f'{mode}_{param}'
                old=saved.get(key if param=='volume' else param)
                if type(old) is int:settings[key]=old
    settings['volume']=max(0,min(100,settings['volume']))
    for mode in MODES:
        for param,(lo,hi,_) in PARAMETERS.items():
            key=f'{mode}_{param}'
            settings[key]=max(lo,min(hi,settings[key]))
        key=f'{mode}_id'
        if not (settings[key]=='auto' or settings[key].startswith(mode+'_')):
            settings[key]=DEFAULTS[key]
    # One-time repair: undo the previous 0.55x pitch/tone processing.
    # Preserve per-tool volumes, dynamics and selected recordings.
    requires_reset = saved.get('natural_original_v07_1') is not True
    if requires_reset:
        for mode in MODES:
            for param, value in (('speed',100),('pitch',0),('brightness',0)):
                settings[f'{mode}_{param}']=value
    settings['natural_original_v07_1']=True
    settings['per_tool_controls_v1']=True
    # One-time switch to the new hand-curated ElevenLabs library.
    # Keep individual mixer settings; retire selections from the old library.
    needs_auto = saved.get('curated_auto_v08') is not True
    if needs_auto:
        for mode in MODES:
            settings[f'{mode}_id']='auto'
    settings['curated_auto_v08']=True
    # New velvet family: make all three menus 'Variar automáticamente' once.
    # Keep independent volume, speed, tone, brightness and dynamics as-is.
    needs_fusion_auto=saved.get('curated_auto_v10') is not True
    if needs_fusion_auto:
        for mode in MODES:settings[f'{mode}_id']='auto'
    settings['curated_auto_v10']=True
    # v0.15: first launch selects the approved 2-stroke A for B/J only.
    # Select A once on upgrade, but never reset P/E or future user choices.
    needs_pair_default = saved.get('brush_pair_default_v15') is not True
    if needs_pair_default:
        settings['brush_id'] = 'brush_pair_A'
    settings['brush_pair_default_v15'] = True
    if (requires_reset or needs_auto or needs_fusion_auto or needs_pair_default
            or (saved and saved.get('per_tool_controls_v1') is not True)):
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
