"""Observable-only receding-horizon approximation with one asking/matching value.

V(state, matching) = sum(pair official-success estimates)
                  + sum(member remaining-free-days * continuation rate).

Rates are optimistic current-opportunity reward rates, not a learned Bellman
value or an oracle forecast. All matching and information values use this same
definition. Hard feasibility always comes from real disclosed observations.
"""
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
from functools import lru_cache

from blackbox.contracts import validate_request, validate_actions
from blackbox.domain import HARD, eligibility
from blackbox.features import pair_features, response_history
from blackbox.ranking import project, rank_names
from blackbox.registry import load_artifact, selected

ROOT=Path(__file__).resolve().parent
EPS=1e-12


def sha(raw):return hashlib.sha256(raw).hexdigest()


@lru_cache(maxsize=2)
def _decode_model(raw):
    obj=json.loads(raw)
    if obj['feature_names']!=rank_names('reference'):raise ValueError('coordinated feature schema')
    for head in ('reward','hold'):
        h=obj[head]
        if len(h['weights'])!=32 or not all(math.isfinite(v) for v in [h['intercept'],*h['weights']]):
            raise ValueError('invalid coordinated model')
    if not 0<obj['timeliness_factor']<=1:raise ValueError('invalid timeliness factor')
    return obj


def load_model():
    release=json.loads((ROOT/'release.json').read_text())
    raw=(ROOT/'model.json').read_bytes()
    if sha(raw)!=release['model_sha256']:raise ValueError('coordinated model identity')
    for name,h in release['runtime_source'].items():
        if sha((ROOT/name).read_bytes())!=h:raise ValueError('coordinated runtime source changed')
    return _decode_model(raw)


def estimates(a,b,state,model,history,constant=False):
    if constant:return model['official_prevalence'],model['hold']['constant_days']
    x=project(pair_features(a,b,state,history),'reference')
    h=model['reward'];z=h['intercept']+sum(w*v for w,v in zip(h['weights'],x))
    probability=model['timeliness_factor']/(1+math.exp(-max(-40,min(40,z))))
    h=model['hold'];hold=40*(h['intercept']+sum(w*v for w,v in zip(h['weights'],x)))
    return probability,max(8,min(40,hold))


def matching(weights,passes=2):
    """Deterministic legal incumbent plus bounded improving two-edge exchanges."""
    edges=sorted(((tuple(sorted(p)),w) for p,w in weights if w>EPS),key=lambda e:(-e[1],e[0]))
    lookup=dict(edges);mate={};adjacency={}
    for (a,b),w in edges:
        adjacency.setdefault(a,[]).append((b,w));adjacency.setdefault(b,[]).append((a,w))
    for (a,b),_ in edges:
        if a not in mate and b not in mate:mate[a]=b;mate[b]=a
    for _ in range(passes):
        changed=False
        for (a,b),weight in edges:
            if mate.get(a)==b:continue
            removed={tuple(sorted((i,mate[i]))) for i in (a,b) if i in mate}
            old=sum(lookup[p] for p in removed)
            leftovers=sorted({i for pair in removed for i in pair}-{a,b})
            reconnect=tuple(leftovers) if len(leftovers)==2 else None
            extra=lookup.get(reconnect,0) if reconnect else 0
            if len(leftovers)==1:
                x=leftovers[0]
                options=[(y,w) for y,w in adjacency[x] if y not in mate and y not in (a,b)]
                if options:
                    y,extra=min(options,key=lambda t:(-t[1],t[0]));reconnect=tuple(sorted((x,y)))
            if weight+extra<=old+EPS:continue
            for x,y in removed:mate.pop(x,None);mate.pop(y,None)
            mate[a]=b;mate[b]=a
            if extra>EPS:
                x,y=reconnect;mate[x]=y;mate[y]=x
            changed=True
        if not changed:break
    pairs=sorted((a,b) for a,b in mate.items() if a<b)
    return [list(p) for p in pairs],sum(lookup[p] for p in pairs)


def objective(edges,day,myopic=False):
    """Same units and continuation definition for actual and sampled graphs."""
    horizon=60-day;rates={}
    if not myopic:
        for (a,b),reward,hold in edges:
            rate=reward/(2*hold+1)
            rates[a]=max(rates.get(a,0),rate);rates[b]=max(rates.get(b,0),rate)
    weighted=[(pair,reward-min(horizon,hold)*sum(rates.get(i,0) for i in pair))
              for pair,reward,hold in edges]
    pairs,gain=matching(weighted)
    continuation=horizon*sum(rates.values())
    return pairs,continuation+gain,{'immediate_estimated_reward':sum(r for p,r,d in edges if list(p) in pairs),
                                  'continuation_value':continuation,'matching_increment':gain,
                                  'feasible_edges':len(edges),'deferred_nonpositive_edges':sum(w<=EPS for _,w in weighted)}


def potential(state,model,constant=False):
    members=sorted((m for m in state['members'] if m['available']),key=lambda m:m['member_id'])
    history=response_history(state)
    past={tuple(sorted((i['user_a'],i['user_b']))) for i in state['introductions']}
    edges=[]
    for a,b in itertools.combinations(members,2):
        pair=(a['member_id'],b['member_id'])
        if pair in past:continue
        status=eligibility(a,b)['status']
        if status=='infeasible':continue
        req=frozenset(m['member_id'] for m in (a,b) if any(m['fields'][k] is None for k in HARD))
        if any(any(m['field_status'][k]=='declined' for k in HARD) for m in (a,b) if m['member_id'] in req):continue
        reward,hold=estimates(a,b,state,model,history,constant)
        edges.append((pair,reward,hold,req))
    return edges


def response_probability(state):
    logs=[a for a in state['ask_log'] if a['field']=='constraints' and a['observed_day']<=state['day']]
    completed=sum(all(a['statuses'][k]=='observed' for k in HARD) for a in logs)
    return (completed+1)/(len(logs)+2)


def draws(state,edges,donors):
    """Joint empirical hard-answer scenarios; never passed into real match actions."""
    from blackbox.clarification import hypothetical
    askable=frozenset(i for _,_,_,req in edges for i in req)
    q=response_probability(state);out=[]
    for sample in range(3):
        scenario=hypothetical(state,askable,donors,sample,1-q)
        members={m['member_id']:m for m in scenario['members']}
        out.append([edge for edge in edges if eligibility(*(members[i] for i in edge[0]))['status']=='feasible'])
    return out,q


def ask(state,edges,myopic=False):
    cap=state['ask_budget_remaining']//3
    current=[e[:3] for e in edges if not e[3]]
    base=objective(current,state['day'],myopic)[1]
    if not cap:return [],{'objective_before':base,'planned_question_cost':0,'sampled_graph_solves':0}
    bundles={e[3] for e in edges if e[3] and len(e[3])<=cap}
    if not bundles:return [],{'objective_before':base,'planned_question_cost':0,'sampled_graph_solves':0}
    donors=load_artifact('answers.json')['donors']
    if not donors:return [],{'objective_before':base,'reason':'no_empirical_answer_support','planned_question_cost':0,'sampled_graph_solves':0}
    scenarios,q=draws(state,edges,donors)
    # Candidate generation is a bounded optimistic screen, not a second reward.
    optimistic={b:0 for b in bundles}
    for pair,reward,hold,req in edges:
        if req in optimistic:optimistic[req]+=reward
    bundles=sorted(bundles,key=lambda b:(-optimistic[b]/len(b),tuple(sorted(b))))[:12]
    cache={frozenset():base};solves=0
    def expected(batch):
        nonlocal solves
        if batch not in cache:
            cache[batch]=sum(objective([e[:3] for e in scenario if e[3]<=batch],state['day'],myopic)[1]
                             for scenario in scenarios)/len(scenarios)
            solves+=len(scenarios)
        return cache[batch]
    chosen=frozenset();value=base
    while len(chosen)<cap:
        choices={chosen|b for b in bundles if b-chosen and len(chosen|b)<=cap}
        if not choices:break
        best=min(choices,key=lambda b:(-(expected(b)-value)/(len(b)-len(chosen)),len(b),tuple(sorted(b))))
        if expected(best)<=value+EPS:break
        chosen=best;value=expected(best)
    return [{'member_id':i,'field':'constraints'} for i in sorted(chosen)],{
        'objective_before':base,'expected_objective_after':value,'estimated_information_gain':value-base,
        'planned_question_cost':3*len(chosen),'sampled_graph_solves':solves,'answer_draws':3,
        'empirical_complete_answer_probability':q,'answer_model_scope':'disclosed donor bundles, Beta(1,1) response smoothing; not population truth'}


def decide(request,ablation=None):
    if ablation not in (None,'myopic','constant'):raise ValueError('unknown coordinated ablation')
    state=validate_request(request);model=load_model()
    edges=potential(state,model,constant=ablation=='constant')
    if request['phase']=='ask':
        actions,diag=ask(state,edges,myopic=ablation=='myopic');key='asks'
    else:
        # Real refreshed disclosures only. Sampled profiles never enter this path.
        actions,value,diag=objective([e[:3] for e in edges if not e[3]],state['day'],myopic=ablation=='myopic')
        diag['selected_objective_value']=value;key='pairs'
    validate_actions(state,request['phase'],actions)
    release=selected()[0]['release_id']
    diag.update(objective='official_success_plus_remaining_availability',approximate=True,
                engine='coordinated-v1',ablation=ablation,model_id=model['model_id'])
    return {key:actions,'memory':{'version':'coordinated-v1','mode':'coordinated','model':model['model_id'],
                                 'release_id':release,'last_day':state['day'],'diagnostics':diag}}
