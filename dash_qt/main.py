"""Entry point for the DASH Qt GUI application.

Usage:
    python -m dash_qt.main
    or:
    python dash_qt/main.py
"""
import sys
from PySide6.QtWidgets import QApplication

from dash_qt.models.stream_session import StreamSession
from dash_qt.models.app_config import AppConfig
from dash_qt.main_window import MainWindow


def main():
    """Launch the DASH player GUI."""
    app = QApplication(sys.argv)
    app.setApplicationName("DASH Adaptive Player")
    app.setOrganizationName("DASHPlayer")

    session = StreamSession()
    config = AppConfig()

    window = MainWindow(session, config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
