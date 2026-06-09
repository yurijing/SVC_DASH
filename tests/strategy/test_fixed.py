"""Tests for FixedQualityStrategy."""
from strategy.fixed import FixedQualityStrategy


class TestFixedQualityStrategy:
    """Tests for FixedQualityStrategy."""

    def test_returns_configured_quality(self):
        """Always returns the quality set in constructor."""
        s = FixedQualityStrategy(quality=1)
        result = s.select_layer(0, 1_000_000, 5, [500_000, 1_500_000, 4_000_000])
        assert result == 1

    def test_different_quality_values_produce_different_outputs(self):
        """Constructor quality=0 vs quality=2 produce different results."""
        s0 = FixedQualityStrategy(quality=0)
        s2 = FixedQualityStrategy(quality=2)
        thresholds = [500_000, 1_500_000, 4_000_000]
        assert s0.select_layer(0, 1_000_000, 5, thresholds) == 0
        assert s2.select_layer(0, 1_000_000, 5, thresholds) == 2

    def test_clamps_to_max_available_layer(self):
        """Quality beyond available layers is clamped to last index."""
        s = FixedQualityStrategy(quality=99)
        thresholds = [500_000, 1_500_000]
        result = s.select_layer(0, 10_000_000, 5, thresholds)
        assert result == 1  # clamped to len(thresholds)-1

    def test_ignores_bandwidth_and_buffer(self):
        """Output is independent of bandwidth and buffer_size inputs."""
        s = FixedQualityStrategy(quality=1)
        thresholds = [500_000, 1_500_000, 4_000_000]
        r1 = s.select_layer(0, 100_000, 0, thresholds)
        r2 = s.select_layer(0, 100_000_000, 10, thresholds)
        assert r1 == r2 == 1

    def test_name_is_fixed(self):
        """Name property returns 'fixed'."""
        s = FixedQualityStrategy()
        assert s.name == "fixed"

    def test_reset_and_finalize_are_noops(self):
        """reset() and finalize() do not raise exceptions."""
        s = FixedQualityStrategy()
        s.reset()
        s.finalize()  # should not raise
