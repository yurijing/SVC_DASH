"""Q-Table heatmap visualization widget."""

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt


class QTableHeatmap(QTableWidget):
    """Displays Q-Learning Q-Table as a color-coded heatmap.

    Cells are colored on a blue (low) to red (high) gradient.
    The currently active state row is highlighted.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlternatingRowColors(False)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().setVisible(False)
        self._current_row = -1

    def update_qtable(self, qtable_data):
        """Rebuild the table from Q-Table data.

        Args:
            qtable_data: 2D list [state][action] of Q values.
        """
        if not qtable_data:
            return

        n_states = len(qtable_data)
        n_actions = len(qtable_data[0]) if n_states > 0 else 0

        self.setRowCount(n_states)
        self.setColumnCount(n_actions)

        # Column headers
        for a in range(n_actions):
            self.setHorizontalHeaderItem(a, QTableWidgetItem("L{}".format(a)))

        # Find global min/max for color scaling
        all_vals = [v for row in qtable_data for v in row]
        min_val = min(all_vals) if all_vals else 0
        max_val = max(all_vals) if all_vals else 1
        val_range = max_val - min_val if max_val != min_val else 1

        for s in range(n_states):
            for a in range(n_actions):
                val = qtable_data[s][a]
                item = QTableWidgetItem("{:.2f}".format(val))
                item.setTextAlignment(Qt.AlignCenter)

                # Color: blue (low) -> white (middle) -> red (high)
                ratio = (val - min_val) / val_range
                if ratio < 0.5:
                    # Blue to white
                    r = int(ratio * 2 * 255)
                    g = int(ratio * 2 * 255)
                    b = 255
                else:
                    # White to red
                    r = 255
                    g = int((1 - ratio) * 2 * 255)
                    b = int((1 - ratio) * 2 * 255)
                item.setBackground(QColor(r, g, b, 100))
                self.setItem(s, a, item)

    def highlight_row(self, row):
        """Highlight a specific state row."""
        self._current_row = row
        self.selectRow(row)
