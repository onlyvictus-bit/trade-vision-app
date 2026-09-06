"""Deterministic output formats. Narration cannot edit decisions or authority."""
from __future__ import annotations
import html
import json
from .contracts import Decision


def markdown(decision: Decision) -> str:
    d=decision
    lines=[f"# {d.symbol} / {d.session_date} / {d.public_ticket}","",
           f"Action: **{d.internal_action}**",f"Policy: `{d.policy_hash}`",
           f"Snapshot: `{d.snapshot_hash}`","",
           "## Observed facts",f"PDC ever touched: {d.gap_ever_touched_pdc}",
           f"Distinct observed failed-break episodes: {d.observed_failure_episodes}","",
           "## Competing scenarios"]
    for branch in d.branches:
        lines += [f"### {branch.branch_id}: {branch.state}",
                  f"Next distinguishing evidence: {branch.next_required}",
                  f"Refuted by: {branch.refute_on}",""]
    lines += ["## Candidate policies"]
    for c in d.candidates:
        lines += [f"### {c.template}: {c.status}",f"Next trigger: {c.next_trigger}",
                  f"Reasons: {', '.join(c.reasons) or 'Frozen geometry checks passed'}",
                  f"Action value: {c.action_value_status}; lower bound: {c.lower_bound}"]
        if c.plan:
            p=c.plan
            lines += [f"Side: {p.side}; entry envelope: {p.minimum_entry} to {p.maximum_entry}; structural stop: {p.stop}",
                      f"Fixed target recipe: {p.reward_risk}R from actual fill; maximum quantity: {p.maximum_quantity}"]
        lines += [f"Challenge: {' '.join(c.challenge)}",""]
    lines += ["## Forecasts (not guarantees)"]
    for f in d.forecasts:
        lines += [f"{f.event}: {f.forecast_status}; probability={f.probability}; requested horizon={f.horizon_minutes} minutes; effective end={f.effective_end_ns}"]
    lines += ["","## Permission reasons",*d.reason_codes,"",
              "Research only. No broker order. Human approval is separate. A passing code test is not proof of a trading advantage."]
    return "\n\n".join(lines)+"\n"


def html_report(decisions: tuple[Decision,...]) -> str:
    body=[]
    for d in decisions:
        body.append('<details open><summary>'+html.escape(d.symbol+' '+d.public_ticket)+'</summary><pre>'+html.escape(markdown(d))+'</pre></details>')
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>AFRE research trace</title><style>body{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:1rem}'
            'pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px ui-monospace;line-height:1.6}summary{font-weight:700;font-size:1.2rem}</style>'
            '<h1>Adaptive ORB: auditable research trace</h1><p>No private chain-of-thought, no broker execution, no promised profitability.</p>'+''.join(body)+'</html>')
