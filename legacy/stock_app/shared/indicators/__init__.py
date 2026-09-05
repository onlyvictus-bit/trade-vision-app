"""
shared.indicators — single import point for all indicator compute functions.

Usage:
    from shared.indicators.pta import hma, fisher, rsx, mfi, cmf, vortex, aroon, tsi, kdj, squeeze
    from shared.indicators.patterns import sr_levels, trendline_proximity

Nothing here imports from server.py — safe for use in research/signals/ without circular deps.
"""
