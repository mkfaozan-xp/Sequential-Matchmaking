"""Batch information acquisition. Sampled value is an approximation, never eligibility."""
import copy,itertools,json,random,time
from pathlib import Path
from .domain import HARD,eligibility
from .allocation import graph_edges,greedy
from .model import score_pair
from .features import response_history


def opportunities(state):
    members=[m for m in state['members'] if m['available']]
    missing={m['member_id'] for m in members if any(m['fields'][k] is None for k in HARD)}
    blocked={m['member_id'] for m in members if any(m['field_status'][k]=='declined' for k in HARD)}
    past={tuple(sorted((i['user_a'],i['user_b']))) for i in state['introductions']}
    out=[]
    for a,b in itertools.combinations(members,2):
        pair=tuple(sorted((a['member_id'],b['member_id'])))
        if pair in past or set(pair)&blocked:continue
        if eligibility(a,b)['status']=='needs_clarification':out.append((a,b,frozenset(set(pair)&missing)))
    return out


def pruned(state,opps=None):
    opps=opportunities(state) if opps is None else opps
    candidates={i for _,_,req in opps for i in req}
    return [{'member_id':m['member_id'],'field':'constraints'} for m in state['members']
        if m['member_id'] in candidates][:state['ask_budget_remaining']//3]


def input_order(state):
    return [{'member_id':m['member_id'],'field':'constraints'} for m in state['members']
        if m['available'] and any(m['fields'][k] is None for k in HARD)
        and not any(m['field_status'][k]=='declined' for k in HARD)][:state['ask_budget_remaining']//3]


def value(edges):
    weights={p:w for p,w in edges}
    return sum(weights[tuple(sorted(p))] for p in greedy(edges))


def hypothetical(state,selected,donors,sample,refusal):
    # Only selected missing fields are sampled. The match phase never sees these copies.
    out=copy.deepcopy(state)
    for member in out['members']:
        if member['member_id'] not in selected:continue
        rng=random.Random(f"17:{state['day']}:{sample}:{member['member_id']}")
        if rng.random()<refusal:continue
        donor=donors[rng.randrange(len(donors))];fields=copy.deepcopy(donor['fields'])
        fields['age_min']=max(18,min(65,member['age']+fields['age_min']-donor['age']))
        fields['age_max']=max(fields['age_min'],min(65,member['age']+fields['age_max']-donor['age']))
        fields['acceptable_zones']=[member['zone'] if z==donor['zone'] else z for z in fields['acceptable_zones']]
        for k in HARD:
            if member['fields'][k] is None and member['field_status'][k]!='declined':
                member['fields'][k]=fields[k];member['field_status'][k]='observed';member['field_observed_day'][k]=state['day']
    return out


def sampled_asks(state,model=None,score='soft',pair_seeds=True,refusal=0.0,seconds=2.5):
    deadline=time.monotonic()+seconds;opps=opportunities(state);fallback=pruned(state,opps)
    from .registry import load_artifact
    donors=load_artifact('answers.json')['donors']
    if not opps:return [],{'search':'pruned','fallback':False,'reason':'no_opportunities'}
    if not donors:return fallback,{'search':'pruned','fallback':True,'reason':'empty_answer_model'}
    cap=state['ask_budget_remaining']//3;history=response_history(state)
    current=graph_edges(state,score,model)
    optimistic=[(tuple(sorted((a['member_id'],b['member_id']))),score_pair(a,b,state,score,model,history),req) for a,b,req in opps]
    # Bound screening BEFORE evaluating graph values: never O(E^2) over every endpoint bundle.
    member_rank={}
    for _,w,req in optimistic:
        for i in req:member_rank[i]=member_rank.get(i,0)+max(0,w)/len(req)
    top_members=sorted(member_rank,key=lambda i:(-member_rank[i],i))[:12]
    bundles={frozenset([i]) for i in top_members}
    if pair_seeds:
        top_edges=sorted(optimistic,key=lambda e:(-e[1]/len(e[2]),e[0]))[:12]
        bundles|={req for _,_,req in top_edges}
    # Screen by optimistic unlock reward, accounting for shared endpoints.
    proxy_cache={}
    def proxy(selected):
        if selected not in proxy_cache:
            proxy_cache[selected]=value(current+[(p,w) for p,w,req in optimistic if req<=selected])
        return proxy_cache[selected]
    rank=sorted(bundles,key=lambda b:(-proxy(b)/len(b),tuple(sorted(b))))[:10]
    candidates={frozenset(),frozenset(a['member_id'] for a in fallback)}
    for seed in rank[:4]:
        selected=seed
        while len(selected)<cap and time.monotonic()<deadline:
            choices=[b-selected for b in rank if b-selected and len(selected|b)<=cap]
            if not choices:break
            addition=max(choices,key=lambda b:(proxy(selected|b)-proxy(selected))/len(b))
            selected=selected|addition
        if len(selected)<=cap:candidates.add(selected)
    batches=sorted(candidates,key=lambda b:(len(b),tuple(sorted(b))))[:6]
    base=value(current);best=frozenset();gain=0.0;solves=0
    for batch in batches:
        if not batch:continue
        estimates=[]
        for sample in range(4):
            if time.monotonic()>=deadline:return fallback,{'search':'pruned','fallback':True,'hypothetical_solves':solves,'reason':'search_deadline'}
            sampled=hypothetical(state,batch,donors,sample,refusal)
            estimates.append(value(graph_edges(sampled,score,model)));solves+=1
        delta=sum(estimates)/len(estimates)-base
        if delta>gain+1e-12:gain=delta;best=batch
    return [{'member_id':i,'field':'constraints'} for i in sorted(best)],{
        'search':'sampled_greedy_value','fallback':False,'hypothetical_solves':solves,'estimated_gain':gain,
        'answer_assumption':'empirical_disclosed_bundles_not_population_truth'}
