"""Restore ORIGINAL audio from the two user-provided CC0 source ZIP archives.

Usage: python tools/import_public_sfx.py /path/to/sfx-kit-main.zip /path/to/uisfx-main.zip
No fake noise extension, normalization, filtering, retuning or time-stretching.
"""
from pathlib import Path
import io, json, sys, wave, zipfile
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'assets'/'sounds'
SR=44100  # native mixer rate; original sources are 48 kHz
# Source paths and option labels. The complete source recordings are preserved.
SFX=[
 ('pencil','pencil_draw','writing-pencil-draw','Lápiz · dibujar (grabación original)',0.48),
 ('pencil','pencil_write','writing-pencil-write','Lápiz · escribir (grabación original)',0.21),
 ('pencil','pencil_tick','writing-pencil-tick','Lápiz · toque breve',0.24),
 ('pencil','pen_draw','writing-pen-draw','Bolígrafo · línea (grabación original)',0.40),
 ('pencil','pen_write','writing-pen-write','Bolígrafo · escritura (grabación original)',0.35),
 ('pencil','pen_tick','writing-pen-tick','Bolígrafo · toque breve',0.24),
 ('pencil','chalk_draw','writing-chalk-draw','Tiza · trazo (grabación original)',0.42),
 ('pencil','chalk_write','writing-chalk-write','Tiza · escritura (grabación original)',0.19),
 ('pencil','chalk_tick','writing-chalk-tick','Tiza · toque breve',0.24),
 ('brush','marker_draw','writing-marker-draw','Marcador · dibujar (grabación original)',0.49),
 ('brush','marker_write','writing-marker-write','Marcador · escritura (grabación original)',0.27),
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

def decode_original(data):
    """Read native waveforms at their intended rate; resample without pitch shift."""
    audio, rate=sf.read(io.BytesIO(data), dtype='float32', always_2d=True)
    mono=audio.mean(axis=1)
    if rate!=SR:
        mono=resample_poly(mono,SR,rate).astype('float32')
    return mono


def write_original_wav(path, data):
    path.parent.mkdir(exist_ok=True,parents=True)
    # Avoid normalized gains or spectral modification. 16-bit PCM is the mixer's format.
    pcm=(np.clip(data,-1.,1.)*32767.).astype('<i2')
    with wave.open(str(path),'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SR)
        wav.writeframes(pcm.tobytes())


def main(sfx_zip, uisfx_zip):
    OUTPUT.mkdir(parents=True,exist_ok=True)
    # Delete the synthetic 26-second tracks and former previews.
    for old in OUTPUT.glob('**/*.wav'):
        old.unlink()
    samples=[]
    with zipfile.ZipFile(sfx_zip) as sfx, zipfile.ZipFile(uisfx_zip) as uisfx:
        source=[]
        for category, short, filename, label, length in SFX:
            source.append((category,short,label,'SFX Kit',f'sfx-kit-main/sounds/writing-and-drawing/{filename}.wav',sfx))
        for category,short,filename,label,length in FOLEY:
            source.append((category,short,label,'SFX Kit',f'sfx-kit-main/sounds/{filename}.wav',sfx))
        for category,short,pack,feature,label,length in UISFX:
            source.append((category,short,label,'UI SFX',f'uisfx-main/packages/uisfx/sounds/{pack}/{feature}.ogg',uisfx))
        for category, short, label, credit, path, archive in source:
            original=decode_original(archive.read(path))
            ident=f'{category}_{short}'
            relative=f'original/{ident}.wav'
            write_original_wav(OUTPUT/relative,original)
            samples.append({'id':ident,'label':label,'category':category,
                            'file':relative,'preview_file':relative,
                            'duration_sec':round(len(original)/SR,3),
                            'loop':False,'source':credit,'source_path':path,
                            'kind':'natural_original_no_processing'})
            print(f'{ident}: {len(original)/SR:.3f}s original',flush=True)
    library={'format':6,'sample_rate':SR,
             'library':'SFX Kit and UI SFX - original tones at 1.00x',
             'behavior':'P/E original one-shot; B original waveform with smooth loop while moving',
             'samples':samples}
    (OUTPUT/'library.json').write_text(json.dumps(library,ensure_ascii=False,indent=2),encoding='utf8')
    print('Restored recordings:',len(samples))

if __name__=='__main__':
    if len(sys.argv)!=3:
        sys.exit('Usage: python tools/import_public_sfx.py sfx-kit-main.zip uisfx-main.zip')
    main(sys.argv[1],sys.argv[2])
