"""Windows desktop entrypoint."""
import os
import sys
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtNetwork import QLocalServer,QLocalSocket
from PySide6.QtWidgets import QApplication,QMessageBox,QSystemTrayIcon
from PySide6.QtGui import QIcon
from . import config
from .audio import AudioEngine
from .ui import MainWindow


def resource(relative):
    root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))
    return root/relative


def main():
    if os.name!='nt':
        raise SystemExit('Kaoru Ink esta diseñado para Windows 10/11.')
    app=QApplication(sys.argv)
    app.setApplicationName('Kaoru Ink')
    app.setQuitOnLastWindowClosed(False)
    icon=resource('assets/icon.ico')  # Windows EXE icon
    original_png=resource('assets/icon.png')  # unmodified user PNG
    if icon.exists():app.setWindowIcon(QIcon(str(icon)))

    # Prevent duplicate playback hooks and duplicate tray icons on login.
    lock_name=f'KaoruInk-{os.getenv("USERNAME","user")}-v1'
    server=QLocalServer()
    if not server.listen(lock_name):
        client=QLocalSocket()
        client.connectToServer(lock_name)
        if client.waitForConnected(220):
            client.write(b'open');client.flush();client.waitForBytesWritten(200)
            return 0
        # Pipe can be stale after hard shutdown.
        QLocalServer.removeServer(lock_name)
        if not server.listen(lock_name):return 0

    try:
        audio=AudioEngine(resource('assets/sounds'))
    except Exception as err:
        QMessageBox.critical(None,'Kaoru Ink — audio','No se pudo iniciar el audio. Revisa tu dispositivo de sonido.\n\n'+str(err))
        return 1
    window=MainWindow(original_png if original_png.exists() else icon,audio,config.load(),app)
    server.newConnection.connect(lambda:(server.nextPendingConnection().readAll(),window._show()))
    if '--background' in sys.argv and QSystemTrayIcon.isSystemTrayAvailable():
        QTimer.singleShot(100,window.hide)
    else:
        window.show()
    return app.exec()

if __name__=='__main__':
    from PySide6.QtWidgets import QSystemTrayIcon
    sys.exit(main())
