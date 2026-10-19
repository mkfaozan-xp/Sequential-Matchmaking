"""General-graph allocation with a hard child-process budget and legal fallback."""
import itertools,json,subprocess,sys
from pathlib import Path
from .domain import eligibility
from .compatibility import prepared
from .features import response_history
from .model import score_pair


def graph_edges(state,score='soft',model=None):
    members=[m for m in state['members'] if m['available']]
    past={tuple(sorted((i['user_a'],i['user_b']))) for i in state['introductions']}
    history=response_history(state);edges=[];check=prepared(members)
    for a,b in itertools.combinations(members,2):
        pair=tuple(sorted((a['member_id'],b['member_id'])))
        if pair in past or check(a,b)['status']!='feasible':continue
        edges.append((pair,score_pair(a,b,state,score,model,history)))
    return sorted(edges)


def greedy(edges):
    used=set();pairs=[]
    for pair,w in sorted(edges,key=lambda e:(-e[1],e[0])):
        if w<0 or used.intersection(pair):continue
        used.update(pair);pairs.append(list(pair))
    return pairs


def allocate(state,score='soft',model=None,solver='greedy',wait_threshold=0,available_since=None):
    edges=graph_edges(state,score,model)
    if wait_threshold and state['day']<57:
        by_id={m['member_id']:m for m in state['members']}
        available_since=available_since or {m['member_id']:state['day'] for m in state['members'] if m['available']}
        edges=[(p,w) for p,w in edges if w>=wait_threshold or any(
            state['day']-available_since.get(i,state['day'])>=3 for i in p)]
    fallback=greedy(edges)
    if solver=='greedy' or not edges:return fallback,{'solver':'greedy','fallback':False}
    # Threads and solver runtime bounded in a killable child, including native startup.
    try:
        import os
        env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
        p=subprocess.run([sys.executable,str(Path(__file__).with_name('solve.py'))],
            input=json.dumps(edges),text=True,capture_output=True,timeout=1.8,env=env)
        if p.returncode:
            return fallback,{'solver':'greedy','fallback':True,'reason':'solver_process_failed'}
        result=json.loads(p.stdout)
        pairs=result['pairs'];weights={tuple(pair):w for pair,w in edges}
        if sum(weights[tuple(sorted(pair))] for pair in pairs)+1e-9<sum(weights[tuple(sorted(pair))] for pair in fallback):
            return fallback,{'solver':'greedy','fallback':True,'reason':'worse_solver_incumbent'}
        return pairs,{'solver':'milp','fallback':False,'optimal':result['optimal']}
    except subprocess.TimeoutExpired:
        return fallback,{'solver':'greedy','fallback':True,'reason':'solver_deadline'}
    except OSError:
        return fallback,{'solver':'greedy','fallback':True,'reason':'solver_unavailable'}
    except (ValueError,KeyError,TypeError):
        return fallback,{'solver':'greedy','fallback':True,'reason':'invalid_solver_output'}


def uniform_matching(edges,seed):
    """Uniform sequential legal-edge draws. Pair marginal propensities stay unknown."""
    import random,math
    rng=random.Random(seed);remaining=list(edges);pairs=[];steps=[];logp=0.0
    while remaining:
        count=len(remaining);pair,_=remaining[rng.randrange(count)]
        pairs.append(list(pair));steps.append({'pair':list(pair),'eligible_edges':count,'conditional_probability':1/count})
        logp-=math.log(count);used=set(pair)
        remaining=[e for e in remaining if not used.intersection(e[0])]
    return pairs,{'solver':'uniform','fallback':False,'selection_steps':steps,'joint_log_probability':logp,
        'propensity_scope':'conditional ordered action draws; pair inclusion probabilities unknown; no IPS claim'}
