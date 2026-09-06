"""Run AFTER installing inside the real checkout. Writes factual JSON results.

This script was syntax-checked here; the full host repository was not available
in the authoring environment. It does not suppress or relabel test failures.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--full-backend',action='store_true')
    parser.add_argument('--out',default='data/afre/host-verification.json')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    env=dict(os.environ);env['PYTHONPATH']=str(root/'apps/api');env['TRADEVISION_AFRE_PROFILE']='off'
    commands=[
        [sys.executable,'-m','pytest','apps/api/tests/afre','-q'],
        [sys.executable,'-c','from app.main import app; from app.orb.adaptive.adapters import repository_gate_hash; print(repository_gate_hash()); print("Host import OK; AFRE off")'],
    ]
    if args.full_backend:commands.append([sys.executable,'-m','pytest','apps/api/tests','-q'])
    reports=[]
    for command in commands:
        result=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
        reports.append({'command':command,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
        print('PASS' if result.returncode==0 else 'FAIL', ' '.join(command))
    target=root/args.out;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({'results':reports,'all_passed':all(x['returncode']==0 for x in reports),
                                 'market_profitability_proved':False,'frontend_verified':False},indent=2),encoding='utf-8')
    return 0 if all(x['returncode']==0 for x in reports) else 1

if __name__=='__main__':raise SystemExit(main())
