from __future__ import annotations

import math
from typing import Literal

import numpy as np

SQRT_2PI = math.sqrt(2.0 * math.pi)
DAYS_PER_YEAR = 365.0


def _phi(x: np.ndarray) -> np.ndarray:
    return np.exp(-0.5 * x * x) / SQRT_2PI


def _d1_d2(forward: np.ndarray, strike: np.ndarray, t_years: np.ndarray, sigma: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    eps = 1e-12
    sqrt_t = np.sqrt(np.maximum(t_years, eps))
    vol_t = np.maximum(sigma * sqrt_t, eps)
    d1 = (np.log(np.maximum(forward, eps) / np.maximum(strike, eps)) + 0.5 * sigma * sigma * t_years) / vol_t
    return d1, d1 - sigma * sqrt_t


def vanna_black76(
    forward: np.ndarray,
    strike: np.ndarray,
    t_years: np.ndarray,
    sigma: np.ndarray,
    rate: np.ndarray | float = 0.0,
    *,
    per_vol_point: bool = True,
) -> np.ndarray:
    """d(delta)/d(volatility) under Black-76, call/put identical.

    sigma is decimal volatility (0.20 = 20%). By default output is delta change
    per one volatility percentage point, matching common trading presentation.
    """
    d1, d2 = _d1_d2(forward, strike, t_years, sigma)
    disc = np.exp(-np.asarray(rate) * t_years)
    raw = -disc * _phi(d1) * d2 / np.maximum(sigma, 1e-12)
    return raw / 100.0 if per_vol_point else raw


def delta_black76(
    option_type: Literal["CE", "PE"],
    forward: np.ndarray,
    strike: np.ndarray,
    t_years: np.ndarray,
    sigma: np.ndarray,
    rate: np.ndarray | float = 0.0,
) -> np.ndarray:
    d1, _ = _d1_d2(forward, strike, t_years, sigma)
    disc = np.exp(-np.asarray(rate) * t_years)
    # numpy has no guaranteed erf ufunc across minimal builds; math.erf vectorized
    cdf = 0.5 * (1.0 + np.vectorize(math.erf, otypes=[float])(d1 / math.sqrt(2.0)))
    return disc * cdf if option_type == "CE" else disc * (cdf - 1.0)


def charm_black76_per_day(
    option_type: Literal["CE", "PE"],
    forward: np.ndarray,
    strike: np.ndarray,
    t_years: np.ndarray,
    sigma: np.ndarray,
    rate: np.ndarray | float = 0.0,
) -> np.ndarray:
    """Stable finite-difference charm: one-calendar-day delta decay.

    We intentionally compute a bounded finite difference rather than hard-code
    a fragile closed-form sign convention. This is vectorized and deterministic.
    Positive output means delta increases after one calendar day passes with F,
    sigma and r held constant. Expiry-day rows are returned as 0.
    """
    day = 1.0 / DAYS_PER_YEAR
    t0 = np.maximum(t_years, 0.0)
    t1 = np.maximum(t0 - day, 1e-12)
    d0 = delta_black76(option_type, forward, strike, np.maximum(t0, 1e-12), sigma, rate)
    d1 = delta_black76(option_type, forward, strike, t1, sigma, rate)
    out = d1 - d0
    return np.where(t0 <= day, 0.0, out)
