import sys
import cv2
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QFileDialog, QSlider,
                             QComboBox, QSpinBox, QPushButton, QGroupBox,
                             QMessageBox, QSizePolicy)
from PyQt6.QtCore import Qt, QEvent, QSignalBlocker
from PyQt6.QtGui import QAction, QImage, QPixmap

class WatermarkApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("watermark")
        self.drag_offset = None
        self.setGeometry(100, 100, 1200, 700)
        self.background = None
        self.watermark = None
        self.result = None
        self.init_ui()

    def init_ui(self):
        # Меню
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Файл")
        act_load_bg = QAction("Загрузить фон...", self)
        act_load_bg.triggered.connect(self.load_background)
        file_menu.addAction(act_load_bg)
        act_load_wm = QAction("Загрузить водяной знак...", self)
        act_load_wm.triggered.connect(self.load_watermark)
        file_menu.addAction(act_load_wm)
        act_save = QAction("Сохранить результат...", self)
        act_save.triggered.connect(self.save_result)
        file_menu.addAction(act_save)
        file_menu.addSeparator()
        act_exit = QAction("Выход", self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        self.setStyleSheet("""
            QWidget { background: #202124; color: #f1f1f4; font-size: 14px; }
            QPushButton, QComboBox, QSpinBox { background: #393a40; border: 1px solid #53545b;
                border-radius: 7px; padding: 7px 12px; }
            QPushButton:hover { background: #46484f; }
            QPushButton#export { background: #245db6; }
            QPushButton#export:disabled { background: #36373b; color: #aaa; }
            QGroupBox { border: 1px solid #494a50; border-radius: 10px; margin-top: 12px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; }
        """)
        main_layout.setContentsMargins(20, 16, 20, 20)
        main_layout.setSpacing(14)
        toolbar = QHBoxLayout()
        for title, handler in (("Загрузить фон…", self.load_background),
                               ("Загрузить водяной знак…", self.load_watermark)):
            button = QPushButton(title)
            button.clicked.connect(handler)
            toolbar.addWidget(button)
        toolbar.addStretch()
        self.save_button = QPushButton("Сохранить результат…")
        self.save_button.setObjectName("export")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_result)
        toolbar.addWidget(self.save_button)
        main_layout.addLayout(toolbar)

        # Область изображений
        img_layout = QHBoxLayout()
        self.lbl_bg = QLabel("Фон")
        self.lbl_bg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_bg.setStyleSheet("background: #292a2e; border: 1px solid #45464c; border-radius: 10px;")
        self.lbl_bg.setScaledContents(True)
        self.lbl_wm = QLabel("Водяной знак")
        self.lbl_wm.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_wm.setStyleSheet("background: #292a2e; border: 1px solid #45464c; border-radius: 10px;")
        self.lbl_wm.setScaledContents(True)
        self.lbl_result = QLabel("Результат")
        self.lbl_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_result.setStyleSheet("background: #292a2e; border: 1px solid #45464c; border-radius: 10px;")
        self.lbl_result.setScaledContents(True)
        self.lbl_result.installEventFilter(self)
        self.lbl_result.setToolTip("Перетащите водяной знак левой кнопкой мыши")
        for preview in (self.lbl_bg, self.lbl_wm, self.lbl_result):
            preview.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
            img_layout.addWidget(preview, 1)
        main_layout.addLayout(img_layout, stretch=1)

        # Панель управления
        control_layout = QHBoxLayout()
        group_pos = QGroupBox("Позиция")
        pos_layout = QVBoxLayout()
        self.combo_pos = QComboBox()
        self.combo_pos.addItems(["Левый верх", "Правый верх", "Левый низ", "Правый низ", "Центр", "Произвольно"])
        self.combo_pos.currentTextChanged.connect(self.on_position_changed)
        pos_layout.addWidget(self.combo_pos)
        hbox_xy = QHBoxLayout()
        hbox_xy.addWidget(QLabel("X:"))
        self.spin_x = QSpinBox()
        self.spin_x.setRange(0, 10000)
        self.spin_x.setEnabled(False)
        self.spin_x.valueChanged.connect(self.process_watermark)
        hbox_xy.addWidget(self.spin_x)
        hbox_xy.addWidget(QLabel("Y:"))
        self.spin_y = QSpinBox()
        self.spin_y.setRange(0, 10000)
        self.spin_y.setEnabled(False)
        self.spin_y.valueChanged.connect(self.process_watermark)
        hbox_xy.addWidget(self.spin_y)
        pos_layout.addLayout(hbox_xy)
        group_pos.setLayout(pos_layout)
        control_layout.addWidget(group_pos)

        group_alpha = QGroupBox("Прозрачность")
        alpha_layout = QVBoxLayout()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(50)
        self.slider.setTracking(False)
        self.slider.valueChanged.connect(self.process_watermark)
        alpha_layout.addWidget(self.slider)
        self.lbl_alpha_val = QLabel("50%")
        alpha_layout.addWidget(self.lbl_alpha_val)
        group_alpha.setLayout(alpha_layout)
        control_layout.addWidget(group_alpha)

        group_mode = QGroupBox("Режим")
        mode_layout = QVBoxLayout()
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Ручной (NumPy)", "Библиотечный (OpenCV)"])
        self.combo_mode.currentIndexChanged.connect(self.process_watermark)
        mode_layout.addWidget(self.combo_mode)
        group_mode.setLayout(mode_layout)
        control_layout.addWidget(group_mode)


        control_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        main_layout.addLayout(control_layout)

    def load_background(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите фоновое изображение", "",
                                              "Images (*.png *.jpg *.jpeg *.bmp)")
        if not path:
            return
        img = self.read_image(path, cv2.IMREAD_COLOR)
        if img is None:
            self.show_error("Не удалось открыть фоновое изображение.")
            return
        self.background = img
        self.display_image(img, self.lbl_bg)
        self.process_watermark()

    def load_watermark(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите водяной знак", "",
                                              "Images (*.png *.jpg *.jpeg *.bmp)")
        if not path:
            return
        img = self.read_image(path, cv2.IMREAD_UNCHANGED)
        if img is None:
            self.show_error("Не удалось открыть изображение водяного знака.")
            return
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.ndim == 3 and img.shape[2] == 2:
            self.show_error("Формат изображения водяного знака не поддерживается.")
            return
        self.watermark = img
        self.display_image(img, self.lbl_wm, is_bgra=(len(img.shape)==3 and img.shape[2]==4))
        self.process_watermark()

    def display_image(self, img, label, is_bgra=False):
        if img.ndim == 2:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        elif is_bgra:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
        else:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        bytes_per_line = ch * w
        q_img = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        label.setPixmap(pixmap.scaled(label.width(), label.height(),
                       Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation))

    def eventFilter(self, widget, event):
        if widget is not getattr(self, "lbl_result", None) or self.result is None:
            return super().eventFilter(widget, event)
        kind = event.type()
        if kind == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = None
        if kind not in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseMove):
            return super().eventFilter(widget, event)
        if not event.buttons() & Qt.MouseButton.LeftButton:
            return False
        rect = widget.contentsRect()
        if rect.isEmpty():
            return False
        height, width = self.result.shape[:2]
        px = (event.position().x() - rect.x()) * width / rect.width()
        py = (event.position().y() - rect.y()) * height / rect.height()
        if kind == QEvent.Type.MouseButtonPress:
            x, y, w, h, _, _ = self.prepare_overlay(
                self.background, self.watermark, self.spin_x.value(),
                self.spin_y.value(), self.combo_pos.currentText())
            if x <= px < x + w and y <= py < y + h:
                self.drag_offset = (px - x, py - y, w, h)
            return self.drag_offset is not None
        if self.drag_offset is None:
            return False
        dx, dy, w, h = self.drag_offset
        with QSignalBlocker(self.combo_pos), QSignalBlocker(self.spin_x), QSignalBlocker(self.spin_y):
            self.combo_pos.setCurrentText("Произвольно")
            self.spin_x.setMaximum(width - w)
            self.spin_y.setMaximum(height - h)
            self.spin_x.setValue(round(px - dx))
            self.spin_y.setValue(round(py - dy))
        self.on_position_changed("Произвольно")
        return True

    def on_position_changed(self, text):
        if text == "Произвольно":
            self.spin_x.setEnabled(True)
            self.spin_y.setEnabled(True)
        else:
            self.spin_x.setEnabled(False)
            self.spin_y.setEnabled(False)
        self.process_watermark()

    @staticmethod
    def read_image(path, flags):
        """Read paths containing non-ASCII characters on Windows as well."""
        try:
            data = np.fromfile(path, dtype=np.uint8)
            return cv2.imdecode(data, flags)
        except (OSError, cv2.error):
            return None

    @staticmethod
    def show_error(message):
        QMessageBox.critical(None, "Ошибка", message)

    @staticmethod
    def prepare_overlay(bg, wm, x, y, pos):
        H, W = bg.shape[:2]
        h, w = wm.shape[:2]
        # Preserve aspect ratio when the watermark is larger than the background.
        scale = min(1.0, W / w, H / h)
        if scale < 1.0:
            wm = cv2.resize(wm, (max(1, round(w * scale)), max(1, round(h * scale))),
                            interpolation=cv2.INTER_AREA)
            h, w = wm.shape[:2]
        if len(wm.shape) == 3 and wm.shape[2] == 4:
            wm_rgb = wm[:, :, :3]
            wm_alpha = wm[:, :, 3] / 255.0
        else:
            wm_rgb = wm
            wm_alpha = np.ones((h, w), dtype=np.float32)
        if pos == "Левый верх":
            x, y = 0, 0
        elif pos == "Правый верх":
            x, y = W - w, 0
        elif pos == "Левый низ":
            x, y = 0, H - h
        elif pos == "Правый низ":
            x, y = W - w, H - h
        elif pos == "Центр":
            x, y = (W - w) // 2, (H - h) // 2
        else:
            x = max(0, min(x, W - w))
            y = max(0, min(y, H - h))
        return x, y, w, h, wm_rgb, wm_alpha

    def apply_watermark_manual(self, bg, wm, pos, alpha, x, y):
        x, y, w, h, wm_rgb, wm_alpha = self.prepare_overlay(bg, wm, x, y, pos)
        roi = bg[y:y+h, x:x+w].astype(np.float32)
        alpha_map = wm_alpha * alpha
        alpha_map = np.expand_dims(alpha_map, axis=2)
        blended = (wm_rgb.astype(np.float32) * alpha_map +
                   roi * (1 - alpha_map))
        blended = np.clip(blended, 0, 255).astype(np.uint8)
        result = bg.copy()
        result[y:y+h, x:x+w] = blended
        return result

    def apply_watermark_lib(self, bg, wm, pos, alpha, x, y):
        x, y, w, h, wm_rgb, wm_alpha = self.prepare_overlay(bg, wm, x, y, pos)
        roi = bg[y:y+h, x:x+w]
        # Apply per-pixel PNG alpha as well as the global opacity setting.
        effective_alpha = np.repeat(
            (wm_alpha.astype(np.float32) * alpha)[:, :, None], 3, axis=2)
        foreground = cv2.multiply(wm_rgb.astype(np.float32), effective_alpha)
        background = cv2.multiply(roi.astype(np.float32), 1.0 - effective_alpha)
        blended = cv2.add(foreground, background)
        blended = np.clip(blended, 0, 255).astype(np.uint8)
        result = bg.copy()
        result[y:y+h, x:x+w] = blended
        return result

    def process_watermark(self):
        if self.background is None or self.watermark is None:
            return
        alpha = self.slider.value() / 100.0
        self.lbl_alpha_val.setText(f"{int(alpha*100)}%")
        pos = self.combo_pos.currentText()
        x = self.spin_x.value()
        y = self.spin_y.value()
        mode = self.combo_mode.currentIndex()
        if mode == 0:
            result = self.apply_watermark_manual(self.background, self.watermark, pos, alpha, x, y)
        else:
            result = self.apply_watermark_lib(self.background, self.watermark, pos, alpha, x, y)
        self.result = result
        self.save_button.setEnabled(True)
        self.display_image(result, self.lbl_result)

    def save_result(self):
        if self.result is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить результат", "",
                                              "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            try:
                extension = path.rsplit(".", 1)[-1]
                success, encoded = cv2.imencode(f".{extension}", self.result)
                if not success:
                    raise ValueError("Неподдерживаемый формат файла.")
                encoded.tofile(path)
            except (OSError, cv2.error, ValueError) as error:
                self.show_error(f"Не удалось сохранить изображение: {error}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WatermarkApp()
    window.show()
    sys.exit(app.exec())
