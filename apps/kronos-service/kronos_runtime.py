from __future__ import annotations

import os
import random
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
import torch


SERVICE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = SERVICE_ROOT.parents[1]
UPSTREAM_ROOT = PROJECT_ROOT / "external" / "kronos"
MODEL_ROOT = SERVICE_ROOT / "models"
MODEL_PATH = MODEL_ROOT / "Kronos-mini"
TOKENIZER_PATH = MODEL_ROOT / "Kronos-Tokenizer-2k"
MODEL_ID = "NeoQuasar/Kronos-mini"
TOKENIZER_ID = "NeoQuasar/Kronos-Tokenizer-2k"
MODEL_REVISION = "local-snapshot"
MAX_CONTEXT = 2048
MODEL_CONFIGS = {
    "Kronos-mini": {
        "model_id": MODEL_ID,
        "tokenizer_id": TOKENIZER_ID,
        "model_path": MODEL_PATH,
        "tokenizer_path": TOKENIZER_PATH,
        "max_context": MAX_CONTEXT,
    },
    "Kronos-base": {
        "model_id": "NeoQuasar/Kronos-base",
        "tokenizer_id": "NeoQuasar/Kronos-Tokenizer-base",
        "model_path": MODEL_ROOT / "Kronos-base",
        "tokenizer_path": MODEL_ROOT / "Kronos-Tokenizer-base",
        "max_context": 512,
    },
}


@dataclass(frozen=True)
class RuntimeInfo:
    loaded: bool
    model_name: str
    tokenizer_name: str
    device: str
    cuda_available: bool
    gpu_name: str | None
    load_error: str | None
    max_context: int
    allocated_vram_mb: float


class KronosRuntime:
    """Owns one selected real Kronos model outside the main Trade Vision API."""

    def __init__(self) -> None:
        self._predictor = None
        self._selected_model = "Kronos-mini"
        self._load_error: str | None = None
        self._load_lock = threading.Lock()
        self._inference_lock = threading.Lock()

    def info(self, model_name: str | None = None) -> RuntimeInfo:
        selected = model_name or self._selected_model
        config = model_config(selected)
        return RuntimeInfo(
            loaded=self._predictor is not None and selected == self._selected_model,
            model_name=str(config["model_id"]),
            tokenizer_name=str(config["tokenizer_id"]),
            device=self.device,
            cuda_available=torch.cuda.is_available(),
            gpu_name=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            load_error=self._load_error,
            max_context=int(config["max_context"]),
            allocated_vram_mb=round(torch.cuda.memory_allocated() / 1024 / 1024, 2) if torch.cuda.is_available() else 0.0,
        )

    @property
    def device(self) -> str:
        requested = os.getenv("TRADEVISION_KRONOS_DEVICE")
        if requested:
            return requested
        return "cuda:0" if torch.cuda.is_available() else "cpu"

    def load(self, model_name: str = "Kronos-mini") -> RuntimeInfo:
        config = model_config(model_name)
        if self._predictor is not None and self._selected_model == model_name:
            return self.info(model_name)
        with self._load_lock:
            if self._predictor is not None and self._selected_model == model_name:
                return self.info(model_name)
            try:
                if not (UPSTREAM_ROOT / "model" / "__init__.py").exists():
                    raise FileNotFoundError(f"Upstream Kronos source missing at {UPSTREAM_ROOT}")
                model_path = Path(config["model_path"])
                tokenizer_path = Path(config["tokenizer_path"])
                if not (model_path / "model.safetensors").exists():
                    raise FileNotFoundError(f"{model_name} model missing at {model_path}")
                if not (tokenizer_path / "model.safetensors").exists():
                    raise FileNotFoundError(f"{model_name} tokenizer missing at {tokenizer_path}")
                if str(UPSTREAM_ROOT) not in sys.path:
                    sys.path.insert(0, str(UPSTREAM_ROOT))
                from model import Kronos, KronosPredictor, KronosTokenizer

                if self._predictor is not None:
                    del self._predictor
                    self._predictor = None
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                tokenizer = KronosTokenizer.from_pretrained(str(tokenizer_path))
                model = Kronos.from_pretrained(str(model_path))
                tokenizer.eval()
                model.eval()
                self._predictor = KronosPredictor(
                    model,
                    tokenizer,
                    device=self.device,
                    max_context=int(config["max_context"]),
                )
                self._selected_model = model_name
                self._load_error = None
            except Exception as exc:
                self._predictor = None
                self._load_error = f"{type(exc).__name__}: {exc}"
                raise
        return self.info(model_name)

    def predict(
        self,
        frame: pd.DataFrame,
        timestamps: pd.DatetimeIndex,
        future_timestamps: pd.DatetimeIndex,
        *,
        seed: int,
        model_name: str = "Kronos-mini",
        temperature: float = 1.0,
        top_p: float = 0.9,
        sample_count: int = 1,
    ) -> tuple[pd.DataFrame, float]:
        self.load(model_name)
        if self._predictor is None:
            raise RuntimeError(self._load_error or "Kronos predictor is unavailable.")
        self._set_seed(seed)
        started = perf_counter()
        with self._inference_lock, torch.inference_mode():
            predicted = self._predictor.predict(
                df=frame,
                x_timestamp=pd.Series(timestamps),
                y_timestamp=pd.Series(future_timestamps),
                pred_len=len(future_timestamps),
                T=temperature,
                top_p=top_p,
                sample_count=sample_count,
                verbose=False,
            )
            if torch.cuda.is_available():
                torch.cuda.synchronize()
        return repair_ohlcv(predicted), (perf_counter() - started) * 1000

    @staticmethod
    def _set_seed(seed: int) -> None:
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)


def repair_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    """Project sampled values back into physically valid, finite OHLCV candles."""

    repaired = frame.copy()
    numeric = ["open", "high", "low", "close", "volume", "amount"]
    for column in numeric:
        repaired[column] = pd.to_numeric(repaired[column], errors="coerce")
    if not np.isfinite(repaired[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Kronos returned NaN or infinite forecast values.")
    repaired["open"] = repaired["open"].clip(lower=0.01)
    repaired["close"] = repaired["close"].clip(lower=0.01)
    repaired["high"] = repaired[["open", "high", "close"]].max(axis=1)
    repaired["low"] = repaired[["open", "low", "close"]].min(axis=1).clip(lower=0.01)
    repaired["volume"] = repaired["volume"].clip(lower=0)
    repaired["amount"] = repaired["amount"].clip(lower=0)
    return repaired


RUNTIME = KronosRuntime()


def model_config(model_name: str) -> dict[str, object]:
    if model_name not in MODEL_CONFIGS:
        raise ValueError(f"Unsupported Kronos model {model_name!r}; allowed: {', '.join(MODEL_CONFIGS)}")
    return MODEL_CONFIGS[model_name]
