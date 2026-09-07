# Gates: prove BEL (walk-forward verification of the 09:15-09:20 combo)

> Tip: latest completed = v2.02-derivatives (914 passed 2026-09-07) per
> `docs/IMPLEMENTATION_STATUS.md`. This file covers the BEL v1.91 proof only
> (frozen evidence, still valid).

OWNS: scripts/prove_bel.py, GATES.md, data/orb_research/bel_proof_output.txt

Scope: run the v1.91 proof layer on the exact BEL discovery request and report
a walk-forward verdict with numbers. Both ELIGIBLE and BLOCKED are honest
verdicts; the gates prove a verdict with metrics exists, never a pre-decided pass.
G1 executes the prove (venv python, ~3 min) and tees output to
data/orb_research/bel_proof_output.txt; G2-G7 read that file.

- [x] G1: proof pipeline runs end-to-end on real HSTRY data and captures output
  CHECK: D:\Projects\trading-platforms\stock-app\.venv\Scripts\python.exe scripts\prove_bel.py > data\orb_research\bel_proof_output.txt 2>&1 && type data\orb_research\bel_proof_output.txt
  EXPECT: PROOF_COMPLETE
  EVIDENCE: exit=0; shell=C:\windows\system32\cmd.exe; cwd=D:\Projects\trading-platforms\stock-app\trade-vision-app; path=c6b86cc53afa/39 entries; output=VERDICT=ELIGIBLE | SAFETY research_only=True trade_allowed=False live_trading_blocked=True

- [x] G2: the discovery winner is identified with metrics
  CHECK: type data\orb_research\bel_proof_output.txt
  EXPECT: DISCOVERY best_composite=
  EVIDENCE: exit=0; shell=C:\windows\system32\cmd.exe; cwd=D:\Projects\trading-platforms\stock-app\trade-vision-app; path=c6b86cc53afa/39 entries; output=VERDICT=ELIGIBLE | SAFETY research_only=True trade_allowed=False live_trading_blocked=True

- [x] G3: chronological holdout split was applied
  CHECK: type data\orb_research\bel_proof_output.txt
  EXPECT: TRAIN_DAYS=
  EVIDENCE: exit=0; shell=C:\windows\system32\cmd.exe; cwd=D:\Projects\trading-platforms\stock-app\trade-vision-app; path=c6b86cc53afa/39 entries; output=VERDICT=ELIGIBLE | SAFETY research_only=True trade_allowed=False live_trading_blocked=True

- [x] G4: walk-forward executed with fold metrics
  CHECK: type data\orb_research\bel_proof_output.txt
  EXPECT: WALK_FORWARD_FOLDS=4
  EVIDENCE: exit=0; shell=C:\windows\system32\cmd.exe; cwd=D:\Projects\trading-platforms\stock-app\trade-vision-app; path=c6b86cc53afa/39 entries; output=VERDICT=ELIGIBLE | SAFETY research_only=True trade_allowed=False live_trading_blocked=True

- [x] G5: winner holdout metrics reported (the real unseen-data test)
  CHECK: type data\orb_research\bel_proof_output.txt
  EXPECT: WINNER_HOLDOUT trades=
  EVIDENCE: exit=0; shell=C:\windows\system32\cmd.exe; cwd=D:\Projects\trading-platforms\stock-app\trade-vision-app; path=c6b86cc53afa/39 entries; output=VERDICT=ELIGIBLE | SAFETY research_only=True trade_allowed=False live_trading_blocked=True

- [x] G6: a promotion verdict with reasons exists (ELIGIBLE or BLOCKED)
  CHECK: type data\orb_research\bel_proof_output.txt
  EXPECT: VERDICT=
  EVIDENCE: exit=0; shell=C:\windows\system32\cmd.exe; cwd=D:\Projects\trading-platforms\stock-app\trade-vision-app; path=c6b86cc53afa/39 entries; output=VERDICT=ELIGIBLE | SAFETY research_only=True trade_allowed=False live_trading_blocked=True

- [x] G7: research-only safety envelope intact
  CHECK: type data\orb_research\bel_proof_output.txt
  EXPECT: SAFETY research_only=True
  EVIDENCE: exit=0; shell=C:\windows\system32\cmd.exe; cwd=D:\Projects\trading-platforms\stock-app\trade-vision-app; path=c6b86cc53afa/39 entries; output=VERDICT=ELIGIBLE | SAFETY research_only=True trade_allowed=False live_trading_blocked=True
