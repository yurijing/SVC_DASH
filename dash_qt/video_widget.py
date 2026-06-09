"""VideoWidget with visible player frame and status overlay."""
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtGui import QImage, QPainter, QPen, QColor
from PySide6.QtCore import Qt


class VideoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._frame = None
        self._status = ""
        self.setMinimumSize(320, 180)
        self.setStyleSheet("background: #000; border: 2px solid #333;")

    def set_frame(self, image):
        self._frame = image
        self.update()

    def set_status(self, text):
        self._status = text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)

        # Draw frame
        if self._frame and not self._frame.isNull():
            scaled = self._frame.scaled(
                self.width()-4, self.height()-4,
                Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawImage(x, y, scaled)
        else:
            # No video — show status text
            painter.setPen(QColor("#555"))
            painter.drawText(self.rect(), Qt.AlignCenter, "DASH Player")

        # Draw border
        painter.setPen(QPen(QColor("#444"), 2))
        painter.drawRect(1, 1, self.width()-2, self.height()-2)

        # Draw status overlay at bottom
        if self._status:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 180))
            painter.drawRect(0, self.height()-28, self.width(), 28)
            painter.setPen(QColor("#0f0"))
            painter.drawText(8, self.height()-10, self._status)
