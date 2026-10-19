"""Policy composition; experimental choices remain explicit and independently ablatable."""
import random
from .contracts import validate_request,validate_actions
from .clarification import pruned,input_order,sampled_asks,soft_fill
from .allocation import allocate,graph_edges,uniform_matching
from .model import load_model

MODES={
 'rank_ref':('pruned','rank_ref','greedy',0),
 'rank_nohistory':('pruned','rank_nohistory','greedy',0),
 'rank_legacy':('pruned','rank_legacy','greedy',0),
 'rank_tie':('pruned','rank_tie','greedy',0),
 'rank_aux':('pruned','rank_aux','greedy',0),
 'outcome':('pruned','learned','greedy',0),
 'aux_hybrid':('pruned','aux_hybrid','greedy',0),
 'rate':('pruned','rate','greedy',0),
 'ridge_tie':('pruned','ridge_tie','greedy',0),
 'nohistory_tie':('pruned','nohistory_tie','greedy',0),
 'goal_tie':('pruned','goal_tie','greedy',0),
 'conservative':('pruned','soft','greedy',0),
 'greedy':('input','soft','greedy',0),
 'no_asks':('none','soft','greedy',0),
 'random':('input','soft','random',0),
 'global':('pruned','soft','milp',0),
 'learned':('pruned','learned','greedy',0),
 'hybrid':('pruned','hybrid','greedy',0),
 'hybrid_soft':('soft','hybrid','greedy',0),
 'hybrid_global':('pruned','hybrid','milp',0),
 'hybrid_pair':('study_pair','hybrid','greedy',0),
 'hybrid_pair_global':('study_pair','hybrid','milp',0),
 'hybrid_single':('study_single','hybrid','greedy',0),
 'hybrid_stress':('study_stress','hybrid','greedy',0),
 'explore_collect':('soft','constant','uniform',0),
 'learned_soft':('soft','learned','greedy',0),
 'soft_collect':('soft','soft','greedy',0),
 'study_pair_greedy':('study_pair','learned','greedy',0),
 'study_pair_global':('study_pair','learned','milp',0),
 'study_single_greedy':('study_single','learned','greedy',0),
 'study_answer_stress':('study_stress','learned','greedy',0),
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
    if score in ('learned','hybrid','aux_hybrid','rate','ridge_tie','nohistory_tie','rank_tie','rank_aux','rank_ref','rank_nohistory','rank_legacy'):model=load_model()
    if request['phase']=='ask':
        if ask=='input':actions=input_order(s)
        elif ask=='none':actions=[]
        elif ask=='soft':actions,diag=soft_fill(s)
        elif ask.startswith('study_'):
            actions,diag=sampled_asks(s,model,score,pair_seeds=ask!='study_single',
                refusal=.25 if ask=='study_stress' else 0,seconds=1.0,max_batches=2,samples=2,pad_batches=True)
        elif ask in ('value','single','stress'):
            actions,diag=sampled_asks(s,model,score,pair_seeds=ask!='single',refusal=.25 if ask=='stress' else 0)
        else:actions=pruned(s)
        key='asks'
    else:
        if solver=='uniform':
            actions,diag=uniform_matching(graph_edges(s,score,model),'exploration-v1:'+str(s['day']))
        elif solver=='random':
            edges=graph_edges(s,score,model);random.Random(17+s['day']).shuffle(edges);used=set();actions=[]
            for p,_ in edges:
                if not used.intersection(p):actions.append(list(p));used.update(p)
        else:actions,diag=allocate(s,score,model,solver,wait,available_since)
        key='pairs'
    validate_actions(s,request['phase'],actions)
    memory={'version':'blackbox-0.8.0','release_id':deployment['release_id'],'mode':mode,'model':model.version if model else 'observed-agreement',
            'last_day':s['day'],'diagnostics':diag}
    if mode=='waiting':memory['available_since']=available_since
    return {key:actions,'memory':memory}
