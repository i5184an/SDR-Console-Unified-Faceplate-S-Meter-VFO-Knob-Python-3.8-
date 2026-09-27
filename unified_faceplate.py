import sys
import math
import re
import serial
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QRadialGradient, QFont, QPainterPath, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QGridLayout, QStackedWidget, QSizePolicy
)

# ==================== 1. S-METER ANALOGICO SUPERIORE (CON SMORZAMENTO AGO) ====================
class ImageMeterWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 110)
        self.s_value = 0.0          # Valore visivo attuale (animato)
        self.target_s_value = 0.0   # Valore target ricevuto dalla seriale
        self.skin_filename = "imageyellow.png"
        self.pixmap = QPixmap(self.skin_filename)
        if not self.pixmap.isNull():
            self.setFixedSize(320, int(320 * self.pixmap.height() / self.pixmap.width()))
        else:
            self.setFixedSize(320, 110)

        # Timer dedicato per la fluidità del movimento dell'ago (~33 fps)
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(20)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start()

    def set_skin(self, filename):
        self.skin_filename = filename
        self.pixmap = QPixmap(filename)
        if not self.pixmap.isNull():
            self.setFixedSize(320, int(320 * self.pixmap.height() / self.pixmap.width()))
        self.update()

    def set_s_value(self, val):
        # Imposta il target; l'animazione penserà a rincorrerlo fluidamente
        self.target_s_value = max(0.0, min(15.0, val))

    def update_animation(self):
        # Interpolazione lineare (LERP) per un movimento morbido e realistico dell'ago
        diff = self.target_s_value - self.s_value
        if abs(diff) > 0.01:
            self.s_value += diff * 0.15  # Regola 0.25 per variare la velocità di smorzamento
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        if not self.pixmap.isNull():
            painter.drawPixmap(0, 0, w, h, self.pixmap)
        else:
            painter.fillRect(0, 0, w, h, QColor("#1e2227"))

        # Coordinate perno ago proporzionali
        cx = w * 0.50
        cy = h * 0.95

        degrees = -58
        if self.s_value <= 9:
            degrees = -58 + (self.s_value * (58 / 9))
        else:
            overS9 = self.s_value - 9
            degrees = 0 + (overS9 * 7.5)
        degrees = max(-62, min(50, degrees))

        length = h * 0.85
        angle_rad = math.radians(degrees)
        tip_x = cx + length * math.sin(angle_rad)
        tip_y = cy - length * math.cos(angle_rad)

        painter.setPen(QPen(QColor("#dc2626"), 2))
        painter.drawLine(QPointF(cx, cy), QPointF(tip_x, tip_y))
        
        # Perno centrale
        painter.setBrush(QBrush(QColor("#1e293b")))
        painter.setPen(QPen(QColor("#475569"), 1.5))
        painter.drawEllipse(QPointF(cx, cy), 5, 5)


# ==================== 2. DIAL ROTATIVO VFO ====================
class RotaryDialWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(140, 140)
        self.setMaximumSize(180, 180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.dial_angle = 0.0
        self.is_dragging = False
        self.last_mouse_angle = 0.0
        self.on_rotate_callback = None

    def get_mouse_angle(self, event):
        center = QPointF(self.width() / 2, self.height() / 2)
        pos = event.pos()
        return math.degrees(math.atan2(pos.y() - center.y(), pos.x() - center.x()))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.last_mouse_angle = self.get_mouse_angle(event)

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            current_angle = self.get_mouse_angle(event)
            delta = current_angle - self.last_mouse_angle
            if delta > 180: delta -= 360
            if delta < -180: delta += 360
            self.last_mouse_angle = current_angle
            self.dial_angle = (self.dial_angle + delta) % 360
            if self.on_rotate_callback:
                self.on_rotate_callback(delta)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = False

    def wheelEvent(self, event):
        delta = 10 if event.angleDelta().y() > 0 else -10
        self.dial_angle = (self.dial_angle + delta) % 360
        if self.on_rotate_callback:
            self.on_rotate_callback(10 if event.angleDelta().y() > 0 else -10)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        outer_radius = min(cx, cy) - 6

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.dial_angle)

        skirt_grad = QRadialGradient(-10, -10, outer_radius)
        skirt_grad.setColorAt(0, QColor("#565a5e"))
        skirt_grad.setColorAt(0.6, QColor("#31363b"))
        skirt_grad.setColorAt(1, QColor("#1a1d20"))
        painter.setBrush(QBrush(skirt_grad))
        painter.setPen(QPen(QColor("#111"), 1.5))
        painter.drawEllipse(QPointF(0, 0), outer_radius, outer_radius)

        for i in range(40):
            deg = i * 9
            rad = math.radians(deg)
            is_major = (i % 5 == 0)
            tick_len = max(4, int(outer_radius * 0.12)) if is_major else max(2, int(outer_radius * 0.06))
            painter.setPen(QPen(QColor("#3daee9" if is_major else "#aaa"), 1.2 if is_major else 0.7))
            painter.drawLine(QPointF((outer_radius - 3) * math.cos(rad), (outer_radius - 3) * math.sin(rad)),
                             QPointF((outer_radius - 3 - tick_len) * math.cos(rad), (outer_radius - 3 - tick_len) * math.sin(rad)))
        painter.restore()
        
        knob_r = outer_radius - max(12, int(outer_radius * 0.28))
        knob_grad = QRadialGradient(cx - 4, cy - 4, knob_r)
        knob_grad.setColorAt(0, QColor("#3d4248"))
        knob_grad.setColorAt(1, QColor("#1f2328"))
        painter.setBrush(QBrush(knob_grad))
        painter.setPen(QPen(QColor("#111"), 1.5))
        painter.drawEllipse(QPointF(cx, cy), knob_r, knob_r)

        painter.setPen(QPen(QColor("#3daee9"), 2.5, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(int(cx), int(cy - outer_radius - 3), int(cx), int(cy - outer_radius + 5))


# ==================== 3. FINESTRA PRINCIPALE UNIFICATA ====================
class UnifiedRadioFaceplateApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_frequency = 11770000
        self.current_step = 100
        self.input_buffer = ""
        self.is_pinned = True
        self.serial_port = None

        self.init_ui()
        
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(250)
        self.poll_timer.timeout.connect(self.poll_cat_status)
        self.init_serial()

    def init_ui(self):
        self.setWindowTitle("SDR S-Meter & VFO Faceplate (Unified)")
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1d20; }
            QWidget { color: #eff0f1; font-family: 'Segoe UI', Tahoma, sans-serif; font-size: 11px; }
            QPushButton { background-color: #31363b; border: 1px solid #555; border-radius: 3px; padding: 4px; color: #eff0f1; }
            QPushButton:hover { background-color: #3daee9; color: #1a1d20; border-color: #3daee9; font-weight: bold; }
            QPushButton:checked { background-color: #232629; border: 1px solid #3daee9; color: #3daee9; font-weight: bold; }
            QLineEdit { background-color: #111417; border: 1px solid #31363b; color: #3daee9; font-family: 'Consolas'; padding: 3px; border-radius: 3px; }
        """)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        # ---------------------------------------------------------
        # A. HEADER SUPERIORE (S-Meter & Skin Selector)
        # ---------------------------------------------------------
        smeter_header = QHBoxLayout()
        self.sig_label = QLabel("SIGNAL: S 0")
        self.sig_label.setStyleSheet("color: #22d3ee; font-weight: bold; font-family: 'Courier';")
        smeter_header.addWidget(self.sig_label)
        smeter_header.addStretch()
        
        self.live_lbl = QLabel("● CAT LIVE")
        self.live_lbl.setStyleSheet("color: #34d399; font-size: 9px; font-weight: bold;")
        smeter_header.addWidget(self.live_lbl)
        main_layout.addLayout(smeter_header)

        # Skin switcher buttons
        skin_frame = QHBoxLayout()
        skins = [("Yellow", "imageyellow.png"), ("White", "imagewhite.png"), ("Blue", "imageblue.png"), ("Black", "imageblack.png"), ("Green", "imagegreen.png")]
        self.skin_buttons = {}
        for name, filename in skins:
            btn = QPushButton(name)
            btn.setStyleSheet("font-size: 9px; padding: 2px;")
            btn.clicked.connect(lambda checked, f=filename, n=name: self.change_skin(f, n))
            skin_frame.addWidget(btn)
            self.skin_buttons[name] = btn
        main_layout.addLayout(skin_frame)

        # Widget S-Meter grafico con immagine
        self.image_meter = ImageMeterWidget()
        meter_container = QHBoxLayout()
        meter_container.addStretch()
        meter_container.addWidget(self.image_meter)
        meter_container.addStretch()
        main_layout.addLayout(meter_container)

        # ---------------------------------------------------------
        # B. HEADER VFO & TAB
        # ---------------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.setSpacing(4)

        self.pin_btn = QPushButton("📌")
        self.pin_btn.setFixedSize(26, 22)
        self.pin_btn.clicked.connect(self.toggle_pin)
        header_layout.addWidget(self.pin_btn)

        self.tab_main_btn = QPushButton("Main")
        self.tab_main_btn.setCheckable(True)
        self.tab_main_btn.setChecked(True)
        self.tab_main_btn.clicked.connect(lambda: self.switch_tab(0))
        header_layout.addWidget(self.tab_main_btn)

        self.tab_setup_btn = QPushButton("Setup CAT")
        self.tab_setup_btn.setCheckable(True)
        self.tab_setup_btn.clicked.connect(lambda: self.switch_tab(1))
        header_layout.addWidget(self.tab_setup_btn)

        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # --- VIEW 0: MAIN VFO CONSOLE ---
        main_view = QWidget()
        main_vbox = QVBoxLayout(main_view)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(4)

        self.rotary_dial = RotaryDialWidget()
        self.rotary_dial.on_rotate_callback = self.handle_dial_rotation
        dial_container = QHBoxLayout()
        dial_container.addStretch()
        dial_container.addWidget(self.rotary_dial)
        dial_container.addStretch()
        main_vbox.addLayout(dial_container)

        step_layout = QHBoxLayout()
        step_layout.setSpacing(2)
        self.step_buttons = {}
        for s_val, s_text in [(1, "1 Hz"), (10, "10 Hz"), (100, "100 Hz"), (1000, "1 kHz"), (5000, "5 kHz"), (10000, "10 kHz")]:
            btn = QPushButton(s_text)
            btn.setCheckable(True)
            if s_val == 100: btn.setChecked(True)
            btn.clicked.connect(lambda checked, val=s_val: self.set_step(val))
            step_layout.addWidget(btn)
            self.step_buttons[s_val] = btn
        main_vbox.addLayout(step_layout)

        self.freq_display = QLabel("Freq: 11.770.000 Hz")
        self.freq_display.setAlignment(Qt.AlignCenter)
        self.freq_display.setStyleSheet("""
            font-size: 14px; font-family: 'Consolas'; font-weight: bold;
            background-color: #111417; border: 1px inset #31363b;
            color: #3daee9; padding: 5px; border-radius: 3px;
        """)
        main_vbox.addWidget(self.freq_display)

        keypad_layout = QGridLayout()
        keypad_layout.setSpacing(2)
        keys = [
            ('1', 0, 0), ('2', 0, 1), ('3', 0, 2), ('C', 0, 3),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2), ('⌫', 1, 3),
            ('7', 2, 0), ('8', 2, 1), ('9', 2, 2), ('.', 2, 3),
            ('0', 3, 0)
        ]
        for key_text, r, c in keys:
            btn = QPushButton(key_text)
            btn.setFont(QFont("Consolas", 9, QFont.Bold))
            if key_text in ['C', '⌫', '.']:
                btn.setStyleSheet("background-color: #232629; color: #3daee9;")
            btn.clicked.connect(lambda checked, t=key_text: self.press_key(t))
            if key_text == '0':
                keypad_layout.addWidget(btn, 3, 0, 1, 2)
            else:
                keypad_layout.addWidget(btn, r, c)

        set_btn = QPushButton("SET FREQ")
        set_btn.setStyleSheet("background-color: #2980b9; color: #fff; font-weight: bold; font-family: 'Consolas';")
        set_btn.clicked.connect(lambda: self.press_key('SET'))
        keypad_layout.addWidget(set_btn, 3, 2, 1, 2)

        main_vbox.addLayout(keypad_layout)
        self.stack.addWidget(main_view)

        # --- VIEW 1: SETUP CAT ---
        setup_view = QWidget()
        setup_vbox = QVBoxLayout(setup_view)
        setup_vbox.setSpacing(6)

        setup_vbox.addWidget(QLabel("Virtual Serial Port (COM Port):"))
        self.port_input = QLineEdit("COM6")
        setup_vbox.addWidget(self.port_input)

        setup_vbox.addWidget(QLabel("Baud Rate:"))
        self.baud_input = QLineEdit("57600")
        setup_vbox.addWidget(self.baud_input)

        setup_vbox.addWidget(QLabel("Offset S-Meter:"))
        self.offset_input = QLineEdit("0.0")
        setup_vbox.addWidget(self.offset_input)

        connect_btn = QPushButton("🔌 Riconnetti CAT")
        connect_btn.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 5px;")
        connect_btn.clicked.connect(self.init_serial)
        setup_vbox.addWidget(connect_btn)
        setup_vbox.addStretch()
        self.stack.addWidget(setup_view)

    def change_skin(self, filename, name):
        self.image_meter.set_skin(filename)

    def toggle_pin(self):
        self.is_pinned = not self.is_pinned
        if self.is_pinned:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.pin_btn.setText("📌")
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.pin_btn.setText("📍")
        self.show()

    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)
        self.tab_main_btn.setChecked(index == 0)
        self.tab_setup_btn.setChecked(index == 1)

    def set_step(self, step_val):
        self.current_step = step_val
        for s, btn in self.step_buttons.items():
            btn.setChecked(s == step_val)

    def handle_dial_rotation(self, delta):
        self.current_frequency += int(delta * (self.current_step * 0.2))
        self.update_display()
        self.send_cat_frequency()

    def update_display(self):
        formatted_freq = f"{self.current_frequency:,}".replace(",", ".")
        self.freq_display.setText(f"Freq: {formatted_freq} Hz")

    def update_display_buffer(self):
        if not self.input_buffer:
            self.update_display()
        else:
            self.freq_display.setText(f"Freq: {self.input_buffer} Hz")

    def press_key(self, val):
        if val == 'C':
            self.input_buffer = ""
            self.update_display()
            return
        if val == '⌫':
            if self.input_buffer:
                self.input_buffer = self.input_buffer[:-1]
            self.update_display_buffer()
            return
        if val == 'SET':
            if self.input_buffer:
                try:
                    clean_str = self.input_buffer.replace('.', '').replace(',', '')
                    self.current_frequency = int(clean_str)
                    self.send_cat_frequency()
                except ValueError:
                    pass
                self.input_buffer = ""
            self.update_display()
            return

        self.input_buffer += val
        self.update_display_buffer()

    def init_serial(self):
        port = self.port_input.text()
        baud = int(self.baud_input.text())
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.serial_port = serial.Serial(port, baudrate=baud, timeout=0.2)
            self.live_lbl.setText("● CAT LIVE")
            self.live_lbl.setStyleSheet("color: #34d399; font-size: 9px;")
            self.poll_timer.start()
        except Exception:
            self.live_lbl.setText("● CAT OFFLINE")
            self.live_lbl.setStyleSheet("color: #e74c3c; font-size: 9px;")

    def poll_cat_status(self):
        if not self.serial_port or not self.serial_port.is_open:
            return
        try:
            # Richiedi Frequenza (FA)
            self.serial_port.write(b"FA;")
            response = self.serial_port.read_until(b";")
            if response.startswith(b"FA") and len(response) >= 13:
                freq_str = response[2:-1].decode('ascii').strip()
                new_freq = int(freq_str)
                if new_freq != self.current_frequency:
                    self.current_frequency = new_freq
                    self.update_display()

            # Richiedi Meter (SM)
            self.serial_port.write(b"SM;")
            sm_resp = self.serial_port.read_until(b";")
            if sm_resp:
                decoded = sm_resp.decode("latin-1", errors="ignore").strip()
                match = re.search(r'SM\s*([+-]?\d+)', decoded, re.IGNORECASE)
                if match:
                    val = int(match.group(1))
                    offset = float(self.offset_input.text() or 0.0)
                    s_val = (float(val) / 2.0) + offset
                    self.image_meter.set_s_value(s_val)
                    db_over = int(round((s_val - 9) * 6))
                    lbl = f"S 9 +{db_over}dB" if s_val > 9 else f"S {max(0, round(s_val))}"
                    self.sig_label.setText(f"SIGNAL: {lbl}")
        except Exception:
            pass

    def send_cat_frequency(self):
        if not self.serial_port or not self.serial_port.is_open:
            return
        try:
            freq_str = f"FA{self.current_frequency:011d};"
            self.serial_port.write(freq_str.encode('ascii'))
        except Exception:
            pass


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = UnifiedRadioFaceplateApp()
    window.show()
    sys.exit(app.exec_())