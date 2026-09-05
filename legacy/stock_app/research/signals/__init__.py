"""
research.signals — Signal Registry
====================================
Auto-discovers and registers all signal definitions from submodules.
Import this package to populate the global registry.
"""
from .base import SignalDefinition, SignalRegistry, registry

# Import submodules to trigger @register_signal decorators
from . import trend              # noqa: F401  — 9 trend signals
from . import momentum           # noqa: F401  — 10 momentum signals
from . import volatility         # noqa: F401  — 4 volatility signals
from . import volume             # noqa: F401  — 3 volume signals
from . import structure          # noqa: F401  — 3 structure signals
from . import pattern            # noqa: F401  — 3 pattern signals

# pandas-ta-classic signals (20 new) — gracefully skipped if pta path missing
try:
    from . import pta_signals        # noqa: F401  — 20 pta signals
except Exception as _e:
    import warnings
    warnings.warn(f"[research.signals] pta_signals skipped: {_e}", stacklevel=2)

# Advanced pattern signals (S/R + trendline proximity)
try:
    from . import advanced_patterns  # noqa: F401  — 2 pattern signals
except Exception as _e:
    import warnings
    warnings.warn(f"[research.signals] advanced_patterns skipped: {_e}", stacklevel=2)

__all__ = ["SignalDefinition", "SignalRegistry", "registry"]
