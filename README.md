# Kaoru Ink v0.3 — one pencil scrape per stroke

Windows desktop companion for Clip Studio Paint. Inspired by Mechvibes, with independent code.

![Logo original aportado por la usuaria](assets/icon.png)

## Modo P — **UN SOLO roce**, no muchos rayones

- Only responds when **Clip Studio Paint is the foreground application**.
- Press **P** to select pencil, hold the **left mouse button**, then move the mouse.
- **Exactly one audio file is triggered for the entire stroke.** The selected WAV is sourced from a *single isolated physical scrape* and time-stretched to a longer sound. No intro+medium+long mix, no additional strokes, and no looping in P.
- Releasing the mouse or stopping the drag fades the sound. The same mouse-down never triggers a second scratch.
- The WAV lasts 9 seconds at normal playback speed, or approximately 16.4 seconds at default 0.55×. Longer strokes become silent after that limit; **P never restarts or loops**.
- There are **15 individual pencil scrapes** to choose from, including 12 derived from the favorite 7–9 second interval (split *between* audible scratches rather than retaining the original sequence).

## Modo B — pintar en loop **sin el ruido de grabación anterior**

- Press **B** in Clip Studio to select brush mode.
- **B is the ONLY mode with looping sound**. Loop runs while dragging, fades on release or when motion stops.
- All **12 previous B WAVs were removed** because the original paint recording has continuous background noise during idle sections.
- Replaced with **4 clean, dry stroke loops** derived from the *Drawing* source, whose gaps are effectively silent. These may sound drier than the original brush recording but do not carry its constant ambient hiss.

## Ajustes

- Default playback speed: **0.55×**; adjustable from 0.45× to 1.20×.
- One sound selector for P and one selector for B, plus previews.
- Volume slider, mute and tray icon; application may start in the background on Windows logon.
- **The original PNG icon is kept byte-for-byte unchanged** under `assets/icon.png`. Windows `.ico` is a technical conversion of the same art.
- Clip Studio detection uses the foreground window and P/B key events. It doesn't modify Clip Studio or record the keyboard.

## Build your Windows EXE

Commit/push to GitHub then open **Actions → Build Windows EXE**. Successful builds provide `KaoruInk-Windows` with `KaoruInk.exe`.

To test on a Windows development machine:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m unittest discover -s tests -v
python run.py
```

The curated WAVs were built using `tools/curate_sounds.py` (install `requirements-audio.txt`); use it with the two supplied MP3 source files if regenerating. Both input MP3s are intentionally excluded from the repository.

## Rights

License MIT applies to the original code only. **Licenses for the audio source recordings have not been independently verified.** File names or "no copyright" descriptions are insufficient proof of redistribution rights. Review `ASSETS_NOTICE.md` before keeping these WAVs in a public repository or releasing an executable.
