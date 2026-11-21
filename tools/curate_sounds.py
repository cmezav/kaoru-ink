"""Kaoru Ink v0.3: isolate a SINGLE pencil contact and remove noisy B recordings.

The pencil file contains repeated audible scrapes (particularly at 7–9 seconds).
Here, every P variant comes from ONE segment bounded within a single scrape,
with a phase-vocoder prolongation of that SAME one segment: no combination,
retrigger, rhythmic succession, or loop at runtime.
Brush B intentionally excludes the original noisy Paint Brush recording.
Instead it uses only isolated clean scratch transients from the near-silent
Drawing recording (no continuous room/microphone background). Copyright must
still be checked independently before redistribution.
"""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import butter,sosfilt
import librosa

SR = 44100
# each pair has ONE audible contact; 7–9 seconds consist of multiple contacts.
# The first 12 are small separate strokes in the user's favorite region.
P_SINGLES = [
('01',7.605,7.725),('02',7.727,7.846),('03',7.851,7.967),
('04',7.972,8.094),('05',8.106,8.217),('06',8.220,8.334),
('07',8.341,8.450),('08',8.455,8.576),('09',8.581,8.703),
('10',8.707,8.827),('11',8.834,8.954),('12',8.968,9.082),
('13',9.090,9.213),('14',9.220,9.338),('15',9.347,9.471),
]
# Drawing recording has near-digital silence between scratches; the other
# "Paint Brush" recording carries continuous -36 to -40 dBFS noise and is
# excluded entirely. B may loop, and only B loops.
B_CLEAN = [
 ('01','Pincel · roce seco 01',.73,1.16),
 ('02','Pincel · roce seco 02',1.78,2.33),
 ('03','Pincel · roce seco 03',2.86,3.19),
 ('04','Pincel · roce seco 04',3.98,4.40),
]

def cut_mono(path):
    data, sample_rate=sf.read(path, always_2d=True,dtype='float32')
    x=data.mean(axis=1)
    if sample_rate!=SR:
        x=librosa.resample(x,orig_sr=sample_rate,target_sr=SR)
    return x

def bands(x,lo=180,hi=10600):
    return sosfilt(butter(3,[lo,hi],btype='bandpass',fs=SR,output='sos'),x).astype('float32')

def level(x, rms_target=0.09, maximum=.83):
    rms=np.sqrt(np.mean(x*x)+1e-12)
    x=x*min(6.5,rms_target/rms)
    p=np.max(np.abs(x))
    if p>maximum:x=x*maximum/p
    return x.astype('float32')

def pencil_single(segment, duration=9.0):
    """One-scrape phase vocoder. Single attack, no concatenated scratches."""
    segment=bands(segment,200,9500)
    # Crop to exact bounded source, never load neighboring scratches.
    segment=level(segment,.11)
    # Stretch one grain once to a finite one-shot; mouse-up fades immediately.
    rate=len(segment)/(SR*duration)
    y=librosa.effects.time_stretch(segment,rate=rate,n_fft=1024,hop_length=256)
    y=y[:int(SR*duration)]
    if len(y)<int(SR*duration):y=np.pad(y,(0,int(SR*duration)-len(y)))
    # Keep ONE rising edge; smooth long-term dynamics so original periodic
    # fluctuations do not sound like a sequence of fresh pencil attacks.
    energy=np.sqrt(np.convolve(y[::128]**2,np.ones(25)/25,'same')+1e-7)
    gain=np.clip(np.median(energy)/(energy+1e-4),.35,1.7)
    # Smooth frame compensation (not mixing other audio)
    gain=np.interp(np.arange(len(y)),np.arange(len(energy))*128,gain)
    y=y*gain.astype('float32')
    y=level(y,.075)
    fadein=int(.045*SR);fadeout=int(.32*SR)
    y[:fadein]*=np.linspace(0,1,fadein,dtype='float32')
    y[-fadeout:]*=np.linspace(1,0,fadeout,dtype='float32')
    return y

def brush_clean(segment):
    """The clean Drawing source has true silence between recorded strokes."""
    segment=bands(segment,350,9500)
    # Suppress faint residues at beginnings and ends, avoid clicking in B loop.
    y=segment.copy()
    y=level(y,.09)
    overlap=min(round(.10*SR),len(y)//5)
    if overlap>30:
        fade=np.linspace(0,1,overlap,dtype='float32')
        bridge=y[-overlap:]*(1-fade)+y[:overlap]*fade
        y=np.concatenate([y[overlap:-overlap],bridge])
    return y.astype('float32')

def make(pencil_file,drawing_file,out):
    p=cut_mono(pencil_file);d=cut_mono(drawing_file)
    out.mkdir(parents=True,exist_ok=True)
    # Make output deterministically clean: eliminate all previous noisy B files.
    for old in out.glob('*.wav'):old.unlink()
    samples=[]
    for n,a,b in P_SINGLES:
        clip=pencil_single(p[int(a*SR):int(b*SR)])
        name=f'pencil_single_{n}'
        sf.write(out/(name+'.wav'),clip,SR,subtype='PCM_16')
        samples.append({'id':name,'label':f'{"★ " if int(n)<=12 else ""}Un solo roce de lápiz {n}',
                        'category':'pencil','file':name+'.wav','source':'pencil',
                        'start_sec':a,'end_sec':b,'duration_sec':len(clip)/SR,
                        'loop':False,'favorite':int(n)<=12})
    for n,label,a,b in B_CLEAN:
        clip=brush_clean(d[int(a*SR):int(b*SR)])
        name='brush_clean_'+n
        sf.write(out/(name+'.wav'),clip,SR,subtype='PCM_16')
        samples.append({'id':name,'label':label,'category':'brush','file':name+'.wav',
                        'source':'drawing','start_sec':a,'end_sec':b,'duration_sec':len(clip)/SR,
                        'loop':True,'favorite':False})
    (out/'library.json').write_text(json.dumps({'format':2,'sample_rate':SR,'samples':samples},ensure_ascii=False,indent=2),encoding='utf8')
    with (out.parent/'sample-catalog.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(samples[0]));writer.writeheader();writer.writerows(samples)
    print(f'Prepared {len(P_SINGLES)} individual pencil contacts + {len(B_CLEAN)} clean B loops. No noisy brush source retained.')

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--pencil',required=True,type=Path)
    ap.add_argument('--drawing',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path)
    a=ap.parse_args();make(a.pencil,a.drawing,a.out)
