"""StrategyContext — centralized strategy lifecycle for download pipelines.

Encapsulates the create → select → update → finalize pattern.
"""
from strategy import create_strategy


class StrategyContext:
    """Encapsulates strategy creation and lifecycle.

    Usage:
        ctx = StrategyContext("fixed", thresholds=[1e6, 3e6, 8e6], fixed_quality=0)
        layer = ctx.select_layer(seg=0, bandwidth=2e6, buffer_size=5,
                                 thresholds=[1e6, 3e6, 8e6])
        ctx.update_state(buffer_size=5, bandwidth=2e6)
        ctx.finalize()
    """

    def __init__(self, name, thresholds, buffer_length=10, total_seq=0,
                 fixed_quality=0):
        """Create and configure the strategy.

        Args:
            name: str - strategy name (currently only 'fixed' available)
            thresholds: list of float - cumulative bandwidth thresholds (bps)
            buffer_length: int - maximum buffer size in segments
            total_seq: int - total number of segments in the video
            fixed_quality: int - quality layer to always select
        """
        self._strategy = create_strategy(name, quality=fixed_quality)

    # ── Delegated interface ──

    @property
    def name(self):
        return self._strategy.name

    def select_layer(self, seg_number, bandwidth, buffer_size, layer_thresholds):
        return self._strategy.select_layer(
            seg_number, bandwidth, buffer_size, layer_thresholds)

    def update_state(self, buffer_size, bandwidth):
        self._strategy.update_state(buffer_size, bandwidth)

    def finalize(self):
        self._strategy.finalize()

    def reset(self):
        self._strategy.reset()
