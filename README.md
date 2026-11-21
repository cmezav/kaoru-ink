# Kaoru Ink v0.13 — sonido en tiempo real ligado al movimiento

Esta versión cambia el motor anterior que dejaba acabar un WAV a los pocos segundos o reactivaba otro con una cadencia demasiado evidente.

## Comportamiento

- **P**: mientras dibujas, un flujo de pequeños fragmentos *internos* de grabaciones reales de lápiz. El audio no termina al agotarse un archivo. Cambia la textura a intervalos irregulares, sin volver a reproducir el inicio completo del clip. Son 16 opciones manuales y una selección automática que prioriza 5 grabaciones aprobadas.
- **B/J**: pintura continua con dos texturas que se mezclan según la dirección horizontal o vertical. Los cuatro favoritos de 1,5 segundos siguen incluidos. No se reinicia un WAV al girar el lápiz.
- **E**: fricción continua de borrador, también ligada a la actividad. 6 opciones y variación automática entre las aprobadas.
- **Movimiento**: volumen que se desvanece cuando detienes la mano y reaparece al moverla, sin reactivar el ataque original. Parada suave cuando levantas el lápiz.
- **Presión**: intenta leer Wintab. Si llegan paquetes recientes se verá **Presión REAL Wintab** con porcentaje; cuando no lleguen, muestra claramente **Intensidad ESTIMADA por movimiento**. El cursor no permite medir la fuerza física del lápiz, y algunas tabletas/Windows Ink no exponen presión a una aplicación en segundo plano.
- Los controles de volumen, velocidad, tono, brillo y dinámica permanecen **independientes** para P, B/J y E. A valores neutros, las fuentes se leen a su tono y velocidad de origen, sin desplazar el tono automáticamente.
- No se cambia ni una muestra de las **37 grabaciones** ni `assets/icon.png` (último logo del usuario, sin modificaciones).

## Importante: límites de sonido

Esto no reproduce un audio infinito auténtico: reconstruye una textura utilizando trozos breves de distintas grabaciones de la biblioteca, seleccionados para evitar los ataques y empalmados con ventanas suaves. Pueden aparecer artefactos o cierta repetición a pesar del sistema; **ninguna prueba de código garantiza naturalidad auditiva**. Se incluyen demostraciones para escuchar antes de instalar.

El motor utiliza **PortAudio a través de sounddevice** para generar audio en bloques en tiempo real. Requiere un dispositivo de salida funcional en Windows. Si no se puede iniciar, muestra un error, en lugar de fingir que se está reproduciendo audio.

## Desarrollo

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m unittest discover -s tests -v
python run.py
```

El workflow `.github/workflows/build-windows.yml` ejecuta los tests y crea `KaoruInk.exe`. Tras publicar un commit, se debe comprobar el resultado de GitHub Actions y la salida de audio con Clip Studio Paint y la tableta reales.


## v0.14 — Solo B/J: coloreado rápido y volumen nivelado (sin cambios P/E)

Esta versión **conserva exactamente el comportamiento y los 16 WAV de P, los 6 WAV de E, sus controles y la captura Wintab**. Mantiene el PNG del icono byte por byte.

Se añade el audio original de 10 segundos aportado por la persona usuaria para una textura de coloreado rápido: se niveló su volumen y se unieron los extremos mediante un fundido cruzado de 480 ms, quedando un ciclo de ~9,52 s. La reproducción mantiene su tono natural, sin síntesis de ruido ni cambio de velocidad. El loop se utiliza **solo en B/J** y **solo cuando se detectan pequeñas inversiones rápidas de dirección o varios trazos pequeños seguidos**. Los trazos rectos de alta velocidad no lo activan por sí solos. La mezcla entre coloreado normal y rápido tiene transiciones graduales; el volumen sigue la velocidad/pausas y la presión disponible de la tableta.

Se añadieron 6 muestras nuevas de B/J como opciones manuales de pintura. La muestra de 10 s queda también disponible como selección manual: en ese caso el bucle permanece activo mientras mueves el lápiz. El modo automático conserva las variantes anteriores para coloreado normal y activa la nueva muestra larga al reconocer coloreado rápido.

Se normalizaron mediante **ganancia fija** los 15 sonidos anteriores de B/J y los 7 nuevos a un nivel cercano a −28 dBFS RMS, limitando los picos a −7 dBFS. No se aplicó compresor, cambio tonal o filtro. P y E no recibieron ningún cambio de volumen. Los niveles registrados están en `AUDIO_NIVELES_B.csv`.

Se verificaron pruebas de la lógica con simulaciones; el comportamiento real de la tableta, los movimientos y la naturalidad de la unión deben probarse en Windows / Clip Studio Paint. El loop es un ciclo de audio reutilizado y puede resultar perceptible después de escucharlo repetidamente; no se promete variación infinita.

## v0.15 — 3 ciclos B/J de dos pasadas (exclusivamente pintura)

- Opción **A** predeterminada para B/J en el primer inicio de v0.15; reúne los favoritos 1 y 2. Velocidad del audio un 15 % mayor, preservando la altura tonal mediante Rubber Band antes de empaquetar. Duración aproximada del ciclo: 2,39 s.
- Opciones **B** (favoritos 3 y 4) y **C** (favoritos 1 y 4) disponibles para elegir manualmente. Ambas mantienen su duración original de 2,75 s.
- En B/J, los tres ciclos se reproducen completos como material aprobado y siguen la compuerta de movimiento y la presión que ya existían. No se reinician al cambiar de dirección.
- **P/E no han cambiado**, ni su motor ni sus archivos de sonido. Tampoco se modificaron los iconos ni sus ajustes.
- La opción `Variar automáticamente` sigue disponible; al seleccionar A, B o C se oye el ciclo elegido de forma explícita.
