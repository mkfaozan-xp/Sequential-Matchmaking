"""Policy composition; experimental choices remain explicit and independently ablatable."""
import random
from .contracts import validate_request,validate_actions
from .clarification import pruned,input_order,sampled_asks
from .allocation import allocate,graph_edges
from .model import load_model

MODES={
 'conservative':('pruned','soft','greedy',0),
 'greedy':('input','soft','greedy',0),
 'no_asks':('none','soft','greedy',0),
 'random':('input','soft','random',0),
 'global':('pruned','soft','milp',0),
 'learned':('pruned','learned','greedy',0),
 'learned_global':('pruned','learned','milp',0),
 'value_greedy':('value','soft','greedy',0),
 'value_global':('value','soft','milp',0),
 'learned_value':('value','learned','greedy',0),
 'single_value':('single','learned','greedy',0),
 'learned_no_asks':('none','learned','greedy',0),
 'waiting':('pruned','learned','greedy',.02),
 'answer_stress':('stress','learned','greedy',0),
}

def decide(request,mode='conservative'):
    s=validate_request(request);ask,score,solver,wait=MODES[mode];diag={}
    from .registry import selected
    deployment,_=selected()
    prior=request.get('memory')
    prior=prior if isinstance(prior,dict) and prior.get('mode')==mode else {}
    previous_since=prior.get('available_since',{}) if mode=='waiting' else {}
    previous_since=previous_since if isinstance(previous_since,dict) else {}
    previous_since={i:day for i,day in previous_since.items() if type(day) is int and 0<=day<=s['day']}
    available_since={m['member_id']:previous_since.get(m['member_id'],s['day']) for m in s['members'] if m['available']}
    model=None
    if score=='learned':model=load_model()
    if request['phase']=='ask':
        if ask=='input':actions=input_order(s)
        elif ask=='none':actions=[]
        elif ask in ('value','single','stress'):
            actions,diag=sampled_asks(s,model,score,pair_seeds=ask!='single',refusal=.25 if ask=='stress' else 0)
        else:actions=pruned(s)
        key='asks'
    else:
        if solver=='random':
            edges=graph_edges(s,score,model);random.Random(17+s['day']).shuffle(edges);used=set();actions=[]
            for p,_ in edges:
                if not used.intersection(p):actions.append(list(p));used.update(p)
        else:actions,diag=allocate(s,score,model,solver,wait,available_since)
        key='pairs'
    validate_actions(s,request['phase'],actions)
    memory={'version':'blackbox-0.3.0','release_id':deployment['release_id'],'mode':mode,'model':model.version if model else 'observed-agreement',
            'last_day':s['day'],'diagnostics':diag}
    if mode=='waiting':memory['available_since']=available_since
    return {key:actions,'memory':memory}
