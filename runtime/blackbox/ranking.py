"""Observed-cohort ranking inputs. Scores are utilities, never MSMI probabilities."""
import hashlib,math
from .features import NAMES
from .domain import SOFT
SIGNALS=('relationship_goal','relationship_pace','lifestyle','conversations')
RANK_NAMES=[n for n in NAMES if (n.startswith(tuple(k+':' for k in SIGNALS)) and ':count:' not in n)
            or n.startswith('outcome:') or n in ('age_gap','wait_min','wait_max','day','history_yes_min','history_yes_max','history_count_min','history_count_max')]
POSITIONS=tuple(NAMES.index(n) for n in RANK_NAMES)
AGREE_POSITIONS=tuple(NAMES.index(k+':agree') for k in SOFT)
PROJECTIONS=('full','reference','reference_nohistory')

def rank_names(projection='full'):
    if projection not in PROJECTIONS:raise ValueError('unknown ranking projection')
    return [n for n in RANK_NAMES if (projection=='full' or not n.endswith(':missing'))
            and (projection!='reference_nohistory' or not n.startswith('outcome:'))]

PROJECTION_POSITIONS={p:tuple(NAMES.index(n) for n in rank_names(p)) for p in PROJECTIONS}

def project(x,projection='full'):
    if len(x)!=len(NAMES) or not all(math.isfinite(v) for v in x):raise ValueError('ranking input schema/finite values')
    if projection not in PROJECTION_POSITIONS:raise ValueError('unknown ranking projection')
    return [x[i] for i in PROJECTION_POSITIONS[projection]]

def heuristic_score(x):
    """The deployed heuristic counts agreement on ALL seven soft fields."""
    return sum(x[i] for i in AGREE_POSITIONS)

def contrasts(rows,target='label',limit=5,window=7,projection='full',same_score=True):
    """Compare recorded positive/negative assignments in the same world near in time.

    Match the actual deployed heuristic score, not just the four projected fields.
    Both members of a contrast are observed introduced pairs, not counterfactual
    labels. They need not compete for an endpoint. Support/selection bias remains.
    Mirrored contrasts enforce a symmetric, balanced ranking target.
    """
    groups={}
    for row in rows:
        if row.get(target) not in (0,1):raise ValueError('mature compatible rows required')
        project(row['x'],projection)
        groups.setdefault((row['seed'],row['variant']),[]).append(row)
    out=[]
    for (seed,variant),world in sorted(groups.items()):
        negatives=[r for r in world if r[target]==0]
        for a in sorted((r for r in world if r[target]==1),key=lambda r:r['row_id']):
            eligible=[b for b in negatives if abs(a['assigned_day']-b['assigned_day'])<=window
                      and (not same_score or heuristic_score(a['x'])==heuristic_score(b['x']))]
            eligible.sort(key=lambda b:(abs(a['assigned_day']-b['assigned_day']),hashlib.sha256((a['row_id']+'|'+b['row_id']).encode()).hexdigest()))
            for b in eligible[:limit]:
                diff=[x-y for x,y in zip(project(a['x'],projection),project(b['x'],projection))]
                key=a['row_id']+'>'+b['row_id']
                for sign in (1,-1):
                    out.append({'seed':seed,'variant':variant,'x':[sign*v for v in diff],'label':int(sign==1),
                        'row_id':key+':'+str(sign),'positive_row_id':a['row_id'],'negative_row_id':b['row_id'],
                        'positive_day':a['assigned_day'],'negative_day':b['assigned_day'],
                        'positive_heuristic_score':heuristic_score(a['x']),
                        'negative_heuristic_score':heuristic_score(b['x'])})
    return out
