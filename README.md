# Kaoru Ink v0.11 — audio continuo sin bucle idéntico

Una aplicación ligera para Windows y Clip Studio Paint: reproduce sonidos de fricción al dibujar con el mouse/lápiz y puede mantenerse en la bandeja del sistema.

## Corrección de esta versión

- **P — lápiz:** deja de apagarse al finalizar un WAV. Empieza una sola vez por gesto y, si el trazo continúa, conecta grabaciones **reales** de lápiz mediante fundidos cruzados antes de que termine la anterior. Mientras dibujas el volumen responde al movimiento o, si está disponible, a la presión Wintab.
- **B/J — pintura:** elimina el bucle fijo de una misma grabación (`loops=-1`). Mantiene dos texturas aterciopeladas (horizontal/vertical), pero **cada textura evoluciona** alternando muestras aprobadas con transiciones suaves. Al girar el lápiz, la mezcla cambia sin un nuevo contacto audible.
- **E — borrador:** tiene el mismo sostén por relevos de grabaciones reales. Ya no se calla por quedarse sin los 0,8–2 s de su archivo inicial.
- **Al parar sin levantar el lápiz:** el audio baja gradualmente hasta quedar en silencio; al reanudar sigue la textura sin reiniciar el evento. **Al levantarlo** se desvanece el audio.
- Los **cinco deslizadores de cada modo** (volumen, velocidad, tono, brillo, dinámica) siguen siendo independientes. Por defecto se respeta el tono original: 100 % de velocidad, 0 semitonos y brillo 0.
- Se conservan **los 37 WAV curados**: 16 P, 15 B/J y 6 E. No se sustituyen ni se vuelven a procesar los WAV del catálogo. Los **cuatro favoritos de pintura aterciopelada de 1,5 s** se mantienen.
- **Logo nuevo:** `assets/icon.png` es copia idéntica del archivo `Diseños RápidosD (18).png` recibido de la persona usuaria; SHA256 `042ce253a146d9b75e77fa68ef5044ba1f4b02d50c53e129c88a4dca4819d34b`. Se utiliza directamente para ventana y bandeja. `icon.ico` es solo una conversión de formato a los tamaños exigidos para iconos de Windows, sin rediseño.

### Limitación acústica importante

Con una biblioteca finita no se puede producir fricción natural perpetua totalmente nueva sin reutilizar audio. Esta versión **no sintetiza un ruido de dos minutos ni baja artificialmente el tono**. En su lugar reproduce varios audios reales y suaviza sus relevos con una transición breve. Se evita el mismo ciclo idéntico en el modo automático, pero un oído atento todavía puede detectar algún cambio de textura. Es necesario probarlo en Windows/Clip Studio Paint para juzgar la naturalidad. El modo manual repite su única muestra con fundidos; para mayor variedad usa «Variar automáticamente».

## Instalación

El flujo `Build Windows EXE` compila `KaoruInk.exe` en GitHub Actions para Windows 10/11. Para actualizar el repositorio `cmezav/kaoru-ink`, descarga el parche v0.11 y el `.ps1` acompañante, guárdalos juntos en Descargas y ejecuta el actualizador con `-Publicar -Instalar`. El script busca la compilación del commit publicado y reemplaza el ejecutable **solo** después de descargar y verificar el artefacto. No requiere Python local.

Se conservan el inicio automático, la bandeja, la detección de Clip Studio Paint al frente, P/B/J/E, el ajuste de presión real opcional con Wintab y la protección para que la rueda del mouse no cambie sonidos elegidos.

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

Los tests usan un mezclador simulado para verificar que P y E continúan 10–25 segundos, que las grabaciones del mezclador no utilizan `loops=-1`, que B/J mezcla direcciones, que P/B/E conservan sus controles y que el PNG es idéntico al recibido. Esto **no** reemplaza una prueba de audio en el hardware real.

## Derechos

Los sonidos de ElevenLabs fueron aportados por la persona usuaria. Su disponibilidad en el repositorio no equivale a autorización universal para redistribuirlos; verifica las condiciones de la cuenta y de publicación de ElevenLabs antes de distribuir el proyecto públicamente. Consulta `ASSETS_NOTICE.md`.
