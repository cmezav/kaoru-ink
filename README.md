# Kaoru Ink — recuperación de audio natural (v0.7.1)

**Esta revisión sustituye el parche v0.7 antes de instalarlo.** No contiene EXE ni inicia compilaciones.

## Qué se corrige

- Elimina por completo la síntesis granular de 120 segundos y los fragmentos superpuestos que provocaron el sonido artificial de la demo de 7 segundos.
- **P y E:** reproducen un WAV original una sola vez, con su tono natural y sin bucle, ruido añadido ni reinicios en un mismo arrastre. Al soltar el mouse, se desvanece el sonido si aún está sonando.
- **B:** único modo con bucle mientras coloreas. El volumen sigue el movimiento y baja al detenerte.
- Preserva los 24 WAV originales y el logo PNG exacto.
- Mantiene **controles independientes** de volumen, velocidad, tono, brillo y sensibilidad para P, B y E.
- Primera ejecución: restaura los ajustes de velocidad a 1,00×, tono a 0 y brillo a 0 para eliminar la coloración guardada de versiones anteriores. No cambia las opciones ni volúmenes por herramienta.
- Bloqueo de rueda del mouse sobre selectores.

### Límite físico importante

Los WAV de lápiz/bolígrafo incluidos duran entre 0,24 y 1,45 segundos. Sin repetir material, sintetizar sonidos ni ralentizar artificialmente los archivos, **no es posible reproducir una fricción natural continua de 7 segundos a partir de estas muestras**. Esta revisión prioriza fidelidad: la muestra acaba cuando acaba, aunque el trazo siga. Para acompañar trazos largos y mantener el sonido natural deben incorporarse grabaciones reales más largas de un único roce; eso no está resuelto con estos ZIP.

## Archivos

Este parche modifica únicamente `app/audio.py`, `app/config.py`, `app/ui.py`, `tests/test_audio_playback.py`, `tests/test_library.py`, `tests/test_ui_features.py` y `README.md`.

No se modifican icono, sonidos, sistema de entrada, detección de Clip Studio, ni empaquetado de Windows. Esta entrega no compiló ni descargó ejecutables.
