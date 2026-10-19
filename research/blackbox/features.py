"""One point-in-time transform shared by fitting and inference. IDs are join keys only."""
from .domain import SOFT, OPTIONS

FEATURE_VERSION = 'observed-symmetric-v2'
NAMES = [f'{k}:{s}' for k in SOFT for s in ('agree','disagree','missing')]
NAMES += [f'{k}:count:{v}' for k in SOFT for v in OPTIONS[k]]
NAMES += ['age_gap','wait_min','wait_max','day','history_yes_min','history_yes_max',
          'history_count_min','history_count_max']
from .outcome_history import summarize,vector,NAMES as OUTCOME_NAMES
NAMES += [f'outcome:{name}:{side}' for name in OUTCOME_NAMES for side in ('min','max')]

class History(dict):
    pass

def response_history(state):
    out=History();out.outcomes=summarize(state)
    for event in state['feedback']:
        if event['event']!='introduction_response' or event['observed_day']>state['day']:continue
        ident=event['member_id'];yes,n=out.get(ident,(0,0))
        out[ident]=(yes+(event['value']=='yes'),n+1)
    return out

def pair_features(a,b,state,history=None):
    history = response_history(state) if history is None else history
    fa,fb=a['fields'],b['fields']; x=[]
    for k in SOFT:
        known=fa[k] is not None and fb[k] is not None
        x += [float(known and fa[k]==fb[k]),float(known and fa[k]!=fb[k]),float(not known)]
    for k in SOFT:
        x += [float((fa[k]==v)+(fb[k]==v))/2 for v in OPTIONS[k]]
    waits=sorted([max(0,state['day']-m['arrived_day'])/60 for m in (a,b)])
    hist=[history.get(m['member_id'],(0,0)) for m in (a,b)]
    rates=sorted([(yes+1)/(n+2) for yes,n in hist]);counts=sorted([min(n,10)/10 for _,n in hist])
    outcomes=getattr(history,'outcomes',None)
    if outcomes is None:outcomes=summarize(state)
    av=vector(a['member_id'],outcomes);bv=vector(b['member_id'],outcomes)
    return x+[abs(a['age']-b['age'])/50,*waits,state['day']/60,*rates,*counts]+[v for va,vb in zip(av,bv) for v in sorted((va,vb))]

DIRECTION_NAMES=NAMES+['actor_yes_rate','actor_history_count','actor_wait']+[f'actor:{n}' for n in OUTCOME_NAMES]
def direction_features(actor,other,state,history=None):
    history=response_history(state) if history is None else history
    yes,n=history.get(actor['member_id'],(0,0))
    outcomes=getattr(history,'outcomes',None)
    if outcomes is None:outcomes=summarize(state)
    return pair_features(actor,other,state,history)+[(yes+1)/(n+2),min(n,10)/10,max(0,state['day']-actor['arrived_day'])/60]+vector(actor['member_id'],outcomes)
