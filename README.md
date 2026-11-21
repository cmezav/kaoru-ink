# Kaoru Ink v0.8 — sonidos naturales seleccionados

App de Windows para Clip Studio Paint, inspirada en Mechvibes y enfocada en el sonido del lápiz digital. Con la ventana de Clip Studio Paint al frente:

- **P:** una grabación de trazo real por arrastre, nunca repetida ni sintetizada. En selección automática rota entre **5 muestras de 5–8 segundos**, evitando que dos trazos seguidos tengan el mismo sonido. Hay también 6 muestras cortas seleccionables manualmente.
- **B y J:** activan el **mismo modo pintura**, con **4 muestras** de 5–6 segundos disponibles en variación automática. Solo pintura tiene bucle, cuyo volumen sigue el movimiento; baja al parar y se desvanece al levantar el stylus.
- **E:** borrador con **2 muestras** de 0,7 y 2,0 segundos, alternadas automáticamente. Sin bucle.
- Los tres selectores comienzan en **Variar automáticamente** tras la actualización. El programa conserva los deslizadores independientes de volumen, tono, agudos, velocidad y dinámica de P/B-J/E. Los atajos solo se reconocen con Clip Studio Paint en primer plano.
- La rueda del mouse no cambia el sonido elegido. Se puede minimizar a la bandeja e iniciar con Windows.

**Limitación:** si dibujas con P más de 8 segundos o borras más de 2,0 segundos, la pista puede terminar antes que el gesto: no inventamos fricción ni repetimos un archivo para disimularlo. Necesitamos **nuevas grabaciones realmente continuas** para esos casos.

## Qué se revisó

De `sounds.zip`: 29 WAV, 1 MP3 (versión anterior descartada), y 1 ZIP interno que contiene duplicados. Se aprobaron técnicamente 17 WAV: 11 de lápiz, 4 de pintura y 2 de borrado. Se descartó el lápiz de 20 segundos por pausas y los borrados largos con varios ataques/silencios. Consulta `REVISION_SONIDOS.csv` para el estado por archivo y `escuchar-curados.html` para escucharlos.

### Construcción del ejecutable

Al subir los cambios a la rama main, GitHub Actions compila en Windows. El artifact se llama `KaoruInk-Windows`. La aplicación instalada solo se reemplaza cuando el build termina correctamente. En la carpeta `assets/sounds/curated/` están los 17 WAV; el catálogo está en `assets/sounds/library.json`.

## Avisos

La variación automática selecciona **una pista por trazo**; no mezcla varias a la vez. Los controles al 100 % de velocidad y 0 de tono mantienen el tono natural. Wintab es experimental: si no hay presión real, la app estima la intensidad a partir de la velocidad del cursor. Consulta `ASSETS_NOTICE.md` para derechos de audio y el logo original.
