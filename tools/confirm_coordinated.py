"""Independent registered confirmation; fixed sample size, unchanged candidate."""
import argparse
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
from datetime import datetime
import hashlib
import json
from multiprocessing import get_context
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'research'))
from coordinated.evaluate import job,subject
from blackbox.metrics import paired_interval
from blackbox.experiment import summarise
from blackbox.storage import atomic_json


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--budget-origin',type=Path,required=True)
    a=p.parse_args();plan_path=ROOT/'coordinated/CONFIRMATION_PLAN.json'
    plan=json.loads(plan_path.read_text());identity=subject()
    if identity!=plan['source_and_assets_sha256']:raise ValueError('registered candidate changed')
    path=ROOT/'results/coordinated/confirmation.json'
    if path.exists():raise ValueError('confirmation is already recorded; do not overwrite')
    origin=json.loads(a.budget_origin.read_text());deadline=datetime.fromisoformat(origin['started_utc']).timestamp()+origin['budget_seconds']
    tasks=[(s,v,m) for s in plan['seeds'] for v in plan['variants'] for m in plan['methods']]
    rows=[];pending={};cursor=0;started=time.monotonic();error=None
    def save():
        complete=len(rows)==len(tasks)
        result={'schema_version':1,'scope':'Independent fixed-size confirmation declared after original final; no pooled significance or policy refit.',
          'source_and_assets_sha256':identity,'confirmation_plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),
          'expected_episodes':len(tasks),'complete':complete,'all_valid':complete and all(r['valid'] for r in rows),
          'config':plan,'episodes':sorted(rows,key=lambda r:(r['seed'],r['variant'],r['method'])),
          'paired_vs_conservative':paired_interval(rows,'coordinated'),
          'summaries':{m:summarise([r for r in rows if r['method']==m]) for m in plan['methods']},
          'elapsed_seconds':time.monotonic()-started,'budget_origin':origin,'error':error,'actual_docker':False}
        atomic_json(path,result);return result
    with ProcessPoolExecutor(max_workers=2,mp_context=get_context('spawn')) as pool:
        while cursor<len(tasks) or pending:
            if time.time()>=deadline:error='Original retained build budget exhausted';save();return 2
            while cursor<len(tasks) and len(pending)<2:
                task=tasks[cursor];cursor+=1;pending[pool.submit(job,task,identity)]=task
            done,_=wait(pending,timeout=1,return_when=FIRST_COMPLETED)
            for future in done:
                task=pending.pop(future)
                try:row=future.result()
                except Exception as failure:
                    row={'seed':task[0],'variant':task[1],'method':task[2],'valid':False,'error':type(failure).__name__+': '+str(failure)}
                rows.append(row);save()
                print(json.dumps({'completed':len(rows),'expected':len(tasks),'seed':task[0],'variant':task[1],
                                  'mode':task[2],'valid':row['valid'],'msmi':row.get('mutual_second_meeting_intention')}),flush=True)
    result=save();return 0 if result['all_valid'] else 2


if __name__=='__main__':raise SystemExit(main())
