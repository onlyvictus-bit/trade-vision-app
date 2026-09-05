"""
CORE ENGINE - Horizontal Support/Resistance using DBSCAN (Production Upgrade)
Replaces K-Means with DBSCAN for more natural, adaptive S/R zones.
"""
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

def get_horizontal_sr_levels(prices: np.ndarray, eps: float = 0.015, min_samples: int = 3) -> np.ndarray:
    if len(prices) < min_samples:
        return np.array([])
    prices = prices.reshape(-1, 1)
    prices_scaled = StandardScaler().fit_transform(prices)
    model = DBSCAN(eps=eps, min_samples=min_samples).fit(prices_scaled)
    labels = model.labels_
    levels = []
    for label in set(labels):
        if label == -1:
            continue
        cluster_prices = prices[labels == label].flatten()
        levels.append(np.mean(cluster_prices))
    return np.sort(np.array(levels))


def get_horizontal_sr_with_strength(prices: np.ndarray, eps: float = 0.015,
                                     min_samples: int = 3) -> list:
    if len(prices) < min_samples:
        return []
    prices_arr = prices.reshape(-1, 1)
    prices_scaled = StandardScaler().fit_transform(prices_arr)
    model = DBSCAN(eps=eps, min_samples=min_samples).fit(prices_scaled)
    labels = model.labels_
    result = []
    for label in set(labels):
        if label == -1:
            continue
        cluster_prices = prices_arr[labels == label].flatten()
        result.append({"price": float(np.mean(cluster_prices)), "touches": int(len(cluster_prices))})
    result.sort(key=lambda x: x["price"])
    return result
