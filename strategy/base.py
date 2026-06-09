"""DASH adaptive video playback strategy base class."""

import six
from abc import ABCMeta, abstractmethod, abstractproperty


class BaseStrategy(six.with_metaclass(ABCMeta, object)):
    """Abstract base class for DASH adaptation strategies.

    Subclasses must implement select_layer() and name.
    Optionally override update_state(), reset(), and finalize().
    """

    @abstractproperty
    def name(self):
        """Unique strategy identifier string."""
        pass

    @abstractmethod
    def select_layer(self, seg_number, bandwidth, buffer_size, layer_thresholds):
        """Select the quality layer for the next segment.

        Args:
            seg_number: int - segment index (0-based)
            bandwidth: float - recent download bandwidth estimate (bps)
            buffer_size: int - number of segments currently buffered
            layer_thresholds: list of float - cumulative bandwidth thresholds
                              for each layer (bps), ascending

        Returns:
            int - selected layer index (0-based), in range [0, len(layer_thresholds))
        """
        pass

    def update_state(self, buffer_size, bandwidth):
        """Post-download learning update. Default no-op.

        Stateful strategies (e.g. Q-Learning) override this to perform
        learning updates after each segment download.

        Args:
            buffer_size: int - number of segments currently buffered
            bandwidth: float - recent download bandwidth estimate (bps)
        """
        pass

    def reset(self):
        """Reset strategy state for a new video session. Default no-op."""
        pass

    def finalize(self):
        """Post-session cleanup/reporting hook. Default no-op.

        Q-Learning strategies override this to compute convergence metrics.
        """
        pass

