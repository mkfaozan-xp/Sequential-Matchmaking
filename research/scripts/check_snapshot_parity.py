"""Complete cold/cached action parity on declared preparation worlds."""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blackbox.experiment import run_episode
from blackbox.registry import verified_episode_snapshot
from blackbox.provenance import execution_identity
from blackbox.storage import atomic_json

def main():
 before=execution_identity();records=[]
 fields=('action_sha256','assignments','mutual_acceptances','dates','mutual_second_meeting_intention','ask_cost','served_members')
 for mode in ('conservative','rank_ref'):
  cold,*_=run_episode(1999,'development',mode)
  with verified_episode_snapshot(before['inference_release']):warm,*_=run_episode(1999,'development',mode)
  if execution_identity()!=before:raise ValueError('parity subject changed')
  if any(cold[k]!=warm[k] for k in fields):raise ValueError('snapshot/cache changed complete episode actions/outcomes')
  records.append({'mode':mode,'cold_wall_seconds':cold['wall_seconds'],'snapshot_wall_seconds':warm['wall_seconds'],'action_sha256':cold['action_sha256']})
 record={'identity':before,'seed':1999,'variant':'development','members':200,'preparation_episodes':4,
  'compared_fields':list(fields),'rows':records,'passed':True,'scope':'Implementation parity, not independent efficacy evidence. Cold CLI/container verification remains separate.'}
 atomic_json(ROOT/'results/snapshot_parity.json',record);print(json.dumps(record))
if __name__=='__main__':raise SystemExit(main())
