"""Calibration and paired seed-block uncertainty; no row-wise policy significance."""
import math,random,statistics
from fractions import Fraction

def quantile(values,q):
    if not values:return None
    xs=sorted(values);return xs[round((len(xs)-1)*q)]

def calibration(rows):
    if not rows:return {'n':0,'brier':None,'log_loss':None,'ece':None,'bins':[]}
    bins=[];ece=0
    for lo,hi in zip([0,.01,.02,.04,.08,.16,.32,.64],[.01,.02,.04,.08,.16,.32,.64,1.00001]):
        r=[x for x in rows if lo<=x['prediction']<hi]
        if not r:continue
        p=statistics.mean(x['prediction'] for x in r);y=statistics.mean(x['label'] for x in r)
        bins.append({'lo':lo,'hi':min(hi,1),'n':len(r),'predicted':p,'observed':y})
        ece+=len(r)/len(rows)*abs(p-y)
    return {'n':len(rows),'positives':sum(x['label'] for x in rows),
        'brier':statistics.mean((x['prediction']-x['label'])**2 for x in rows),
        'log_loss':-statistics.mean(x['label']*math.log(max(1e-12,x['prediction']))+(1-x['label'])*math.log(max(1e-12,1-x['prediction'])) for x in rows),
        'ece':ece,'bins':bins,
        'prediction_quantiles':{str(q):quantile([r['prediction'] for r in rows],q) for q in (0,.05,.5,.95,1)},
        'scope':'selected mature introductions only','ranking':ranking(rows)}

def paired_interval(rows,candidate,baseline='conservative',draws=2000):
    values={}
    for r in rows:
        if r['method'] in (candidate,baseline):values.setdefault((r['seed'],r['variant']),{})[r['method']]=r
    seeds=sorted({k[0] for k in values});families=sorted({k[1] for k in values})
    if not seeds or any(set(v)!={candidate,baseline} or not all(r['valid'] for r in v.values()) for v in values.values()) or len(values)!=len(seeds)*len(families):
        return {'status':'incomplete_or_invalid'}
    # Preserve exact zero at the promotion boundary. Family/seed averaging of
    # binary floats can otherwise turn a zero percentile into +2.8e-18.
    def exact_score(row):
        if 'mutual_second_meeting_intention' in row and 'arrived_members' in row:
            return Fraction(100*row['mutual_second_meeting_intention'],row['arrived_members'])
        return Fraction(str(row['msmi_per_100_arrived_members']))
    diffs={seed:statistics.mean(exact_score(values[(seed,v)][candidate])-
        exact_score(values[(seed,v)][baseline]) for v in families) for seed in seeds}
    rng=random.Random(17);boot=[statistics.mean(diffs[rng.choice(seeds)] for _ in seeds) for _ in range(draws)]
    return {'status':'descriptive_seed_block_bootstrap','seed_blocks':len(seeds),'delta':float(statistics.mean(diffs.values())),
        'ci95':[float(quantile(boot,.025)),float(quantile(boot,.975))],
        'warning':'Descriptive percentile bootstrap; sample count alone does not establish statistical power.'}


def ranking(rows):
    """Tie-aware AUROC/AP and fractional-tie top-decile lift on mature labels."""
    n=len(rows);positive=sum(r['label'] for r in rows);negative=n-positive
    if not n:return {'n':0,'auc':None,'average_precision':None,'top_decile_lift':None}
    groups={}
    for row in rows:
        p=row['prediction']
        if not math.isfinite(p) or not 0<=p<=1 or row['label'] not in (0,1):raise ValueError('invalid ranking observation')
        g=groups.setdefault(p,[0,0]);g[0]+=row['label'];g[1]+=1-row['label']
    below=0;wins=0.0
    for p,(pos,neg) in sorted(groups.items()):wins+=pos*(below+.5*neg);below+=neg
    seen=tp=0;ap=0.0;take=max(1,n/10);taken=top_positive=0.0
    for p,(pos,neg) in sorted(groups.items(),reverse=True):
        size=pos+neg;seen+=size;tp+=pos
        if positive:ap+=(pos/positive)*(tp/seen)
        fraction=min(1,max(0,take-taken)/size);top_positive+=fraction*pos;taken+=fraction*size
    return {'n':n,'auc':wins/(positive*negative) if positive and negative else None,
        'average_precision':ap if positive else None,'prevalence':positive/n,
        'top_decile_lift':(top_positive/taken)/(positive/n) if positive else None,
        'scope':'mature selected introductions; no population/counterfactual claim'}
