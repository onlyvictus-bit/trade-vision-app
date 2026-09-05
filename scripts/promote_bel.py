"""Promote the proven BEL 09:15-09:20 combo to an active ORB playbook.

AUTH: user said "promote bel" (2026-08-26). Requires the server-stored proof
ab7b3163 (VERDICT=ELIGIBLE) - enforced by promote_orb_playbook itself.
"""

import sys

sys.path.insert(0, r"D:\Projects\trading-platforms\stock-app\trade-vision-app\apps\api")

from app.models import OrbPlaybookPromotionRequest
from app.orb import list_orb_playbooks, promote_orb_playbook

request = OrbPlaybookPromotionRequest(
    proof_id="ab7b3163-cee6-5c0c-987c-68db75717273",
    combo_id="ba1121c62248ed991403",
    promoted_by="sakth (explicit approval 2026-08-26)",
)
playbook = promote_orb_playbook(request)
print("PROMOTED")
print(f"playbook_id={playbook.playbook_id}")
print(f"symbol={playbook.symbol} timeframe={playbook.timeframe}")
print(f"combo={playbook.combo_id} proof={playbook.proof_id}")
print(f"config={playbook.config.model_dump(mode='json')}")
print(f"promoted_by={playbook.promoted_by} at {playbook.promoted_at}")

active = list_orb_playbooks(symbol="BEL", timeframe="5m")
print(f"active BEL 5m playbooks: {len(active)}")
for p in active:
    print(f"  {p.playbook_id} combo={p.combo_id}")
