"""Reserve final seeds for one frozen plan; source/asset changes cannot recycle them."""
import json
from pathlib import Path
from .storage import WorkflowLock,atomic_json,digest
ROOT=Path(__file__).resolve().parents[1]
HISTORICAL=((3101,3110),(3201,3210))

def reserve(seeds,plan,root=None):
    root=Path(root or ROOT);folder=root/'artifacts';folder.mkdir(exist_ok=True)
    if any(lo<=s<=hi for s in seeds for lo,hi in HISTORICAL):raise ValueError('historical consumed final seeds cannot bind a new plan')
    key=digest(plan)
    with WorkflowLock(folder/'seed_registry.lock'):
        path=folder/'final_seed_registry.json'
        data=json.loads(path.read_text()) if path.exists() else {'schema_version':1,'reservations':{}}
        if data.get('schema_version')!=1:raise ValueError('seed registry schema')
        for seed in seeds:
            old=data['reservations'].get(str(seed))
            if old and old!=key:raise ValueError('final seed already reserved by another frozen source/asset plan: '+str(seed))
        for seed in seeds:data['reservations'][str(seed)]=key
        atomic_json(path,data)
    return key
