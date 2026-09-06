"""Run with python -m app.orb.adaptive.cli --help (from apps/api or PYTHONPATH)."""
from __future__ import annotations
import argparse
import json
import secrets
import sys
import time
from pathlib import Path
from .contracts import Policy,AccountLimits,canonical,clock_ns
from .controller import Controller
from .research import ResearchDay,replay_day,prove_policies,ProofThresholds,ProofReport
from .governance import code_fingerprint,sign_review
from .store import Store
from .explain import markdown,html_report
from .integration import load_controller


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text((value if isinstance(value,str) else json.dumps(value,indent=2,sort_keys=True,allow_nan=False))+"\n",encoding="utf-8")


def read_days(path: str) -> tuple[ResearchDay,...]:
    return tuple(ResearchDay.model_validate(x) for x in json.loads(Path(path).read_text(encoding="utf-8")))


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description="AFRE local research; never real orders")
    commands=parser.add_subparsers(dest="command",required=True)
    d=commands.add_parser("demo",help="Run clearly synthetic failure/fade/reclaim paths")
    d.add_argument("--out",required=True)
    d.add_argument("--path",choices=["fade","fade-fails","reclaim","gap-filled"],default="fade")
    for name in ("replay","label-structural","label-actions"):
        sub=commands.add_parser(name)
        sub.add_argument("--data",required=True);sub.add_argument("--policy",required=True)
        sub.add_argument("--limits",required=True);sub.add_argument("--out",required=True)
        sub.add_argument("--forecast-model");sub.add_argument("--value-model")
        if name=="label-actions": sub.add_argument("--anchor-minute",type=int,required=True)
    p=commands.add_parser("prove",help="Registered chronological whole-policy study, no automatic promotion")
    for arg in ("data","policies","limits","holdout-start","study-id","registry-db","out"):p.add_argument("--"+arg,required=True)
    p.add_argument("--thresholds")
    for name in ("fit-frequency","fit-value"):
        sub=commands.add_parser(name)
        for arg in ("labels","train-end","out"):sub.add_argument("--"+arg,required=True)
        if name=="fit-frequency":sub.add_argument("--calibration-end",required=True);sub.add_argument("--event",choices=["PDC_TOUCH","RETURN_INSIDE_OR"],required=True)
    s=commands.add_parser("review",help="Offline operator review; refuses ineligible/synthetic proof")
    for arg in ("proof","key-file","reviewer","phrase","out"):s.add_argument("--"+arg,required=True)
    s.add_argument("--valid-days",type=int,default=30)
    bind=commands.add_parser("bind-host-d1",help="Bind existing repository D1 source and thresholds before a new study")
    bind.add_argument("--policy",required=True);bind.add_argument("--out",required=True)
    k=commands.add_parser("generate-local-secrets")
    k.add_argument("--out",required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=="bind-host-d1":
            from .adapters import repository_gate_hash
            from .contracts import evolve
            policy=Policy.model_validate_json(Path(args.policy).read_text(encoding="utf-8"))
            if policy.forecast_model_hash or policy.value_model_hash:
                raise ValueError("Bind D1 before training models; changed rules require model revalidation")
            bound=evolve(policy,host_d1_source_hash=repository_gate_hash())
            write(Path(args.out),bound.model_dump(mode="json"));print(bound.policy_hash)
        elif args.command=="generate-local-secrets":
            out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
            for name,body in (("api-token.txt",secrets.token_urlsafe(48).encode()),("review-key.bin",secrets.token_bytes(48))):
                p=out/name
                with p.open("xb") as f:f.write(body)
                try:p.chmod(0o600)
                except OSError:pass
            print("Local secrets created. Do not commit this directory or reuse its keys elsewhere.")
        elif args.command=="demo":
            from .demo import demo_day,demo_policy,demo_limits
            day=demo_day(path=args.path);c=Controller(demo_policy(),demo_limits());out=Path(args.out)
            frames=[]
            result=replay_day(day,c,retain_decisions=lambda s:frames.append(s))
            write(out/"input.synthetic.json",[day.model_dump(mode="json")])
            write(out/"policy.json",c.policy.model_dump(mode="json"));write(out/"limits.json",c.limits.model_dump(mode="json"))
            write(out/"result.json",result.model_dump(mode="json"))
            selected=[]
            for state in frames:
                for d in state.decisions.values():
                    if d.as_of_ns<=clock_ns(day.session_date,600):selected.append(d)
            write(out/"trace.jsonl","\n".join(canonical(d) for d in selected))
            write(out/"trace.md","\n\n".join(markdown(d) for d in selected))
            write(out/"trace.html",html_report(tuple(selected)))
            print(json.dumps({"source":"SYNTHETIC_NOT_MARKET_PROOF","path":args.path,"status":result.status,
                              "filled":result.entry_filled,"label":result.end_state.position.label if result.end_state.position else "NO_ENTRY",
                              "output":str(out)}))
        elif args.command in {"replay","label-structural","label-actions"}:
            c=load_controller(args.policy,args.limits,forecast_path=args.forecast_model,value_path=args.value_model)
            data=read_days(args.data)
            if args.command=="replay": records=tuple(replay_day(d,c) for d in data)
            elif args.command=="label-structural":
                from .datasets import structural_dataset
                records=structural_dataset(data,c)
            else:
                from .datasets import action_dataset
                records=action_dataset(data,c,anchor_minute=args.anchor_minute)
            write(Path(args.out),[r.model_dump(mode="json") for r in records])
            print(f"Wrote {len(records)} {args.command} records; no human-approved paper trades created.")
        elif args.command=="prove":
            data=read_days(args.data)
            policies=tuple(Policy.model_validate(x) for x in json.loads(Path(args.policies).read_text(encoding="utf-8")))
            if any(p.forecast_model_hash or p.value_model_hash for p in policies):
                raise ValueError("Model-bound studies require the Python prove_policies interface with loaded, validated providers; CLI will not silently drop models")
            limits=AccountLimits.model_validate_json(Path(args.limits).read_text(encoding="utf-8"))
            thresholds=ProofThresholds.model_validate_json(Path(args.thresholds).read_text(encoding="utf-8")) if args.thresholds else ProofThresholds()
            store=Store(args.registry_db)
            registration={"policy_hashes":[p.policy_hash for p in policies],"holdout_start":args.holdout_start,
                          "holdout_dates":[d.session_date for d in data if d.session_date>=args.holdout_start],
                          "code_hash":code_fingerprint(),"thresholds":thresholds.model_dump(mode="json")}
            store.register_trial(args.study_id,registration)
            report=prove_policies(data,tuple(Controller(p,limits,data_guard=__import__("app.orb.adaptive.adapters",fromlist=["RepositoryDataGuard"]).RepositoryDataGuard(p.host_d1_source_hash) if p.host_d1_source_hash else None) for p in policies),holdout_start=args.holdout_start,
                                  code_hash=code_fingerprint(),thresholds=thresholds)
            store.finish_trial(args.study_id,report.model_dump(mode="json"))
            write(Path(args.out),report.model_dump(mode="json"))
            print(json.dumps({"promotion_eligible":report.promotion_eligible,"blockers":report.blockers,"proof_hash":report.proof_hash}))
        elif args.command=="fit-frequency":
            from .forecasting import Label,fit_frequency_model
            labels=tuple(Label.model_validate(x) for x in json.loads(Path(args.labels).read_text(encoding="utf-8")))
            chosen=tuple(l for l in labels if l.event==args.event)
            # Do not silently omit censored labels and call the result complete.
            train=tuple(l for l in chosen if l.session_date<=args.train_end)
            cal=tuple(l for l in chosen if args.train_end<l.session_date<=args.calibration_end)
            test=tuple(l for l in chosen if l.session_date>args.calibration_end)
            model=fit_frequency_model(train,cal,test)
            write(Path(args.out),model.model_dump(mode="json"));print(model.status)
        elif args.command=="fit-value":
            from .value import ActionOutcome,fit_value_model
            labels=tuple(ActionOutcome.model_validate(x) for x in json.loads(Path(args.labels).read_text(encoding="utf-8")))
            model=fit_value_model(tuple(l for l in labels if l.session_date<=args.train_end),tuple(l for l in labels if l.session_date>args.train_end))
            write(Path(args.out),model.model_dump(mode="json"));print(model.status)
        elif args.command=="review":
            report=ProofReport.model_validate_json(Path(args.proof).read_text(encoding="utf-8"));now=time.time_ns()
            if not 1<=args.valid_days<=90:raise ValueError("Review validity must be 1 to 90 days")
            review=sign_review(report,Path(args.key_file).read_bytes(),args.reviewer,now,now+args.valid_days*86400*1_000_000_000,args.phrase)
            write(Path(args.out),review.model_dump(mode="json"));print("Signed local operator review; not a profitability guarantee.")
        return 0
    except (ValueError,OSError,KeyError,RuntimeError) as exc:
        print(f"AFRE failed closed: {exc}",file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
