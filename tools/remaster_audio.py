"""Build a curated Kaoru Ink sound library from three user-supplied recordings.

Usage: python tools/remaster_audio.py --pencil PATH --drawing PATH --brush PATH
Do not assume the recordings are freely redistributable. The derivative samples
are provided only under the permissions of the original recordings' owners.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly

TARGET_RATE = 44100
# Key: (id, public name, original recording, start, end, loop, favorite)
CUTS = [
    # Pencil drawing – hand-curated transient variations
    ('pencil_tick_01','Lápiz · roce leve 01','pencil',0.69,1.04,False,False),
    ('pencil_tick_02','Lápiz · roce leve 02','pencil',1.08,1.43,False,False),
    ('pencil_tick_03','Lápiz · roce seco 03','pencil',1.53,1.89,False,False),
    ('pencil_tick_04','Lápiz · roce breve 04','pencil',2.53,2.82,False,False),
    ('pencil_tick_05','Lápiz · punta 05','pencil',2.86,3.19,False,False),
    ('pencil_tick_06','Lápiz · punta 06','pencil',3.39,3.73,False,False),
    ('pencil_tick_07','Lápiz · punta 07','pencil',3.76,4.12,False,False),
    ('pencil_tick_08','Lápiz · roces suaves 08','pencil',5.21,5.65,False,False),
    ('pencil_tick_09','Lápiz · roces suaves 09','pencil',6.23,6.68,False,False),
    ('pencil_fav_short_01','★ Favorito 7s · inicio','pencil',7.55,7.94,False,True),
    ('pencil_fav_short_02','★ Favorito 8s · centro','pencil',7.96,8.38,False,True),
    ('pencil_fav_short_03','★ Favorito 8s · final','pencil',8.40,8.81,False,True),
    ('pencil_fav_short_04','★ Favorito 9s · remate','pencil',8.84,9.19,False,True),
    ('pencil_tick_10','Lápiz · grano 10','pencil',10.22,10.56,False,False),
    ('pencil_tick_11','Lápiz · grano 11','pencil',10.59,10.93,False,False),
    ('pencil_tick_12','Lápiz · grano 12','pencil',11.01,11.39,False,False),
    ('pencil_tick_13','Lápiz · grano 13','pencil',12.56,12.94,False,False),
    ('pencil_tick_14','Lápiz · grano 14','pencil',13.21,13.54,False,False),
    ('pencil_tick_15','Lápiz · rasgo 15','pencil',14.61,14.98,False,False),
    ('pencil_tick_16','Lápiz · rasgo 16','pencil',15.10,15.48,False,False),
    ('pencil_tick_17','Lápiz · rasgo 17','pencil',15.52,15.93,False,False),
    ('pencil_tick_18','Lápiz · golpe 18','pencil',16.86,17.16,False,False),
    ('pencil_tick_19','Lápiz · golpe 19','pencil',17.19,17.51,False,False),
    ('pencil_tick_20','Lápiz · punta rápida 20','pencil',18.09,18.44,False,False),
    ('pencil_tick_21','Lápiz · punta rápida 21','pencil',18.46,18.73,False,False),
    ('pencil_tick_22','Lápiz · punta rápida 22','pencil',19.24,19.56,False,False),
    ('pencil_tick_23','Lápiz · punta rápida 23','pencil',19.60,19.91,False,False),
    ('pencil_tick_24','Lápiz · trazos 24','pencil',20.63,21.02,False,False),
    ('pencil_tick_25','Lápiz · trazos 25','pencil',21.22,21.61,False,False),
    ('pencil_tick_26','Lápiz · trazos 26','pencil',21.85,22.29,False,False),
    ('pencil_tick_27','Lápiz · toques 27','pencil',23.13,23.46,False,False),
    ('pencil_tick_28','Lápiz · toques 28','pencil',23.48,23.76,False,False),
    # Drawing strokes – four discrete noisier brush/pencil attacks
    ('drawing_short_01','Grafito · ataque 01','drawing',0.70,1.04,False,False),
    ('drawing_short_02','Grafito · ataque 02','drawing',1.70,2.05,False,False),
    ('drawing_short_03','Grafito · ataque 03','drawing',2.83,3.16,False,False),
    ('drawing_short_04','Grafito · ataque 04','drawing',3.94,4.29,False,False),
    ('drawing_short_05','Grafito · cola 05','drawing',2.08,2.36,False,False),
    # Medium strokes, separate from both fast attacks and sustained dragging.
    ('pencil_medium_01','Medio · lápiz suave 01','pencil',0.72,1.55,False,False),
    ('pencil_medium_02','Medio · lápiz granulado 02','pencil',1.42,2.13,False,False),
    ('pencil_medium_03','Medio · lápiz granulado 03','pencil',2.62,3.42,False,False),
    ('pencil_medium_04','Medio · lápiz ligero 04','pencil',3.43,4.23,False,False),
    ('pencil_medium_05','Medio · lápiz cortado 05','pencil',5.23,5.89,False,False),
    ('pencil_medium_06','Medio · lápiz cortado 06','pencil',6.23,6.87,False,False),
    ('pencil_medium_fav_01','★ Favorito · trazo medio 7–8s','pencil',7.55,8.39,False,True),
    ('pencil_medium_fav_02','★ Favorito · trazo medio 8–9s','pencil',8.40,9.19,False,True),
    ('pencil_medium_07','Medio · trazos finos 07','pencil',10.25,11.11,False,False),
    ('pencil_medium_08','Medio · trazos finos 08','pencil',11.15,12.05,False,False),
    ('pencil_medium_09','Medio · punta seca 09','pencil',12.59,13.43,False,False),
    ('pencil_medium_10','Medio · punta seca 10','pencil',14.63,15.43,False,False),
    ('pencil_medium_11','Medio · punta seca 11','pencil',15.28,16.04,False,False),
    ('pencil_medium_12','Medio · grafito 12','pencil',20.64,21.55,False,False),
    ('pencil_medium_13','Medio · grafito 13','pencil',21.49,22.51,False,False),
    ('drawing_medium_01','Medio · grafito áspero 01','drawing',1.71,2.38,False,False),
    # Long pencil variants, deliberately used as loopable sustained pencil contact
    ('pencil_long_01','Largo · lápiz suave 01','pencil',0.70,2.10,True,False),
    ('pencil_long_02','Largo · lápiz granulado 02','pencil',2.60,4.24,True,False),
    ('pencil_long_03','Largo · lápiz ligero 03','pencil',5.23,6.74,True,False),
    ('pencil_fav_long_01','★ Favorito 7–9s · completo','pencil',7.55,9.20,True,True),
    ('pencil_fav_long_02','★ Favorito 8s · roce extendido','pencil',7.95,9.20,True,True),
    ('pencil_long_04','Largo · lápiz continuo 04','pencil',10.24,12.12,True,False),
    ('pencil_long_05','Largo · lápiz fino 05','pencil',12.56,14.02,True,False),
    ('pencil_long_06','Largo · lápiz áspero 06','pencil',14.62,16.08,True,False),
    ('pencil_long_07','Largo · lápiz rítmico 07','pencil',20.64,22.51,True,False),
    ('drawing_long_01','Largo · grafito áspero 01','drawing',0.72,1.20,True,False),
    ('drawing_long_02','Largo · grafito áspero 02','drawing',1.72,2.37,True,False),
    ('drawing_long_03','Largo · grafito áspero 03','drawing',2.84,3.23,True,False),
    ('drawing_long_04','Largo · grafito áspero 04','drawing',3.95,4.46,True,False),
    # Paint brushes – seamless crossfaded loops. Different textures/pressures.
    ('paint_loop_01','Pintura · tela sutil 01','brush',0.08,1.47,True,False),
    ('paint_loop_02','Pintura · tela sutil 02','brush',1.49,3.17,True,False),
    ('paint_loop_03','Pintura · brocha fuerte 03','brush',3.44,4.18,True,False),
    ('paint_loop_04','Pintura · brocha fuerte 04','brush',4.48,5.13,True,False),
    ('paint_loop_05','Pintura · cerda 05','brush',5.20,6.13,True,False),
    ('paint_loop_06','Pintura · cerda 06','brush',6.14,6.90,True,False),
    ('paint_loop_07','Pintura · cerda 07','brush',6.98,7.90,True,False),
    ('paint_loop_08','Pintura · roce largo 08','brush',0.91,2.85,True,False),
    ('paint_loop_09','Pintura · roce intenso 09','brush',3.47,5.24,True,False),
    ('paint_loop_10','Pintura · roce mixto 10','brush',5.21,7.83,True,False),
    ('paint_loop_11','Pintura · fondo suave 11','brush',0.10,3.20,True,False),
    ('paint_loop_12','Pintura · barrido 12','brush',3.46,4.09,True,False),
]


def mono_resample(path: Path):
    x, rate = sf.read(str(path), always_2d=True, dtype='float32')
    mono = x.mean(axis=1).astype(np.float32)
    if rate != TARGET_RATE:
        g = math.gcd(rate, TARGET_RATE)
        mono = resample_poly(mono, TARGET_RATE//g, rate//g).astype(np.float32)
    return mono


def seamless_crossfade(x, sr=TARGET_RATE):
    overlap = min(round(0.095*sr), int(len(x)*0.16))
    if overlap < 24: return x
    phase = np.linspace(0, np.pi/2, overlap, dtype=np.float32)
    # First and last overlap combine across a wrap seam and are emitted at end.
    join = x[-overlap:]*np.cos(phase)**2 + x[:overlap]*np.sin(phase)**2
    return np.concatenate((x[overlap:-overlap], join)).astype(np.float32)


def master(x:np.ndarray, *, looping:bool):
    # 80Hz HP and 13kHz LP remove low rumble and sharp MP3 hiss.
    hp = butter(2, 85, btype='highpass', fs=TARGET_RATE, output='sos')
    lp = butter(2, 12500, btype='lowpass', fs=TARGET_RATE, output='sos')
    x = sosfilt(hp, x).astype(np.float32)
    x = sosfilt(lp, x).astype(np.float32)
    # Reference to energetic 30 ms frames avoids boosting long silences.
    chunk = max(1, int(TARGET_RATE*0.03))
    levels = [np.sqrt(np.mean(x[i:i+chunk]**2)) for i in range(0,len(x),chunk) if len(x[i:i+chunk]) > 50]
    ref = float(np.percentile(levels, 68)) if levels else 0.
    if ref < 0.0012:
        raise ValueError('Too much silence in requested sound interval')
    gain = float(np.clip(0.14/ref, 1.0, 8.0))
    x = x * gain
    # Soft limiter to preserve the contact sounds with no hard digital clipping.
    if np.max(np.abs(x)) > 0.90:
        x = (0.9*np.tanh(x/0.9)).astype(np.float32)
    if looping:
        x = seamless_crossfade(x)
    else:
        fade_in = min(int(.009*TARGET_RATE), len(x)//5)
        fade_out = min(int(.055*TARGET_RATE), len(x)//4)
        if fade_in: x[:fade_in] *= np.sin(np.linspace(0,np.pi/2,fade_in,dtype=np.float32))
        if fade_out: x[-fade_out:] *= np.cos(np.linspace(0,np.pi/2,fade_out,dtype=np.float32))
    # Per-sample loudness leveling toward -19 dBFS average. This second step
    # raises quiet ASMR textures as well as louder scratch sounds consistently.
    rms = max(1e-5, float(np.sqrt(np.mean(x*x))))
    final_gain = float(np.clip(0.112/rms,0.5,4.0))
    x = x * final_gain
    if np.max(abs(x)) > 0.91:
        x = (0.91 * np.tanh(x/0.91)).astype(np.float32)
    return x


def build(pencil:Path, drawing:Path, brush:Path, out:Path):
    sources = {k:mono_resample(p) for k,p in [('pencil',pencil),('drawing',drawing),('brush',brush)]}
    out.mkdir(parents=True,exist_ok=True)
    samples=[]
    for name,label,source,start,end,loop,fav in CUTS:
        y = sources[source]
        a=int(round(start*TARGET_RATE)); b=int(round(end*TARGET_RATE))
        if b>len(y): raise ValueError(f'{name} end out of bounds')
        x=master(y[a:b].copy(),looping=loop)
        sf.write(str(out / f'{name}.wav'),x,TARGET_RATE,subtype='PCM_16')
        samples.append({'id':name,'label':label,'category':'brush' if source=='brush' else ('medium' if '_medium_' in name else ('long' if loop else 'short')),
            'file':f'{name}.wav','source':source,'start_sec':start,'end_sec':end,'duration_sec':round(len(x)/TARGET_RATE,3),
            'loop':loop,'favorite':fav,'peak_dbfs':round(float(20*np.log10(max(1e-8,np.max(abs(x))))),1),
            'rms_dbfs':round(float(20*np.log10(max(1e-8,np.sqrt(np.mean(x*x))))),1)})
    (out/'library.json').write_text(json.dumps({'format':1,'sample_rate':TARGET_RATE,'samples':samples},ensure_ascii=False,indent=2), encoding='utf-8')
    with (out.parent/'sample-catalog.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(samples[0])); w.writeheader();w.writerows(samples)
    print('Created',len(samples),'samples; categories:',{c:sum(s['category']==c for s in samples) for c in ('short','medium','long','brush')})
    print('Favorite region included:',[s['id'] for s in samples if s['favorite']])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--pencil',type=Path,required=True);parser.add_argument('--drawing',type=Path,required=True);parser.add_argument('--brush',type=Path,required=True);parser.add_argument('--out',type=Path,default=Path('assets/sounds'))
    a=parser.parse_args(); build(a.pencil,a.drawing,a.brush,a.out)
