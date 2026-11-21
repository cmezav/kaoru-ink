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
