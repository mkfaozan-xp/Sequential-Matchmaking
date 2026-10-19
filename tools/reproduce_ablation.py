"""One-component asking ablation on recorded validation worlds, not fresh evidence."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from multiprocessing import get_context
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
RESEARCH=ROOT/'research'
sys.path.insert(0,str(RESEARCH))
PLAN={'seeds':[3051,3052],
      'variants':['development','sparse','cold_start','delayed','shift','drift'],
      'methods':['conservative','no_asks'], 'members':200,
      'decision_days':60,'follow_up_days':40,
      'hypothesis':'Removing pruned hard-field clarification while retaining the same soft-score greedy allocation changes feasibility, coverage and official MSMI.',
      'scope':'Post-review diagnostic on previously observed validation worlds; no fresh-efficacy or causal population claim; policy choice fixed conservative before execution.'}


def run(task):
    from blackbox.experiment import run_episode
    from blackbox.registry import verified_episode_snapshot
    from blackbox.provenance import source_hash
    if source_hash(RESEARCH)!='65e2d14ab9d468a902af97ea79780b2523306d7b12b9414ebf7d90e9d5595bf4':
        raise ValueError('research source changed')
    seed,variant,method=task
    with verified_episode_snapshot():
        row,*_=run_episode(seed,variant,method)
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if ROOT in a.output.resolve().parents:
        p.error('write new execution evidence outside the frozen submission folder')
    started=time.monotonic()
    tasks=[(s,v,m) for s in PLAN['seeds'] for v in PLAN['variants'] for m in PLAN['methods']]
    rows=[]
    with ProcessPoolExecutor(max_workers=2,mp_context=get_context('spawn')) as pool:
        pending={pool.submit(run,t):t for t in tasks}
        for future in as_completed(pending,timeout=300):
            row=future.result();rows.append(row)
            print(json.dumps({'completed':len(rows),'total':len(tasks),'method':row['method'],'variant':row['variant']}),flush=True)
    from blackbox.experiment import summarise
    from blackbox.provenance import execution_identity
    # Replayed controls must reproduce the old validation observations exactly.
    old=json.loads((RESEARCH/'results/validation.json').read_text())
    controls={(r['seed'],r['variant']):r for r in old['episodes'] if r['method']=='conservative'}
    compare=['action_sha256','assignments','mutual_second_meeting_intention','ask_cost',
             'first_introduction_wait_days','unserved_members','missing_feedback']
    for row in rows:
        if row['method']=='conservative':
            assert all(row[k]==controls[row['seed'],row['variant']][k] for k in compare)
    result={'schema_version':1,'plan':PLAN,'identity':execution_identity(),
            'complete':len(rows)==24,'all_valid':all(r['valid'] for r in rows),
            'control_replay_identical':True,'elapsed_seconds':time.monotonic()-started,
            'episodes':sorted(rows,key=lambda r:(r['seed'],r['variant'],r['method'])),
            'summaries':{m:summarise([r for r in rows if r['method']==m]) for m in PLAN['methods']}}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return 0 if result['complete'] and result['all_valid'] else 2


if __name__=='__main__':raise SystemExit(main())
