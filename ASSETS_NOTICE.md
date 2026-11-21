# Audio y derechos de Kaoru Ink v0.8

La biblioteca activa contiene 17 fragmentos procedentes de `sounds.zip` aportado por la persona usuaria y generado con ElevenLabs. Los WAV fueron revisados técnicamente para excluir pausas internas, segmentos rítmicos y duplicados. La selección es preliminar y requiere escucha subjetiva antes de una publicación final.

Se respetó el **tono y la velocidad originales**. La única conversión fue de 48 kHz estéreo a 44,1 kHz mono (para el mixer Windows), con ganancia fija limitada por muestra para audibilidad y fundidos de solo 6 ms para evitar clics. **No** se aplicó cambio de tono, compresión dinámica, alargamiento ni prolongación sintética.

La licencia MIT del código no significa que los WAV sean MIT. Antes de distribuirlos públicamente comprueba los términos de tu cuenta y de las generaciones de ElevenLabs, y conserva las evidencias de autoría / permisos que correspondan. Los archivos de audio de UI SFX y SFX Kit de versiones anteriores ya no se usan en esta compilación. El PNG del logo original no se modificó.

## Biblioteca fusionada v0.10

Las 20 nuevas muestras fueron proporcionadas por la persona usuaria desde ElevenLabs. El catálogo conserva el nombre de origen de cada una; no implican licencia de redistribución pública automática. Las versiones importadas solo han recibido conversión a mono/44,1 kHz, ganancia de nivel y, para P/E, un fundido breve al final. No se aplicaron cambios de tono, estiramiento ni generación sintética.

## Cambio v0.11: logo nuevo y audio sostenido

El archivo `assets/icon.png` se copió byte por byte desde el PNG proporcionado por la persona usuaria en esta conversación. SHA256: `042ce253a146d9b75e77fa68ef5044ba1f4b02d50c53e129c88a4dca4819d34b`.

El archivo `assets/icon.ico` se generó automáticamente a partir de esos mismos píxeles únicamente porque el ejecutable de Windows requiere icono de formato ICO. No es otro diseño. Los 37 WAV se mantienen sin cambios: el programa selecciona partes centrales de grabaciones reales al crear transiciones, sin alterar los originales que se conservan en disco.


## v0.14 — Audios adicionales de pintura

Se incorporaron siete nuevas grabaciones de ElevenLabs aportadas por la persona usuaria; los archivos se identifican en el catálogo mediante `source_filename`. Solo el sonido B/J de 10 segundos se acondicionó para unirse consigo mismo en un bucle; los otros seis recibieron ganancia fija y conversión mono/44,1 kHz. Los 15 WAV existentes de B/J se nivelaron del mismo modo. Los WAV de P/E no fueron modificados. El material original continúa perteneciendo a sus respectivos titulares; comprueba los términos de publicación/uso de ElevenLabs para distribuirlo públicamente.
