"""Kaoru Ink Windows settings panel and system-tray control."""
from pathlib import Path
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QIcon,QAction,QFont,QPixmap
from PySide6.QtWidgets import (
    QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFrame,
    QComboBox,QSlider,QCheckBox,QSystemTrayIcon,QMenu,QGraphicsDropShadowEffect,
    QSizePolicy,QScrollArea,QMessageBox
)
from . import config
from .focus import foreground_paint
from .input_monitor import InputEvents,MouseKeyboardMonitor,StrokeController

STYLE = '''
QMainWindow,QWidget#root,QScrollArea#scroll { background: #12111c; color: #f4efff; }
QWidget { font-family: 'Segoe UI'; font-size: 12px; color: #f3f0ff; }
QFrame#panel { background: #201d30; border: 1px solid #333044; border-radius: 17px; }
QFrame#hero { background: #29223e; border: 1px solid #514367; border-radius: 20px; }
QLabel#eyebrow { color: #b4a5ce; font-size: 11px; font-weight: 700; }
QLabel#title { color: #fff3fd; font-size: 28px; font-weight: 800; }
QLabel#headline { color: #f5efff; font-size: 17px; font-weight: 700; }
QLabel#muted { color: #a9a1bb; font-size: 12px; }
QLabel#value { color: #e5b8fb; font-weight: 700; }
QLabel#status { color: #decafa; font-weight: 700; }
QComboBox { background: #151422; border: 1px solid #4d4365; border-radius: 9px; padding: 10px 12px; min-height: 20px; color: #f2e9ff; }
QComboBox:hover { border-color: #af80de; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox QAbstractItemView { background: #252039; color: white; selection-background-color: #685184; }
QPushButton { background: #7f5aae; border: none; color: white; padding: 11px 16px; font-weight: 700; border-radius: 10px; }
QPushButton:hover { background: #946ac8; }
QPushButton:pressed { background: #583d80; }
QPushButton#secondary { background: #342d4a; border: 1px solid #53476a; }
QPushButton#secondary:hover { background: #49375f; }
QPushButton#mode { background: #322946; border: 1px solid #695886; }
QPushButton#mode:checked { background: #8054ad; border: 1px solid #d9adef; }
QSlider::groove:horizontal { height: 7px; background: #39334d; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #ba87e6; border-radius: 3px; }
QSlider::handle:horizontal { background: #f7d6fd; width: 16px; margin: -5px 0; border-radius: 8px; }
QCheckBox { color: #e6dced; spacing: 10px; }
QCheckBox::indicator { width: 18px; height: 18px; }
QCheckBox::indicator:unchecked { background: #20182d; border: 1px solid #66547e; border-radius: 5px; }
QCheckBox::indicator:checked { background: #9a6dca; border: 1px solid #9a6dca; border-radius: 5px; image: none; }
QScrollBar:vertical { background: #171521; width: 9px; }
QScrollBar::handle:vertical { background: #514263; border-radius: 4px; }
'''


def text(content,obj=None):
    label=QLabel(content)
    if obj:label.setObjectName(obj)
    label.setWordWrap(True)
    return label


def panel():
    p=QFrame();p.setObjectName('panel')
    l=QVBoxLayout(p);l.setContentsMargins(22,20,22,20);l.setSpacing(12)
    return p,l


class MainWindow(QMainWindow):
    def __init__(self,app_icon:Path,audio,settings,app):
        super().__init__()
        self.app=app
        self.app_icon=app_icon
        self.audio=audio
        self.settings=settings
        self.controller=StrokeController(audio,settings)
        self.bus=InputEvents()
        self.monitor=MouseKeyboardMonitor(self.bus)
        self.focused=False
        self.muted=False
        self.is_quitting=False
        self.setWindowTitle('Kaoru Ink — Painting SFX')
        self.setWindowIcon(QIcon(str(app_icon)))
        self.setMinimumSize(760,650)
        self.resize(890,760)
        self.setStyleSheet(STYLE)
        self._build()
        self._tray(app_icon)
        self._wiring()
        self.audio.set_volume(settings['volume'])
        self.audio.set_speed(settings['speed'])
        try:
            if settings['start_at_login']:
                config.set_startup(True)
        except OSError as ex:
            self.start_check.setToolTip(f'No se pudo activar inicio automático: {ex}')
        try:
            self.monitor.start()
        except Exception as ex:
            QMessageBox.warning(self,'Control del mouse','No se pudo iniciar el monitor de entradas: '+str(ex))
        self.timer=QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(80)
        self._tick()

    def _build(self):
        wrapper=QWidget();wrapper.setObjectName('root')
        self.setCentralWidget(wrapper)
        root=QVBoxLayout(wrapper);root.setContentsMargins(28,23,28,18);root.setSpacing(17)
        header=QHBoxLayout()
        logo=QLabel()
        logo.setPixmap(QPixmap(str(self.app_icon)).scaled(66,66,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        header.addWidget(logo)
        namebox=QVBoxLayout();namebox.setSpacing(0)
        namebox.addWidget(text('KAORU · AUDIO STUDIO','eyebrow'))
        namebox.addWidget(text('Kaoru Ink','title'))
        namebox.addWidget(text('Cada trazo merece sonar.','muted'))
        header.addLayout(namebox,1)
        self.mute_button=QPushButton('Silenciar')
        self.mute_button.setObjectName('secondary')
        self.mute_button.clicked.connect(self._toggle_mute)
        header.addWidget(self.mute_button)
        self.hide_button=QPushButton('A la bandeja  ↘')
        self.hide_button.clicked.connect(self.hide)
        header.addWidget(self.hide_button)
        root.addLayout(header)
        scroll=QScrollArea();scroll.setObjectName('scroll');scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner=QWidget();inner.setStyleSheet('background: transparent;')
        body=QVBoxLayout(inner);body.setContentsMargins(1,1,6,16);body.setSpacing(18)
        hero=QFrame();hero.setObjectName('hero')
        h=QVBoxLayout(hero);h.setContentsMargins(23,20,23,22);h.setSpacing(9)
        h.addWidget(text('CONEXIÓN CON CLIP STUDIO','eyebrow'))
        self.status=text('Buscando Clip Studio Paint…','status')
        h.addWidget(self.status)
        h.addWidget(text('Solo suena al arrastrar el botón izquierdo del mouse mientras Clip Studio Paint está al frente. No produce sonidos en otras aplicaciones.','muted'))
        mode_row=QHBoxLayout();mode_row.setSpacing(10)
        mode_row.addWidget(text('Herramienta activa:'))
        self.pencil_button=QPushButton('P · Lápiz')
        self.pencil_button.setObjectName('mode');self.pencil_button.setCheckable(True)
        self.brush_button=QPushButton('B · Pincel')
        self.brush_button.setObjectName('mode');self.brush_button.setCheckable(True)
        self.pencil_button.setChecked(True)
        mode_row.addWidget(self.pencil_button);mode_row.addWidget(self.brush_button);mode_row.addStretch()
        h.addLayout(mode_row)
        h.addWidget(text('P: una sola reproducción por trazo, sostenida y suave. B: pintura en bucle solo mientras arrastras.','muted'))
        body.addWidget(hero)
        samples,_=panel()
        samples.layout().addWidget(text('Biblioteca de trazos','headline'))
        samples.layout().addWidget(text('78 sonidos remasterizados · P usa un solo sonido continuo; únicamente B repite su muestra. Los ★ son tus favoritos del segundo 7–9.','muted'))
        self.combos={}
        self.preview_buttons={}
        for category,heading,info,setting in (
            ('short','01 · Inicio de trazo','El primer roce de P. Un sonido por trazo, sin repetir.','short_id'),
            ('medium','02 · Cuerpo del trazo','Se une suavemente al inicio si mantienes P.','medium_id'),
            ('long','03 · Textura sostenida','Se alarga en el mismo sonido de P, sin iniciar otro ni hacer loop.','long_id'),
            ('brush','04 · Pintar en bucle','Al deslizar el pincel con B, hasta detenerte.','brush_id')):
            p=QFrame();line=QVBoxLayout(p);line.setContentsMargins(0,8,0,8);line.setSpacing(5)
            line.addWidget(text(heading,'headline'));line.addWidget(text(info,'muted'))
            r=QHBoxLayout();r.setSpacing(12)
            combo=QComboBox();combo.setMinimumWidth(360);combo.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
            combo.addItem('↝  Variar automáticamente','auto')
            for sid in self.audio.by_category[category]:
                s=self.audio.samples[sid]
                combo.addItem(s['label']+f"  ({s['duration_sec']:.2f} s)",sid)
            current=combo.findData(self.settings[setting]);combo.setCurrentIndex(max(0,current))
            r.addWidget(combo,1)
            preview=QPushButton('Escuchar ▶');preview.setObjectName('secondary')
            r.addWidget(preview)
            self.combos[category]=combo;self.preview_buttons[category]=preview
            line.addLayout(r)
            samples.layout().addWidget(p)
        body.addWidget(samples)
        controls,content=panel()
        content.addWidget(text('Mezcla de sonido','headline'))
        grid=QHBoxLayout();grid.setSpacing(12)
        volume_col=QVBoxLayout();vol_head=QHBoxLayout();vol_head.addWidget(text('Volumen'));vol_head.addStretch();self.vol_label=text('76 %','value');vol_head.addWidget(self.vol_label)
        volume_col.addLayout(vol_head)
        self.vol_slider=QSlider(Qt.Orientation.Horizontal);self.vol_slider.setRange(0,100);self.vol_slider.setValue(self.settings['volume'])
        volume_col.addWidget(self.vol_slider);grid.addLayout(volume_col,1)
        speed_col=QVBoxLayout();speed_head=QHBoxLayout();speed_head.addWidget(text('Velocidad + tono'));speed_head.addStretch();self.speed_label=text('1.00×','value');speed_head.addWidget(self.speed_label)
        speed_col.addLayout(speed_head)
        self.speed_slider=QSlider(Qt.Orientation.Horizontal);self.speed_slider.setRange(45,120);self.speed_slider.setSingleStep(5);self.speed_slider.setPageStep(5);self.speed_slider.setValue(self.settings['speed'])
        speed_col.addWidget(self.speed_slider);grid.addLayout(speed_col,1)
        content.addLayout(grid)
        content.addWidget(text('Mover la velocidad también cambia el tono, como acelerar una grabación. La velocidad inicial es 0,65×. Baja a 0,50× para dibujar aún más despacio.','muted'))
        body.addWidget(controls)
        options,option_layout=panel()
        option_layout.addWidget(text('En segundo plano','headline'))
        self.start_check=QCheckBox('Iniciar automáticamente al entrar a Windows')
        self.start_check.setChecked(self.settings['start_at_login'])
        option_layout.addWidget(self.start_check)
        self.close_check=QCheckBox('Cerrar la ventana = ocultarla en la bandeja')
        self.close_check.setChecked(self.settings['close_to_tray'])
        option_layout.addWidget(self.close_check)
        option_layout.addWidget(text('El icono junto al reloj permite volver a abrir la ventana, silenciar o salir. La configuración se guarda en tu computadora.','muted'))
        body.addWidget(options)
        body.addWidget(text('Kaoru Ink 0.1 · Inspirado en Mechvibes · Solo Windows · El sonido requiere Clip Studio Paint en primer plano.','muted'))
        body.addStretch()
        scroll.setWidget(inner);root.addWidget(scroll,1)
        self.vol_label.setText(f"{self.settings['volume']} %")
        self.speed_label.setText(f"{self.settings['speed']/100:.2f}×")

    def _tray(self,icon_path):
        self.tray=QSystemTrayIcon(QIcon(str(icon_path)),self)
        self.tray.setToolTip('Kaoru Ink · esperando Clip Studio Paint')
        menu=QMenu()
        open_action=QAction('Abrir Kaoru Ink',self);open_action.triggered.connect(self._show)
        self.mute_action=QAction('Silenciar',self);self.mute_action.triggered.connect(self._toggle_mute)
        exit_action=QAction('Salir por completo',self);exit_action.triggered.connect(self.quit_app)
        menu.addAction(open_action);menu.addAction(self.mute_action);menu.addSeparator();menu.addAction(exit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason:self._show() if reason in (QSystemTrayIcon.ActivationReason.DoubleClick,QSystemTrayIcon.ActivationReason.Trigger) else None)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def _wiring(self):
        self.bus.down.connect(self._on_down)
        self.bus.moved.connect(self._on_move)
        self.bus.up.connect(self.controller.mouse_up)
        self.bus.tool.connect(self._set_mode)
        self.pencil_button.clicked.connect(lambda:self._set_mode('pencil'))
        self.brush_button.clicked.connect(lambda:self._set_mode('brush'))
        for category,setting in [('short','short_id'),('medium','medium_id'),('long','long_id'),('brush','brush_id')]:
            self.combos[category].currentIndexChanged.connect(lambda _,c=category,k=setting:self._selected(c,k))
            self.preview_buttons[category].clicked.connect(lambda _,c=category:self._preview(c))
        self.vol_slider.valueChanged.connect(self._volume)
        self.speed_slider.valueChanged.connect(self._speed)
        self.start_check.toggled.connect(self._start_change)
        self.close_check.toggled.connect(self._close_change)

    def _selected(self,category,setting):
        self.settings[setting]=self.combos[category].currentData()
        config.save(self.settings)
        if category == 'brush':
            self.audio.refresh_live_loop(category,self.settings[setting])

    def _preview(self,category):
        name=self.audio.preview(category,self.combos[category].currentData())
        self.status.setText('▶ Prueba: '+name)
        QTimer.singleShot(1000,self._update_status)

    def _volume(self,value):
        self.vol_label.setText(f'{value} %');self.settings['volume']=value
        self.audio.set_volume(value);config.save(self.settings)

    def _speed(self,value):
        self.speed_label.setText(f'{value/100:.2f}×');self.settings['speed']=value
        self.audio.stop_stroke();self.audio.set_speed(value);config.save(self.settings)

    def _start_change(self,enabled):
        try:
            applied=config.set_startup(enabled)
            if enabled and not applied:
                QMessageBox.information(self,'Inicio con Windows','El inicio automático se registrará al ejecutar el archivo KaoruInk.exe, no en el entorno de desarrollo.')
            self.settings['start_at_login']=enabled
            config.save(self.settings)
        except OSError as ex:
            self.start_check.blockSignals(True);self.start_check.setChecked(not enabled);self.start_check.blockSignals(False)
            QMessageBox.warning(self,'Inicio automático',str(ex))

    def _close_change(self,enabled):
        self.settings['close_to_tray']=enabled;config.save(self.settings)

    def _toggle_mute(self):
        self.muted=not self.muted
        self.audio.muted=self.muted
        if self.muted:self.audio.stop_all()
        self.audio.refresh_volume()
        self.mute_button.setText('Activar sonido' if self.muted else 'Silenciar')
        self.mute_action.setText('Activar sonido' if self.muted else 'Silenciar')
        self._update_status()

    def _on_down(self,x,y):
        if self.focused and not self.muted:self.controller.mouse_down(x,y)

    def _on_move(self,x,y):
        if self.focused and not self.muted and foreground_paint():
            self.controller.mouse_move(x,y)
        else:
            self.controller.mouse_up()

    def _set_mode(self,mode):
        self.controller.change_mode(mode)
        self.pencil_button.setChecked(mode=='pencil')
        self.brush_button.setChecked(mode=='brush')
        self._update_status()

    def _tick(self):
        try:
            now=foreground_paint()
            if now!=self.focused:
                self.focused=now
                if not now:self.audio.stop_all()
                self._update_status()
            self.controller.tick(self.focused and not self.muted)
        except Exception as ex:
            self.status.setText('No se pudo comprobar Clip Studio: '+str(ex))

    def _update_status(self):
        mode='Lápiz (P)' if self.controller.mode=='pencil' else 'Pincel (B)'
        if self.muted: status='● Silenciado · '+mode
        elif self.focused: status='● Clip Studio Paint activo · '+mode
        else: status='○ Esperando Clip Studio Paint en primer plano'
        self.status.setText(status)
        self.tray.setToolTip('Kaoru Ink · '+status)

    def _show(self):
        self.showNormal();self.raise_();self.activateWindow()

    def closeEvent(self,event):
        if not self.is_quitting and self.settings['close_to_tray'] and self.tray.isVisible():
            self.hide();event.ignore();return
        self.quit_app();event.accept()

    def quit_app(self):
        self.is_quitting=True
        if hasattr(self,'timer'):self.timer.stop()
        self.controller.disable()
        self.monitor.stop()
        self.audio.close()
        self.tray.hide()
        self.app.quit()
