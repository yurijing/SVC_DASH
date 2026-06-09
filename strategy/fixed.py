"""Fixed-quality strategy for DASH video playback."""

from strategy.base import BaseStrategy


class FixedQualityStrategy(BaseStrategy):
    """Always selects the same quality layer regardless of conditions.

    Useful for benchmarking, testing, or when bandwidth is guaranteed.
    """

    def __init__(self, quality=0):
        """Initialize with a fixed quality layer.

        Args:
            quality: Layer index to always select (0-based, default 0 = base).
        """
        self._quality = quality

    @property
    def name(self):
        return "fixed"

    def select_layer(self, seg_number, bandwidth, buffer_size, layer_thresholds):
        """Return the fixed quality, clamped to available layers.

        Args:
            seg_number: Segment index (unused).
            bandwidth: Current bandwidth (unused).
            buffer_size: Buffer occupancy (unused).
            layer_thresholds: Available layer thresholds.

        Returns:
            Fixed layer index, clamped to [0, len(thresholds)-1].
        """
        return min(self._quality, len(layer_thresholds) - 1)

    def reset(self):
        """No state to reset."""
        pass

    def finalize(self):
        """No cleanup needed."""
        pass
