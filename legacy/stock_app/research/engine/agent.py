"""Autonomous research loop."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from research.engine.runner import run_discovery


@dataclass
class AutoResearchAgent:
    max_rounds: int = 4
    patience: int = 2
    min_improvement: float = 0.005
    progress_callback: Optional[Callable[[int, int, str], None]] = None
    history: List[Dict[str, Any]] = field(default_factory=list)

    def run(self, **kwargs) -> List[Dict[str, Any]]:
        best_score = float("-inf")
        stale = 0
        best_results: List[Dict[str, Any]] = []
        base_cap = int(kwargs.pop("max_param_combos", 50))
        kwargs.pop("sweep_params", None)
        
        # Track categories for pruning
        excluded_categories: List[str] = []
        
        from research.signals import registry

        for rnd in range(1, self.max_rounds + 1):
            cap = min(500, max(base_cap, base_cap * rnd))
            if self.progress_callback:
                self.progress_callback(rnd - 1, self.max_rounds, f"Auto round {rnd}: param cap {cap}" + 
                                       (f", excluded: {excluded_categories}" if excluded_categories else ""))

            results = run_discovery(
                **kwargs,
                sweep_params=True,
                max_param_combos=cap,
                exclude_categories=excluded_categories if rnd > 1 else None,
                progress_callback=self.progress_callback,
            )
            top = results[0] if results else None
            score = float(top["composite_score"]) if top else float("-inf")
            self.history.append({"round": rnd, "score": score, "param_cap": cap, "top": top})

            # After Round 1, perform pruning
            if rnd == 1 and results:
                top_pct = results[:max(5, len(results) // 5)] # Top 20%
                active_cats = set()
                for r in top_pct:
                    for s_name in r["entry_signals"]:
                        try:
                            active_cats.add(registry.get(s_name).category)
                        except KeyError:
                            pass
                
                all_cats = set(kwargs.get("categories") or registry.categories())
                inactive_cats = all_cats - active_cats
                if inactive_cats:
                    # Only prune if we have at least 2 active categories left
                    if len(active_cats) >= 2:
                        excluded_categories = list(inactive_cats)

            if score > best_score + self.min_improvement:
                best_score = score
                best_results = results
                stale = 0
            else:
                stale += 1

            if stale >= self.patience:
                break

        if self.progress_callback:
            self.progress_callback(self.max_rounds, self.max_rounds, "Auto research done")
        return best_results


def run_auto_research(
    max_rounds: int = 4,
    patience: int = 2,
    min_improvement: float = 0.005,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    **kwargs,
) -> List[Dict[str, Any]]:
    return AutoResearchAgent(
        max_rounds=max_rounds,
        patience=patience,
        min_improvement=min_improvement,
        progress_callback=progress_callback,
    ).run(**kwargs)
