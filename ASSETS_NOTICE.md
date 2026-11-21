# Audio y licencias de Kaoru Ink v0.6 — grabaciones naturales

Se utilizaron exclusivamente los dos ZIP aportados por la usuaria:

- **SFX Kit (Wyzowl):** 16 grabaciones de escritura/dibujo y 2 de roce de materiales. Licencia **CC0** según la documentación del paquete. Copia en `assets/licenses/SFX-KIT-CC0.txt`.
- **UI SFX (Yuki Capital):** 6 grabaciones de arrastre y deslizamiento (algunas estilizadas). Licencia de audio **CC0 1.0**. Copia en `assets/licenses/UISFX-LICENSE-AUDIO.txt`.

**A diferencia de v0.4/v0.5, NO se genera ruido sintético de 26 segundos.** Las pistas son el audio original en su duración original, convertido de 48 kHz a PCM mono 44,1 kHz (16 bits) para el mezclador. No se aplica ajuste de tono, velocidad, compresión, filtrado, ecualización ni normalización. La mezcla estéreo se convierte a mono cuando aplica.

La velocidad por defecto de reproducción es **1,00×**, tono **0 semitonos** y brillo **0**. Al actualizar, una migración de configuración corrige automáticamente las antiguas preferencias de sonido de 0,55×; los demás ajustes se conservan.

P y E reproducen una sola vez la grabación seleccionada y no la repiten. Debido a la duración real de los clips (alrededor de 0,24–1,45 s), no pueden cubrir un trazo más largo sin recurrir a loops o síntesis; preferimos admitir esa limitación antes que deformar su sonido. B utiliza un loop con una unión suavizada mientras haya movimiento real de cursor.

El logo original `assets/icon.png` no fue modificado. `assets/icon.ico` es su conversión técnica para Windows.
