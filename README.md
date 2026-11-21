# Kaoru Ink v0.4 — trazos de mouse para Clip Studio Paint

Kaoru Ink es una aplicación independiente para Windows, inspirada en la idea de sonido de interacción de Mechvibes. **Solo funciona mientras Clip Studio Paint está en primer plano** y se usa el botón izquierdo del mouse. Se oculta en la bandeja, puede iniciarse con Windows y **no graba pulsaciones ni dibuja por sí misma**.

![Logo original sin modificaciones](assets/icon.png)

## P / B / E: ningún sonido se repite

| Atajo pulsado en Clip Studio | Material | Opciones | Comportamiento |
| --- | --- | ---: | --- |
| **P** | Lápiz, bolígrafo, tiza, deslizamientos alternativos | 12 | Un contacto y roce continuo, sin loop |
| **B** | Marcador, resaltador y roces suaves | 9 | Un solo sonido por arrastre, sin loop |
| **E** | Goma, borrador de pizarra, borrado a lápiz | 3 | Un contacto de goma, sin loop |

El sonido comienza con el **primer movimiento real** después de presionar el mouse, no con el clic quieto. Un trazo corto se detiene rápidamente al soltar. Si la línea continúa, se mantiene **el mismo flujo de fricción**: el programa NO inicia un segundo archivo, no encadena varios cortes, no vuelve al principio y no hace loop, ni siquiera para colorear. Si detienes el mouse sin soltar, baja el volumen y continúa el mismo flujo al volver a moverlo, sin activación nueva. Soltar o cambiar de ventana finaliza suavemente.

**El programa no puede saber al comenzar un trazo cuántos segundos durará.** Por ello prepara una sola grabación larga por trazo; el sonido inicial proviene del primer contacto real y la continuación es una fricción creada a partir del carácter acústico de ese contacto, **sin copiarlo repetidamente**. La continuación es una señal aleatoria no periódica, no una grabación adicional con rayones. La muestra fuente dura 26 s a velocidad 1.0× (aproximadamente 47 s al ritmo predeterminado de 0.55× y 21.7 s a 1.20×); después de ese límite el sonido termina. Para la mayoría de los trazos de dibujo, termina antes cuando sueltas. La duración y el sonido están acotados por estas limitaciones técnicas; no se promete una duración infinita.

### Biblioteca actual

- **16** efectos del apartado `Writing and drawing` de **SFX Kit**. Cuando el audio original contenía varios movimientos, se aisló el primero y se evitó reproducir el resto.
- **2** efectos Foley ligeros de SFX Kit para pincel.
- **6** deslizamientos suaves **orgánicos, zen o studio** de **UI SFX**. Son efectos estilizados de interfaz, no grabaciones reales de papel; están etiquetados como alternativas.
- **24 opciones en total**, cada una con una reproducción previa corta (`preview/`) y una versión sostenida (`held/`) para trazos largos.
- Se quitaron todos los sonidos anteriores procedentes de los tres audios MP3 y los loops B de las versiones previas.
- Velocidad predeterminada: **0,55×**. Se ajusta entre 0,45× y 1,20×. Cambia la velocidad y también el tono.
- Volumen ajustable; sonidos silenciosos cuando Clip Studio Paint no está en primer plano.

### Nota sobre el sonido sostenido

Una grabación de 0,2–1,4 segundos **no alcanza por sí sola** para un trazo de 40 segundos sin repetir fragmentos. Para que se escuche como un solo contacto, la aplicación extrae el primer roce y continúa con ruido de fricción modelado según su espectro. Es una síntesis acústica, no una prolongación perfecta del sonido original. Si deseas una textura completamente grabada (sin síntesis ni loops), la duración máxima siempre dependerá de las grabaciones disponibles.

## Usar y compilar

- Descarga `KaoruInk.exe` desde **Actions → Build Windows EXE → Artifacts → KaoruInk-Windows** una vez que GitHub Actions termine de compilar.
- Guarda el EXE en una ruta permanente, por ejemplo `%LOCALAPPDATA%\Programs\KaoruInk\KaoruInk.exe`, ejecútalo, y configura P/B/E desde su panel.
- Al cerrarlo normalmente queda junto al reloj de Windows; en el menú de bandeja puedes salir por completo. El inicio automático usa una clave de usuario de Windows, sin pedir privilegios de administrador.
- Para ejecutarlo desde Python: `py -3.11 -m pip install -r requirements.txt` y `py -3.11 run.py`.
- Para reproducir el catálogo sin instalar nada, abre `escuchar-sonidos.html` junto a la carpeta `assets`.

### Regenerar esta biblioteca desde los ZIP aportados

No necesitas hacerlo para usar el programa, pues los 24 sonidos ya están incluidos.

```
py -3.11 -m pip install -r requirements-audio.txt
py -3.11 tools/import_public_sfx.py sfx-kit-main.zip uisfx-main.zip
```

### Derechos de los audios

Los paquetes suministrados indican que los archivos de audio incluidos están bajo **CC0 1.0**: [SFX Kit](https://github.com/wyzowl/sfx-kit) y [UI SFX](https://github.com/romainsimon/uisfx). Se conservan en `assets/licenses/` las licencias encontradas en los ZIP del usuario. El código de Kaoru Ink mantiene su licencia MIT. No se incluyen grabaciones de los MP3 compartidos en versiones anteriores. Ver [ASSETS_NOTICE.md](ASSETS_NOTICE.md).

**Limitaciones:** la detección de P/B/E se basa en los atajos de teclado tal como el usuario los asignó en Clip Studio; la app no consulta internamente el estado de las herramientas. Si Clip Studio corre como administrador puede impedir que otra app reciba sus eventos. Algunas tabletas gráficas envían eventos equivalentes al mouse; la app no identifica dispositivos físicos por separado. El EXE generado por Actions no tiene firma digital y puede activar SmartScreen.
