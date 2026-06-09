"""Entry point for SVC-DASH Player GUI. Kills old instances on startup."""

import sys, os, subprocess

# Kill old instances
try:
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if 'simple_main' in line and 'grep' not in line and str(os.getpid()) not in line:
            pid = line.split()[1]
            try: os.kill(int(pid), 9)
            except: pass
        if 'ffmpeg' in line and 'grep' not in line and ('BBB-I-360p' in line or 'seg_' in line):
            pid = line.split()[1]
            try: os.kill(int(pid), 9)
            except: pass
except: pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from dash_qt.simple_window import SimpleWindow
import signal
signal.signal(signal.SIGCHLD, signal.SIG_DFL)

app = QApplication(sys.argv)
app.setApplicationName("SVC-DASH Player")
window = SimpleWindow()
window.show()
sys.exit(app.exec())
