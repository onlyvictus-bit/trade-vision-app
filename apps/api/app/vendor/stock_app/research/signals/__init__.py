"""
research.signals — Signal Registry
====================================
Auto-discovers and registers all signal definitions from submodules.
Import this package to populate the global registry.
"""
from .base import SignalDefinition, SignalRegistry, registry

# Import submodules to trigger @register_signal decorators.
# v1.99 fix: the vendored package ships only base.py + pta_signals.py; the other
# modules were never copied from the source tree. Unguarded imports killed the
# whole package (circular/partial-init ImportError) and silently disabled all
# 23 PTA markers. Every submodule import is now guarded.
for _module in (
    "trend",              # 9 trend signals (source tree only)
    "momentum",           # 10 momentum signals (source tree only)
    "volatility",         # 4 volatility signals (source tree only)
    "volume",             # 3 volume signals (source tree only)
    "structure",          # 3 structure signals (source tree only)
    "pattern",            # 3 pattern signals (source tree only)
    "advanced_patterns",  # 2 pattern signals (source tree only)
):
    try:
        __import__(f"{__name__}.{_module}")  # noqa: F401
    except Exception as _e:  # noqa: BLE001 - optional modules must not kill the registry
        import warnings

        warnings.warn(f"[research.signals] {_module} skipped: {_e}", stacklevel=2)

# pandas-ta-classic signals (20 new) — gracefully skipped if pta path missing
try:
    from . import pta_signals        # noqa: F401  — 20 pta signals
except Exception as _e:
    import warnings
    warnings.warn(f"[research.signals] pta_signals skipped: {_e}", stacklevel=2)

__all__ = ["SignalDefinition", "SignalRegistry", "registry"]
