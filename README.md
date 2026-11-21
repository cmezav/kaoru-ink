# ✎ Kaoru Ink — Painting SFX

**Sonidos naturales al dibujar con el mouse en Clip Studio Paint.** Inspirado en la idea de retroalimentación sonora de [Mechvibes](https://github.com/hainguyents13/mechvibes), pero con código independiente, limitado a Windows 10/11 y enfocado exclusivamente en trazos de dibujo.

![Icono original de Kaoru Ink](assets/icon.png)

## ¿Qué hace?

- **Solo funciona con Clip Studio Paint como ventana activa (en primer plano).** Si cambias a Chrome, al escritorio o a otra aplicación, se detienen los loops. El programa puede permanecer en la bandeja del sistema sin ocupar sitio en la barra de tareas.
- Si pulsas **P** mientras Clip Studio Paint está al frente, activa el modo **Lápiz**. Un clic sin desplazamiento es silencioso; al mover el mouse con botón izquierdo presionado, reproduce un trazo corto, seguido de uno mediano cuando superas 0,19 s. Al mantener el botón y dibujar más de **0,58 s** y **28 píxeles** de recorrido, reproduce un trazo largo en bucle hasta detenerte o soltar el botón.
- Si pulsas **B**, activa el modo **Pincel**. Mientras arrastras el mouse, elige un loop de pintura con uniones suavizadas. Al dejar de moverlo por **0,19 s** o soltarlo, el audio se desvanece.
- Biblioteca incluida: **78 sonidos** (37 cortos, 16 medios, 13 largos, 12 loops de pintura), entre los cuales hay 8 favoritos del segmento **7,55–9,20 segundos** del audio original de lápiz.
- En la ventana se puede escuchar cada muestra, elegirla individualmente o alternar automáticamente, ajustar **volumen** y **velocidad/tono** (0,70× a 1,60×), cambiar P/B manualmente y silenciar.
- **Inicio automático** al entrar a Windows mediante `HKCU\...\Run` (sin administrador), activado por defecto en el `.exe`; al iniciar con Windows se abre **oculto en la bandeja**.
- **Cerrar la ventana = minimizar a bandeja** por defecto. Clic derecho sobre el icono para abrirla o salir.
- Ajustes locales: `%APPDATA%\KaoruInk\settings.json`.
- **No** registra ni almacena pulsaciones. El teclado solo sirve para reconocer P/B cuando CSP está en primer plano; **no** añade sonidos de teclado.

### Alcance y limitaciones

El ejecutable se compila para Windows en GitHub Actions; este repositorio no contiene un `.exe` previamente compilado. En Windows, algunas tabletas o lápices digitales pueden generar eventos compatibles con mouse: esta versión escucha eventos de arrastre del botón izquierdo y no identifica físicamente cada dispositivo USB. Los atajos P/B se detectan sin Ctrl/Alt/Windows; si modificaste tus atajos de Clip Studio, cambia la herramienta manualmente en la app. Si ejecutas Clip Studio con privilegios de administrador, podrías necesitar ejecutar la app con un nivel de permisos equivalente para recibir eventos de entrada. De forma predeterminada, **no** se ejecuta como administrador.

La app solo reproduce sonido: **no dibuja en Clip Studio ni intercepta el trazo real**. La selección de modo se basa en los atajos P/B que pulsas, no en leer internamente el pincel activo desde la API de Clip Studio. El sonido es una simulación sincronizada con los movimientos del mouse, no con la presión real del pincel.

## Uso en Windows (ejecutable)

1. Descarga `KaoruInk.exe` desde **Actions → Build Windows EXE → Artifacts → KaoruInk-Windows** o desde una Release etiquetada.
2. Colócalo en una ruta fija, por ejemplo `%LOCALAPPDATA%\Programs\KaoruInk\KaoruInk.exe`. Evita mover el archivo después de activar el inicio automático.
3. Abre `KaoruInk.exe` y deja marcada la opción *Iniciar automáticamente al entrar a Windows*.
4. Abre Clip Studio Paint, selecciona P (lápiz) o B (pincel) y arrastra con el botón izquierdo. Regresa a Kaoru Ink desde el icono junto al reloj cuando quieras cambiar un sonido.

> Windows SmartScreen puede advertir que el archivo no está firmado. El compilado de GitHub Actions no utiliza un certificado de firma de código. Comprueba que lo descargaste de tu propio repositorio y revisa el código antes de ejecutarlo.

## Publicar en la cuenta cmezav

Primero abre una terminal PowerShell dentro de la carpeta de este proyecto, con Git y GitHub CLI (`gh`) instalados:

```powershell
gh auth login
git init
git branch -M main
git add .
git commit -m "feat: launch Kaoru Ink for Clip Studio Paint"
gh repo create cmezav/kaoru-ink --private --source . --remote origin --push
```

Se recomienda **privado inicialmente** hasta revisar los permisos de los sonidos. Luego en el repositorio, `Actions → Build Windows EXE` permite ejecutarlo manualmente. También se genera automáticamente al hacer `git push` a `main`.

Descargar el resultado tras completar la ejecución:

```powershell
$repo = 'cmezav/kaoru-ink'
$run = gh run list -R $repo --workflow build-windows.yml --limit 1 --json databaseId --jq '.[0].databaseId'
gh run watch $run -R $repo --exit-status
$dest = Join-Path $env:USERPROFILE 'Downloads\KaoruInk-build'
gh run download $run -R $repo --name KaoruInk-Windows --dir $dest
$install = Join-Path $env:LOCALAPPDATA 'Programs\KaoruInk'
New-Item -ItemType Directory -Force $install | Out-Null
Copy-Item (Join-Path $dest 'KaoruInk.exe') (Join-Path $install 'KaoruInk.exe') -Force
Start-Process (Join-Path $install 'KaoruInk.exe')
```

Para una Release instalable desde una URL fija, crea una etiqueta:

```powershell
git tag v0.1.0
git push origin v0.1.0
```

Se adjuntará `KaoruInk.exe` a `https://github.com/cmezav/kaoru-ink/releases/tag/v0.1.0` cuando termine la ejecución del workflow de la etiqueta.

## Desarrollo y compilación local

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py
```

El script para regenerar audio a partir de los **tres originales** está disponible en `tools/remaster_audio.py` y necesita `requirements-audio.txt`. Los archivos originales **no están incluidos** en este repositorio. Los WAV recortados y el catálogo `assets/sample-catalog.csv` sí están incluidos.

## Créditos y derechos

Inspiración de UX: [Mechvibes](https://github.com/hainguyents13/mechvibes) (licencia MIT). Esta app no copia el proyecto Rust/Dioxus. Código original Kaoru Ink: MIT. Para los archivos de audio, ver [ASSETS_NOTICE.md](ASSETS_NOTICE.md); **las licencias de las grabaciones originales no han sido verificadas**.
