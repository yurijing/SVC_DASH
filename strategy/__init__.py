"""DASH video playback strategy package.

Provides a unified interface for adaptive bitrate decision strategies.

Usage:
    from strategy import create_strategy, list_strategies

    # Create a fixed-quality strategy
    strategy = create_strategy("fixed", quality=0)

    # List available strategies
    print(list_strategies())
    # ['fixed']
"""

from strategy.fixed import FixedQualityStrategy

_STRATEGY_REGISTRY = {
    'fixed': FixedQualityStrategy,
}


def create_strategy(name, **kwargs):
    """Create a strategy instance by name.

    Args:
        name: str - strategy name ('fixed')
        **kwargs: passed to the strategy constructor

    Returns:
        BaseStrategy instance

    Raises:
        ValueError: if name is not a registered strategy
    """
    if name not in _STRATEGY_REGISTRY:
        raise ValueError(
            "Unknown strategy: '{}'. Available: {}".format(
                name, list(_STRATEGY_REGISTRY.keys())))
    return _STRATEGY_REGISTRY[name](**kwargs)


def list_strategies():
    """Return list of registered strategy names."""
    return list(_STRATEGY_REGISTRY.keys())


# Import at bottom to avoid circular import (StrategyContext imports from strategy)
from strategy.context import StrategyContext  # noqa: E402
