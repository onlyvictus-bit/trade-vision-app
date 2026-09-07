"""Production-oriented, research-only ORB derivatives intelligence layer."""
from .contracts import (
    DERIVATIVES_ENGINE_VERSION,
    DerivativesContext,
    DerivativesPolicy,
    EvidenceRelation,
    FuturesSnapshot,
    Greeks,
    OptionChainSnapshot,
    OptionQuote,
    OptionStrike,
    PriceScenario,
    ScenarioAssessment,
    ScenarioKind,
    Side,
)
from .calculators import build_context, max_pain
from .openalgo import OpenAlgoDataProvider, OpenAlgoError
from .reasoning import DerivativesScenarioController
from .service import DerivativesService
from .scenario_catalog import CATALOG as FAILURE_SCENARIO_CATALOG
from .store import DerivativesStore

__all__ = [
    "DERIVATIVES_ENGINE_VERSION", "DerivativesContext", "DerivativesPolicy", "EvidenceRelation",
    "FuturesSnapshot", "Greeks", "OptionChainSnapshot", "OptionQuote", "OptionStrike", "PriceScenario",
    "ScenarioAssessment", "ScenarioKind", "Side", "build_context", "max_pain", "OpenAlgoDataProvider",
    "OpenAlgoError", "DerivativesScenarioController", "DerivativesService", "DerivativesStore", "FAILURE_SCENARIO_CATALOG",
]
