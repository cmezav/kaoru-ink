# Kaoru Ink v0.6 — sonido natural restaurado

Kaoru Ink reproduce efectos de escritura y dibujo solo cuando **Clip Studio Paint está en primer plano**. Mantiene el icono PNG azul proporcionado por la usuaria, la bandeja del sistema, el inicio con Windows, las teclas **P / B / E**, los ocho controles de audio, Wintab opcional y el bloqueo de la rueda del mouse en los desplegables.

## Qué se corrigió

- **Se eliminaron TODOS los WAV de fricción artificial de 26 segundos**. Aquellas pistas sintetizadas hacían que el tono y la textura se escucharan muy distintos de las grabaciones originales.
- Se reconstruyeron las mismas 24 opciones, utilizando las grabaciones WAV/OGG **íntegras** que están en `sfx-kit-main.zip` y `uisfx-main.zip`, sin filtrado, normalización, compresión, cambios de tono ni cambios de velocidad.
- Los originales de 48 kHz se convirtieron a WAV PCM mono 44,1 kHz / 16 bits para compatibilidad con el mezclador. **No se altera la duración ni el tono**.
- Ajustes neutros de fábrica: **velocidad 1,00×, tono 0, agudos 0**. La primera ejecución de v0.6 reinicia una vez esos tres valores antiguos en `%APPDATA%\KaoruInk\settings.json`; después conserva cualquier ajuste manual. El resto de tus preferencias se conserva.
- **P y E:** una sola reproducción del audio original por contacto, sin repetición dentro del mismo trazo.
- **B:** reproduce un bucle suavizado de la grabación original mientras el cursor se mueve con el mouse presionado, y se atenúa cuando el cursor deja de moverse.

### Límite importante de los trazos largos

Los archivos originales duran entre 0,24 y 1,45 segundos. Si P o E se mantienen presionados más allá de la duración del archivo, el audio termina: **no es posible crear sonido real durante 10 segundos a partir de 0,3 segundos de grabación sin repetir o generar contenido**. Esta versión prioriza la fidelidad del sonido sobre la extensión artificial. Para alargar trazos de forma completamente natural harían falta grabaciones largas auténticas de un solo movimiento.

### Control de sonido

Los controles de velocidad, tono y agudos siguen disponibles, pero cuando los cambias dejan de sonar exactamente como los originales. Para recuperarlos, pulsa **Restaurar tono original** o usa **1,00× / 0 st / 0 %**. La intensidad por presión Wintab se intenta cuando el controlador lo permite; si no hay datos, depende de la velocidad de desplazamiento del mouse (no de la presión física). La rueda no cambia la opción seleccionada.

## Fuentes y licencias

- SFX Kit, CC0: 16 grabaciones `writing-and-drawing` + 2 roces `foley`.
- UI SFX, licencia de audio CC0: 6 efectos de deslizamiento de los paquetes Organic, Studio y Zen.

Consulta `ASSETS_NOTICE.md` y `assets/sounds/library.json` para los archivos exactos. El PNG original `assets/icon.png` no se modificó.

## Windows

Sube el proyecto a `cmezav/kaoru-ink` y consulta **Actions → Build Windows EXE**, que genera el artefacto `KaoruInk-Windows`. El script de actualización incluido por separado permite publicar los cambios e instalar el ejecutable si termina correctamente la compilación de GitHub Actions.

## Regenerar los WAV desde los ZIP

Con Python, `numpy`, `soundfile`, `scipy` instalados:

```powershell
python -m pip install -r requirements-audio.txt
python tools/import_public_sfx.py "$HOME\Downloads\sfx-kit-main.zip" "$HOME\Downloads\uisfx-main.zip"
```

Los archivos ya vienen convertidos en `assets/sounds/original/`, así que **no necesitas instalar Python localmente para aplicar el parche de Windows**.
