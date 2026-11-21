"""Import the user's CC0 source ZIPs and render non-repeating mouse stroke textures.

Usage: python tools/import_public_sfx.py /path/to/sfx-kit-main.zip /path/to/uisfx-main.zip
The held sounds contain exactly one onset and one unique noise bed, never a repeated source event.
"""
from pathlib import Path
import io, json, re, sys, wave, zipfile, hashlib
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from scipy.ndimage import gaussian_filter1d

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'assets'/'sounds'
SR=22050
HOLD_SECONDS=26.0  # 26 s at 1.0x, ~47 s at the 0.55x default
# Model one physical contact. Multi-stroke 'write' tracks are cropped BEFORE the second event.
SFX=[
 ('pencil','pencil_draw','writing-pencil-draw','Lápiz · dibujar (roce aislado)',0.48),
 ('pencil','pencil_write','writing-pencil-write','Lápiz · escribir (roce aislado)',0.21),
 ('pencil','pencil_tick','writing-pencil-tick','Lápiz · toque breve',0.24),
 ('pencil','pen_draw','writing-pen-draw','Bolígrafo · línea (roce aislado)',0.40),
 ('pencil','pen_write','writing-pen-write','Bolígrafo · escritura (roce aislado)',0.35),
 ('pencil','pen_tick','writing-pen-tick','Bolígrafo · toque breve',0.24),
 ('pencil','chalk_draw','writing-chalk-draw','Tiza · trazo (roce aislado)',0.42),
 ('pencil','chalk_write','writing-chalk-write','Tiza · escritura (roce aislado)',0.19),
 ('pencil','chalk_tick','writing-chalk-tick','Tiza · toque breve',0.24),
 ('brush','marker_draw','writing-marker-draw','Marcador · dibujar (roce aislado)',0.49),
 ('brush','marker_write','writing-marker-write','Marcador · escritura (roce aislado)',0.27),
 ('brush','marker_tick','writing-marker-tick','Marcador · toque breve',0.24),
 ('brush','highlighter','writing-highlighter','Resaltador · pasada suave',0.38),
 ('eraser','eraser','writing-eraser','Goma de borrar · roce aislado',0.19),
 ('eraser','wipe','writing-wipe','Borrador de pizarra · pasada',0.37),
 ('eraser','scribble','writing-scribble','Borrado a lápiz · roce rápido',0.35),
]
UISFX=[
 ('pencil','organic_drag','organic','drag-start','Orgánico · inicio de arrastre (estilizado)',0.32),
 ('pencil','zen_drag','zen','drag-start','Zen · arrastre suave (estilizado)',0.25),
 ('pencil','studio_drag','studio','drag-start','Studio · arrastre (estilizado)',0.27),
 ('brush','organic_swipe','organic','swipe','Orgánico · pincel deslizante (estilizado)',0.44),
 ('brush','zen_swipe','zen','swipe','Zen · pincel suave (estilizado)',0.31),
 ('brush','studio_swipe','studio','swipe','Studio · pincel deslizante (estilizado)',0.33),
]
FOLEY=[
 ('brush','paper_slide','foley/foley-paper-slide','Pincel · roce de papel (alternativo)',0.42),
 ('brush','fabric_slide','foley/foley-fabric-slide','Pincel · roce de tela (alternativo)',0.39),
]

def load_audio(data):
    audio, rate=sf.read(io.BytesIO(data), dtype='float32',always_2d=True)
    mono=audio.mean(axis=1)
    if rate!=SR: mono=resample_poly(mono,SR,rate).astype('float32')
    return mono


def write_wav(path, data):
    path.parent.mkdir(exist_ok=True,parents=True)
    pcm=(np.clip(data,-.94,.94)*32767).astype('<i2')
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes(pcm.tobytes())


def single_contact(original, duration):
    # Use the first continuous sound contact only, never the full multi-stroke track.
    audio=original[:int(duration*SR)].copy()
    if len(audio)<int(.07*SR):raise ValueError('Too short')
    # Reduce source noise / long gaps; retain physical material coloration.
    local=(np.abs(audio))
    maxamp=float(local.max())
    # Trim long initial silence but leave 10ms of lead-in.
    audible=np.flatnonzero(local>max(.0007,maxamp*.035))
    if len(audible):
        begin=max(0,int(audible[0]) - int(.012*SR))
        audio=audio[begin:]
    # First event, stable normalization across all selected sounds.
    rms=float(np.sqrt(np.mean(audio**2)))
    if rms>1e-7:audio *= min(3.4, .048/rms)
    peak=float(np.max(np.abs(audio)))
    if peak>.67:audio*=.67/peak
    n=min(len(audio),int(.009*SR))
    if n>0:audio[:n]*=np.linspace(0,1,n)
    return audio


def build_hold(head, key):
    """One physical attack plus 26 seconds of NON-LOOPING spectral friction.

    The continuation is novel noise matched to the source spectral profile,
    not a repeated/sequenced/concatenated recording. It cannot make another attack.
    """
    count=int(SR*HOLD_SECONDS)
    rng=np.random.default_rng(int(hashlib.sha256(key.encode()).hexdigest()[:8],16))
    # Spectral envelope extracted from actual clean single-contact sample.
    analysis=np.zeros(8192,dtype='float32')
    context=head[max(0,len(head)-8192):]
    analysis[:len(context)]=context*np.hanning(len(context))
    spectral=np.abs(np.fft.rfft(analysis))
    spectral=gaussian_filter1d(spectral,38)
    freqs=np.fft.rfftfreq(8192,1/SR)
    # Remove unnecessary high-frequency hiss and mains rumble.
    spectral *= np.clip(freqs/145,0,1) * np.clip((9100-freqs)/2600,0,1)
    spectral /= spectral.max()+1e-12
    # Create a truly unique continuous noise stream, no sample-loop, no periodic grain.
    noise=rng.standard_normal(count).astype('float32')
    spectrum=np.fft.rfft(noise)
    spectrum *= np.interp(np.fft.rfftfreq(count,1/SR),freqs,spectral)
    friction=np.fft.irfft(spectrum,n=count).astype('float32')
    friction/=float(np.sqrt(np.mean(friction*friction)))+1e-9
    # No rhythmic amplitude peaks: only gentle slow variations to resemble pressure.
    times=np.arange(count,dtype='float32')/SR
    knots=np.arange(0,HOLD_SECONDS+.6,.6)
    levels=rng.uniform(.80,1.07,len(knots)).astype('float32')
    pressure=np.interp(times,knots,levels).astype('float32')
    amp=min(.039, max(.018, float(np.sqrt(np.mean(head**2)))*.7))
    out=friction*(amp*pressure)
    # Sound has one and only one contact transient. Blend to friction at end of contact.
    a=min(int(.105*SR),len(head)//2)
    b=min(len(head),a+int(.12*SR))
    if b<=a: a=max(0,len(head)//3);b=len(head)
    env=np.ones(len(head),dtype='float32')
    env[a:b]=np.linspace(1,0,b-a)
    env[b:]=0
    out[:b] *= 1-env[:b]
    out[:len(head)] += head*env
    # Natural stop in the unusual case someone paints beyond available duration.
    fade=int(.8*SR)
    out[-fade:]*=np.linspace(1,0,fade)
    return out


def main(sfx_zip,uisfx_zip):
    OUTPUT.mkdir(parents=True,exist_ok=True)
    for old in OUTPUT.glob('**/*.wav'):old.unlink()
    samples=[]
    with zipfile.ZipFile(sfx_zip) as sfx,zipfile.ZipFile(uisfx_zip) as uisfx:
        source=[]
        for category,short,filename,label,length in SFX:
            source.append((category,short,label,length, 'SFX Kit',f'sfx-kit-main/sounds/writing-and-drawing/{filename}.wav',sfx))
        for category,short,folder,label,length in FOLEY:
            source.append((category,short,label,length,'SFX Kit',f'sfx-kit-main/sounds/{folder}.wav',sfx))
        for category,short,pack,feature,label,length in UISFX:
            source.append((category,short,label,length,'UI SFX',f'uisfx-main/packages/uisfx/sounds/{pack}/{feature}.ogg',uisfx))
        for category,short,label,length,credit,path,archive in source:
            original=load_audio(archive.read(path))
            contact=single_contact(original,length)
            ident=f'{category}_{short}'
            preview=Path('preview')/f'{ident}.wav'
            held=Path('held')/f'{ident}.wav'
            # The preview is intentionally short. End it without an abrupt click.
            audition=contact.copy()
            fade=min(len(audition)//3, int(.035*SR))
            if fade>0:audition[-fade:]*=np.linspace(1,0,fade)
            write_wav(OUTPUT/preview,audition)
            write_wav(OUTPUT/held,build_hold(contact,ident))
            samples.append({'id':ident,'label':label,'category':category,'file':str(held).replace('\\','/'),
                            'preview_file':str(preview).replace('\\','/'),'duration_sec':round(len(contact)/SR,2),
                            'hold_seconds':HOLD_SECONDS,'loop':False,'source':credit,'source_path':path,
                            'source_trim_seconds':length,'kind':'one_onset_friction'})
            print(ident,len(contact)/SR,flush=True)
    library={'format':4,'sample_rate':SR,'library':'CC0 SFX Kit and UI SFX',
             'behavior':'one playback on first movement, no looping/no retrigger, fade on mouse up',
             'samples':samples}
    (OUTPUT/'library.json').write_text(json.dumps(library,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Samples:',len(samples))

if __name__=='__main__':
    if len(sys.argv)!=3:sys.exit('Usage: python tools/import_public_sfx.py sfx-kit-main.zip uisfx-main.zip')
    main(sys.argv[1],sys.argv[2])
