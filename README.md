# Kaoru Ink v0.5 — sonido para dibujar en Clip Studio Paint

Aplicación independiente para Windows 10/11 inspirada en la idea de retroalimentación sonora de [Mechvibes](https://github.com/hainguyents13/mechvibes). Usa el mouse o los eventos de mouse que genera la tableta al dibujar en **Clip Studio Paint**, solo cuando este programa está en primer plano.

![Logo original de Kaoru Ink, PNG sin modificar](assets/icon.png)

## Cambios de v0.5

- **P — Lápiz:** exactamente una reproducción por trazo. Usa la textura de fricción no repetida de v0.4; no hace bucle ni dispara sonidos nuevos al pausar o alargar el trazo. Se desvanece al levantar el botón.
- **B — Pincel:** ahora **sí permite un bucle de textura de pincel**, sin ataques/clics adicionales. El volumen depende del movimiento: al detener el cursor mientras el botón sigue presionado se silencia gradualmente y al continuar se recupera sin reiniciar la pista. Al soltar el botón, fade-out y fin. La textura en bucle se prepara del tramo de fricción de la muestra existente, evitando el ataque inicial de cada repetición.
- **E — Borrador:** una reproducción por trazo, igual que P, sin bucle.
- **Mezclador con 8 controles:** volumen general, velocidad (0,45×–1,20×), tono (−8 a +8 semitonos), brillo de agudos (−100 a +100), sensibilidad dinámica (0–100), volumen P, volumen B y volumen E. Los ajustes se guardan automáticamente en `%APPDATA%\KaoruInk\settings.json`.
- **Presión del lápiz:** intento opcional de captación mediante el controlador **Wintab**, si la tableta dispone de él y permite recibir datos en segundo plano. El estado de la interfaz indica si está recibiendo *presión real Wintab*. **No todas las tabletas/controladores Windows Ink lo permiten**. Si no llegan datos, los cambios de volumen se calculan **aproximadamente a partir de la velocidad del movimiento del cursor**, no a partir de presión física. Con mouse normal nunca se conoce la fuerza de pulsación. Si la opción no funciona en tu tableta, prueba el modo de estimación y ajusta sensibilidad.
- **Rueda del mouse:** desplazarse por la ventana de configuración ya **no cambia accidentalmente** la muestra seleccionada en los desplegables. Hay que abrir el desplegable y elegir explícitamente otro sonido.
- **Logo:** el archivo `assets/icon.png` es exactamente el que suministraste, sin ningún cambio; el ejecutable lo incluye como recurso. Para el icono del `.exe`, Windows requiere el archivo `assets/icon.ico` equivalente.

## Cómo escucharlo

Elige una muestra P/B/E en el desplegable. Pulsa **Escuchar** para previsualizarla. La vista previa suena **una sola vez** (incluso B). En Clip Studio Paint, activa la herramienta con los atajos **P**, **B** o **E** y arrastra con el botón izquierdo del mouse. **La aplicación no lee directamente la herramienta activa dentro de Clip Studio**, sino que reconoce las teclas usadas para cambiarla. Si configuraste otros atajos, puedes escoger el modo desde la propia aplicación.

- La aplicación se queda en la bandeja junto al reloj y se puede iniciar con Windows.
- Solo reproduce mientras Clip Studio Paint sea la ventana activa; no guarda las teclas ni graba el dibujo.
- Los tres modos tienen un **inicio sonoro por contacto**. Solo B puede mantener una textura continua en bucle durante ese mismo contacto.
- En P y E, los archivos de fricción duran hasta ~26 s a velocidad 1×, y unos ~47 s al ajuste predeterminado 0,55×; si dibujas más tiempo puede agotarse el audio. Nunca se reinicia a mitad del trazo.
- La presión real depende de Wintab, que puede estar ausente o entregar eventos solo a Clip Studio. La captura se intenta sin requerir privilegios de administrador. **No se promete compatibilidad universal con presión real.**
- El ajuste de tono independiente de la velocidad utiliza estiramiento por solapamiento adaptado a sonidos de fricción. En ajustes extremos puede alterar ligeramente la textura.

## Compilar en GitHub Actions

Haz push a `main` de `cmezav/kaoru-ink`. El workflow `.github/workflows/build-windows.yml` valida el código y genera el artefacto **KaoruInk-Windows** con `KaoruInk.exe`.

Para descargar el artefacto de una ejecución existente (reemplaza `<RUN_ID>` por su número):

```powershell
gh run download <RUN_ID> --repo cmezav/kaoru-ink --name KaoruInk-Windows --dir "$HOME\Downloads\KaoruInk-build"
```

O usa el script `Actualizar-KaoruInk-v05.ps1` incluido por separado junto al ZIP del parche, con los parámetros `-Publicar -Instalar`.

## Desarrollo local

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python run.py
```

Las 24 muestras existentes de v0.4 se mantienen intactas. Son audios de SFX Kit y UI SFX; los archivos de licencia y la procedencia exacta de cada muestra están en `ASSETS_NOTICE.md` y `assets/sounds/library.json`. Este parche v0.5 no añade audios externos.

## Limitaciones de verificación

Se comprueban las pruebas unitarias y la sintaxis del código en esta entrega. El ejecutable para Windows se crea en tu GitHub Actions después de publicar el parche y necesita una prueba real en Clip Studio con tu tableta para confirmar la captura Wintab y la sensación sonora.
