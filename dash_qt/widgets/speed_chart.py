"""Real-time download speed chart using QtCharts."""

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QPen, QColor


class SpeedChart(QChartView):
    """Real-time line chart showing download speed over segments.

    Maintains a rolling window of recent data points and auto-scrolls
    the X axis as new segments are downloaded.
    """

    MAX_POINTS = 200  # Rolling window size

    def __init__(self, parent=None):
        super().__init__(parent)
        self._series = QLineSeries()
        self._series.setName("Speed (Kbps)")
        self._series.setPen(QPen(QColor("#4CAF50"), 2))

        self._chart = QChart()
        self._chart.addSeries(self._series)
        self._chart.setTitle("Download Speed")
        self._chart.setAnimationOptions(QChart.SeriesAnimations)
        self._chart.legend().setVisible(False)
        self._chart.setBackgroundBrush(Qt.white)

        # Axes
        self._axis_x = QValueAxis()
        self._axis_x.setTitleText("Segment")
        self._axis_x.setLabelFormat("%d")
        self._axis_x.setRange(0, 10)
        self._chart.addAxis(self._axis_x, Qt.AlignBottom)
        self._series.attachAxis(self._axis_x)

        self._axis_y = QValueAxis()
        self._axis_y.setTitleText("Kbps")
        self._axis_y.setLabelFormat("%.0f")
        self._axis_y.setRange(0, 100)
        self._chart.addAxis(self._axis_y, Qt.AlignLeft)
        self._series.attachAxis(self._axis_y)

        self.setChart(self._chart)
        self.setRenderHint(self.renderHints())

        self._data_count = 0

    def append(self, kbps):
        """Add a new data point and scroll the view."""
        self._data_count += 1
        self._series.append(float(self._data_count), float(kbps))

        # Trim old points
        points = self._series.points()
        if len(points) > self.MAX_POINTS:
            self._series.removePoints(0, len(points) - self.MAX_POINTS)

        # Auto-scroll X axis
        if self._data_count > self._axis_x.max():
            self._axis_x.setRange(
                max(0, self._data_count - 50),
                self._data_count + 10)

        # Auto-scale Y axis
        max_y = max(p.y() for p in self._series.points()) if points else 100
        self._axis_y.setRange(0, max(max_y * 1.2, 100))

    def reset(self):
        """Clear all data."""
        self._series.clear()
        self._data_count = 0
        self._axis_x.setRange(0, 10)
        self._axis_y.setRange(0, 100)
