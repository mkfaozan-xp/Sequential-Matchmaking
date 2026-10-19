"""Trusted offline control plane. Only observe() records enter the policy or model."""
import copy,hashlib,json,statistics,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'starter'))
from kit import Simulator,generate,VERSION,HARD
from evaluate import invoke,summarise
from blackbox.policy import decide
from blackbox.features import pair_features,direction_features,response_history,NAMES
from blackbox.labels import msmi_label,response_label
from blackbox.model import load_model
from blackbox.metrics import calibration,quantile

VARIANTS=('development','sparse','cold_start','delayed','shift','drift')

def reference_decide(request,mode):
    # Load official module under a unique name: avoid root policy.py name collision.
    import importlib.util
    spec=importlib.util.spec_from_file_location('supplied_policy',ROOT/'starter/policy.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.decide(request,mode)

def run_episode(seed,variant,method='conservative',transport='inprocess',collect=False,n=200,heartbeat=None):
    started=time.perf_counter();sim=Simulator(generate(seed,n,'evaluation',variant))
    memory=None;times=[];snapshots={};donors={};trace=[];diag_counts={};reason_counts={};max_bytes=0
    initial_info={};max_request=0
    model=None if collect else load_model()
    official=method.startswith('baseline_')
    for _ in range(60):
        for phase in ('ask','match'):
            if heartbeat:heartbeat()
            state=sim.observe()
            for m in state['members']:
                if m['member_id'] not in initial_info:
                    known=sum(m['fields'][k] is not None for k in HARD)
                    initial_info[m['member_id']]='complete' if known==len(HARD) else ('low' if known<=2 else 'partial')
                if collect and all(m['fields'][k] is not None for k in HARD):
                    donors[m['member_id']]={'age':m['age'],'zone':m['zone'],'fields':{k:copy.deepcopy(m['fields'][k]) for k in HARD}}
            request={'schema_version':VERSION,'phase':phase,'state':state,'memory':memory}
            max_request=max(max_request,len(json.dumps(request).encode()))
            t=time.perf_counter()
            if transport=='subprocess':
                command=[sys.executable,str(ROOT/'starter/policy.py'),'--baseline',method.removeprefix('baseline_')] if official else [sys.executable,str(ROOT/'policy.py'),'--mode',method]
                response,elapsed=invoke(command,request)
            else:
                response=reference_decide(request,method.removeprefix('baseline_')) if official else decide(request,method)
                elapsed=time.perf_counter()-t
            times.append(elapsed);memory=response['memory'];actions=response['asks' if phase=='ask' else 'pairs']
            reason=(memory or {}).get('diagnostics',{}).get('reason')
            if reason:reason_counts[reason]=reason_counts.get(reason,0)+1
            for k,v in (memory or {}).get('diagnostics',{}).items():
                if isinstance(v,(bool,int,float)):diag_counts[k]=diag_counts.get(k,0)+v
            max_bytes=max(max_bytes,len(json.dumps(response).encode()))
            trace.append([sim.day,phase,actions])
            if phase=='ask':sim.resolve_asks(actions)
            else:
                ids={m['member_id']:m for m in state['members']};history=response_history(state)
                for pair in actions:
                    a,b=(ids[i] for i in pair);key=(tuple(sorted(pair)),state['day'])
                    # Capture BEFORE assignment, never join a day-30 profile backwards.
                    snapshots[key]={'x':pair_features(a,b,state,history),
                        'directions':{m['member_id']:direction_features(m,o,state,history) for m,o in ((a,b),(b,a))},
                        'assigned_day':state['day']}
                sim.advance(actions)
    arrived={m['member_id']:m['arrived_day'] for m in sim.observe()['members'] if m['arrived_day']<=59}
    for _ in range(40):sim.advance([])
    feedback=sim.receive_feedback();joint=[];direction=[];predictions=[];direction_predictions=[];first={}
    for intro in sim.introductions:
        snap=snapshots[(tuple(sorted((intro['user_a'],intro['user_b']))),intro['assigned_day'])]
        label=msmi_label(intro,feedback,sim.day)
        key=f"{seed}:{variant}:{intro['introduction_id']}"
        if label is not None:
            row={'row_id':key,'seed':seed,'variant':variant,'x':snap['x'],'label':label,'assigned_day':intro['assigned_day']}
            joint.append(row)
            if model:predictions.append({'prediction':model.predict(snap['x']),'label':label})
        for actor in (intro['user_a'],intro['user_b']):
            first.setdefault(actor,intro['assigned_day'])
            y=response_label(intro,actor,feedback,sim.day)
            if y is not None:
                direction.append({'row_id':key+':'+actor,'seed':seed,'variant':variant,'x':snap['directions'][actor],'label':y})
                if model:direction_predictions.append({'prediction':model.predict(snap['directions'][actor],'direction'),'label':y})
    metrics=sim.metrics();waits=[first[i]-arrived[i] for i in first]
    slices={}
    for group in ('low','partial','complete'):
        ids={i for i in arrived if initial_info[i]==group};served=ids&set(first)
        # Unserved exposure is reported separately from served-only waiting.
        slices[group]={'members':len(ids),'served':len(served),'unserved':len(ids-served),
            'coverage':len(served)/len(ids) if ids else None,
            'unserved_exposure_days':sum(60-arrived[i] for i in ids-served),
            'served_wait_p95':quantile([first[i]-arrived[i] for i in served],.95)}
    metrics.update(seed=seed,variant=variant,method=method,transport=transport,valid=True,
        arrived_members=len(arrived),msmi_per_100_arrived_members=100*metrics['mutual_second_meeting_intention']/max(1,len(arrived)),
        mutual_acceptances_per_100=100*metrics['mutual_acceptances']/max(1,len(arrived)),
        served_members=len(first),unserved_members=len(arrived)-len(first),coverage=len(first)/max(1,len(arrived)),
        first_introduction_wait_days=sorted(waits),served_wait_p95=quantile(waits,.95),
        unserved_exposure_days=sum(60-arrived[i] for i in set(arrived)-set(first)),service_slices=slices,
        inference_seconds=sum(times),max_call_seconds=max(times),p95_call_seconds=quantile(times,.95),
        wall_seconds=time.perf_counter()-started,max_response_bytes=max_bytes,max_request_bytes=max_request,
        diagnostics=diag_counts,reason_counts=reason_counts,action_sha256=hashlib.sha256(json.dumps(trace,sort_keys=True).encode()).hexdigest(),
        calibration=calibration(predictions),directional_response_calibration=calibration(direction_predictions))
    metrics['mature_feature_missingness']={name:sum(r['x'][i] for r in joint)/len(joint) if joint else None
        for i,name in enumerate(NAMES) if name.endswith(':missing')}
    return metrics,joint,direction,list(donors.values())
