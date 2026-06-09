"""Scrollable log panel with color-coded severity levels."""

from PySide6.QtWidgets import QPlainTextEdit, QWidget, QVBoxLayout, QPushButton
from PySide6.QtGui import QTextCursor, QColor, QTextCharFormat
from PySide6.QtCore import Qt


class LogPanel(QWidget):
    """Scrollable log viewer with color-coded messages.

    Colors: ERROR=red, WARNING=orange, INFO=default.
    Auto-scrolls to bottom on new messages.
    Supports collapse/expand via toggle button.
    """

    MAX_LINES = 1000

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Toggle button
        self._toggle_btn = QPushButton("▼ Log")
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(True)
        self._toggle_btn.clicked.connect(self._toggle_log)
        layout.addWidget(self._toggle_btn)

        # Log text area
        self._text_edit = QPlainTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setMaximumBlockCount(self.MAX_LINES)
        self._text_edit.setStyleSheet(
            "font-family: Menlo, Monaco, monospace; font-size: 11px;")
        layout.addWidget(self._text_edit)

        # Color formats
        self._error_fmt = QTextCharFormat()
        self._error_fmt.setForeground(QColor("#D32F2F"))
        self._warn_fmt = QTextCharFormat()
        self._warn_fmt.setForeground(QColor("#F57C00"))
        self._info_fmt = QTextCharFormat()
        self._info_fmt.setForeground(QColor("#333333"))

    def append(self, message, level="INFO"):
        """Append a color-coded message to the log.

        Args:
            message: The log message text.
            level: One of "INFO", "WARNING", "ERROR".
        """
        cursor = self._text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)

        if level == "ERROR":
            fmt = self._error_fmt
        elif level == "WARNING":
            fmt = self._warn_fmt
        else:
            fmt = self._info_fmt

        cursor.insertText(message + "\n", fmt)

        # Auto-scroll
        self._text_edit.moveCursor(QTextCursor.End)
        self._text_edit.ensureCursorVisible()

    def _toggle_log(self, checked):
        """Show or hide the log text area."""
        self._text_edit.setVisible(checked)
        self._toggle_btn.setText("▼ Log" if checked else "▶ Log")

    def clear(self):
        """Clear all log messages."""
        self._text_edit.clear()
