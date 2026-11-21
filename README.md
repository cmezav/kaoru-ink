# Kaoru Ink v0.12 — Audio por gestos, sin bucles de reloj

**Corrección del defecto de v0.11 demostrado en la grabación del 21 de noviembre**: el motor anterior reactivaba una pista al agotarse la anterior, incluso durante un arrastre uniforme. El resultado fue una cadencia audible de roces repetidos.

## Regla nueva

- **P**: exactamente un archivo original por cada arrastre del lápiz. Nunca se vuelve a disparar durante el mismo arrastre, ni por tiempo ni por dirección.
- **B o J**: una grabación natural cuando comienza a colorear. **Solo** se permite otra en variación automática al confirmar una nueva pasada horizontal/vertical o inversión de dirección; exige desplazamiento significativo y evita movimientos pequeños. El cambio usa un fundido de 90 ms.
- **E**: mismo criterio por pasadas reales; un borrado continuo recto no reinicia una pista por tiempo, y una nueva pasada de borrado puede reproducir otra muestra solo en automático.
- **Selección manual**: una sola grabación por arrastre, incluso para B/J/E; no hay relanzamientos por cambios de dirección.
- Se mantuvieron los **37 sonidos** originales y el **PNG exacto** proporcionado por la persona usuaria. Tono, brillo, velocidad y sensibilidad se ajustan independientemente para P, B/J y E.
- La presión física depende de si el controlador de la tableta permite leerla mediante Wintab; si no, la intensidad depende del desplazamiento. El sonido es audible solo con Clip Studio Paint al frente.

**Límite importante:** no existe audio auténticamente perpetuo y no repetitivo al reproducir una biblioteca finita. Si la línea recta dura más que el WAV y no haces una nueva pasada, el sonido termina. Esta versión da prioridad explícita a **no escuchar bucles** sobre fingir una continuidad artificial. Los cambios de dirección en B/J/E sí pueden producir un nuevo roce, asociado al gesto real, y no a un cronómetro.

## Prueba sugerida

1. Abre CSP, elige P y mantén una línea recta de 10 s. Deberías oír un solo inicio, luego silencio cuando el WAV se agote, sin golpes periódicos.
2. En B o J, dibuja una línea recta de 10 s; no hay reactivaciones. Después pinta de izquierda a derecha y de derecha a izquierda: cada **pasada** significativa puede activar un nuevo roce suave.
3. En E, repite la prueba anterior. La aplicación solo reacciona a nuevas pasadas, nunca al fin del archivo anterior.
4. En selección manual, comprueba que cambiar de dirección no reinicia el audio.

## Compilar (Windows)

Hay un workflow en `.github/workflows/build-windows.yml` que compila el EXE mediante PyInstaller en GitHub Actions. El corrector `.ps1` suministrado en la conversación aplica el parche, lo publica en `cmezav/kaoru-ink` y descarga el EXE **solo después de la compilación satisfactoria**, con verificación SHA256 y copia de seguridad previa.

Para desarrollo local usa `requirements.txt` y `python -m unittest discover -s tests -v`.
