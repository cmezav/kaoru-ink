# Licencias y procedencia de sonidos de Kaoru Ink v0.4

**Fuentes utilizadas en esta versión (y solamente estas):**

1. **SFX Kit** (Wyzowl) — `sfx-kit-main.zip` aportado por la persona usuaria. Extraídas las 16 pistas `sounds/writing-and-drawing/writing-*.wav` y 2 pistas de `sounds/foley/`. El README del ZIP declara licencia **CC0** para sus 320 efectos. Archivo de licencia exacto del ZIP: `assets/licenses/SFX-KIT-CC0.txt`. Página indicada en el ZIP: https://github.com/wyzowl/sfx-kit
2. **UI SFX** (Yuki Capital) — `uisfx-main.zip` aportado por la persona usuaria. Extraídas 6 pistas OGG bajo `packages/uisfx/sounds/{organic,studio,zen}/{drag-start,swipe}.ogg`. Archivo de licencia de audios exacto del ZIP: `assets/licenses/UISFX-LICENSE-AUDIO.txt` (dedicación **CC0 1.0**). Página indicada por el material: https://uisfx.com

El script `tools/import_public_sfx.py` documenta cada selección y los recortes que se hacen antes de un segundo gesto. Los WAV generados de 26 segundos usan un solo contacto real y una continuación **sintetizada no periódica**: no contienen loops ni segmentos de grabación reiterados. Los WAV de `preview/` contienen el contacto aislado para preescuchar.

**No se han copiado archivos de los tres MP3 originales** en v0.4. No se incluye código fuente de UI SFX ni de SFX Kit. El PNG original del usuario se conserva sin cambios como `assets/icon.png`. El ICO es una conversión técnica necesaria para Windows.
