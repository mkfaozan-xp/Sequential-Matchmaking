"""Calibration and paired seed-block uncertainty; no row-wise policy significance."""
import math,random,statistics

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
        'scope':'selected mature introductions only'}

def paired_interval(rows,candidate,baseline='conservative',draws=2000):
    values={}
    for r in rows:
        if r['method'] in (candidate,baseline):values.setdefault((r['seed'],r['variant']),{})[r['method']]=r
    seeds=sorted({k[0] for k in values});families=sorted({k[1] for k in values})
    if not seeds or any(set(v)!={candidate,baseline} or not all(r['valid'] for r in v.values()) for v in values.values()) or len(values)!=len(seeds)*len(families):
        return {'status':'incomplete_or_invalid'}
    diffs={seed:statistics.mean(values[(seed,v)][candidate]['msmi_per_100_arrived_members']-values[(seed,v)][baseline]['msmi_per_100_arrived_members'] for v in families) for seed in seeds}
    rng=random.Random(17);boot=[statistics.mean(diffs[rng.choice(seeds)] for _ in seeds) for _ in range(draws)]
    return {'status':'descriptive_seed_block_bootstrap','seed_blocks':len(seeds),'delta':statistics.mean(diffs.values()),
        'ci95':[quantile(boot,.025),quantile(boot,.975)],
        'warning':'Descriptive percentile bootstrap; sample count alone does not establish statistical power.'}
