# Kaoru Ink v0.10 — biblioteca fusionada (Clip Studio Paint / Windows)

Biblioteca actual: **37 sonidos**, de los cuales **17** ya estaban aprobados de `sounds.zip`, **10** fueron seleccionados de `sounds2.zip` y **10** son los nuevos WAV aportados en esta conversación. Los **4 favoritos aterciopelados de 1,5 s** (`brush_velvet_fav_15_01` a `_04`) se conservan sin excepción y tienen prioridad al variar automáticamente.

- **P:** 16 muestras. Un único sonido real por trazo, sin bucle ni relleno artificial. Las grabaciones cortas de lápiz están disponibles en la lista, pero el modo automático continúa favoreciendo las originales largas de 5–8 s para no quedarse en silencio demasiado pronto.
- **B o J:** 15 muestras. Al elegir «Variar automáticamente», usa dos clips de la familia aterciopelada, mezclándolos suavemente de acuerdo con el movimiento horizontal/vertical; la orientación es un **papel de mezcla sonora asignado**, NO una garantía de que los sonidos fueron grabados físicamente con esa orientación. Cambiar de dirección no dispara nuevos archivos. Solo B/J tiene bucle y se silencia al detenerse el lápiz.
- **E:** 6 muestras. Un solo borrado natural por gesto y sin bucle; las opciones con ataques más marcados se conservan como elección manual.

Todas las muestras están en `assets/sounds/curated/`; el catálogo contiene el nombre original, la duración, la categoría y el estado de selección automática. Consulta `REVISION_FUSION.csv` y `AUDITORIA_SOUNDS2.csv` para ver cuáles se añadieron o se dejaron fuera y por qué. Abre `escuchar-fusion.html` para escuchar antes de actualizar Windows.

**Audio:** Los 20 añadidos se convirtieron de 48 kHz estéreo a 44,1 kHz mono PCM16 (requisito del motor) por remuestreo de calidad. No se modificó el tono ni la velocidad; únicamente se igualó el volumen con ganancia constante limitada y se suavizaron los extremos de P/E. No se reconstruyó ninguna textura sintética.

**Ajustes:** P, B/J y E conservan deslizadores independientes; el volumen aumenta con presión real si el controlador Wintab la entrega, de lo contrario usa una estimación de movimiento. Para mantener el audio natural, dejar velocidad 100 %, tono 0, brillo 0. B/J es el único modo en bucle.

**Inicio y segundo plano:** La aplicación puede iniciarse con Windows y quedarse en la bandeja. Solo se activa al tener Clip Studio Paint en primer plano. La rueda de desplazamiento no cambia la muestra seleccionada. El logo PNG original se conserva intacto.

**Compilación:** `.github/workflows/build-windows.yml` compila con GitHub Actions y deja `KaoruInk.exe` en el artefacto `KaoruInk-Windows`. El proyecto no incluye EXE precompilado. Puedes usar el corrector PowerShell entregado junto con el parche para actualizar `cmezav/kaoru-ink` e instalarlo tras compilar. No es necesario Python local.

**Licencias:** Los archivos importados de ElevenLabs son los aportados por la persona usuaria. Sus derechos de redistribución dependen de las condiciones aplicables de ElevenLabs. Consulte `ASSETS_NOTICE.md` para la biblioteca anterior.

**Limitación:** Un sonido P/E más corto que el movimiento se agotará antes de levantar el lápiz; no se crearán prolongaciones artificiales ni un bucle oculto. La sincronización completa depende de qué eventos y presión entregue Windows a la app.
