"""Train-only grouped selection, convex sparse logits and bounded duration ridge."""
import math
import numpy as np
from scipy.optimize import minimize
from .basis import lift,lifted_names
from .metrics import calibration
from .model import sigmoid

GRID=[('identity',0,10),('identity',0,100),('identity',2,10),
      ('identity',10,100),('compact',2,10),('signal_projection',2,10),('interactions_v1',2,10)]

def fit_constant(rows,names):
    p=sum(r['label'] for r in rows)/len(rows);safe=max(1e-12,min(1-1e-12,p))
    return {'feature_names':list(names),'basis':'identity','intercept':math.log(safe/(1-safe)),
        'weights':[0.0]*len(names),'n':len(rows),'positives':sum(r['label'] for r in rows),
        'training_prevalence':p,'l1':0,'l2':None,'estimator':'constant_prevalence','optimizer_converged':True}

def fit(rows,names,l2=10,basis='identity',l1=0):
    if not rows:raise ValueError('empty fitting data')
    if len({r['label'] for r in rows})<2:return fit_constant(rows,names)
    x=np.asarray([lift(r['x'],names,basis) for r in rows]);y=np.asarray([r['label'] for r in rows],dtype=float)
    if not np.isfinite(x).all() or not set(y)<={0,1}:raise ValueError('invalid training matrix')
    d=x.shape[1]
    # Positive/negative variable split gives exact L1 with smooth bounded solve.
    def objective(theta):
        w=theta[1:d+1]-theta[d+1:];z=theta[0]+x@w
        loss=np.logaddexp(0,z).sum()-y@z+.5*l2*np.dot(w,w)+l1*theta[1:].sum()
        p=1/(1+np.exp(-np.clip(z,-40,40)));res=p-y;g=x.T@res+l2*w
        return loss/len(rows),np.r_[res.sum(),g+l1,-g+l1]/len(rows)
    init=np.zeros(1+2*d);init[0]=math.log((y.sum()+.5)/(len(y)-y.sum()+.5))
    attempts=[]
    for attempt in range(3):
        result=minimize(objective,init,jac=True,method='L-BFGS-B',bounds=[(None,None)]+[(0,None)]*(2*d),
            options={'maxiter':1000 if attempt==0 else 2000,'ftol':1e-12 if attempt==0 else 1e-15,
                     'gtol':1e-6 if attempt==0 else 1e-8,'maxls':100})
        grad=result.jac.copy()*len(rows)
        grad[1:][(result.x[1:]<=1e-10)&(grad[1:]>0)]=0
        kkt=float(np.max(np.abs(grad))/len(rows))
        attempts.append({'optimizer_success':bool(result.success),'message':str(result.message),
                         'iterations':int(result.nit),'kkt_max_per_row':kkt})
        if result.success and kkt<=1e-4:break
        init=result.x.copy()
    else:
        raise RuntimeError(f'fitting convergence failed after bounded retries: {kkt:g}, basis={basis}, l1={l1}, l2={l2}')
    weights=result.x[1:d+1]-result.x[d+1:]
    weights[np.abs(weights)<1e-12]=0
    return {'feature_names':lifted_names(names,basis),'basis':basis,'intercept':float(result.x[0]),
        'weights':weights.tolist(),'n':len(rows),'positives':int(y.sum()),'training_prevalence':float(y.mean()),
        'l1':l1,'l2':l2,'estimator':'elastic_net_logistic' if l1 else 'ridge_logistic',
        'optimizer_converged':True,'optimizer_attempts':attempts,'kkt_max_per_row':kkt,'nonzero_weights':int(np.count_nonzero(weights))}

def folds_for(rows):
    seeds=sorted({r['seed'] for r in rows},key=str)
    if len(seeds)<3:raise ValueError('at least three independent seed/pool groups required')
    count=min(6,len(seeds))
    return [seeds[i::count] for i in range(count)]

def predictions(rows,head,names):
    return [{'prediction':sigmoid(head['intercept']+sum(w*x for w,x in zip(head['weights'],
        lift(r['x'],names,head.get('basis','identity'))))),'label':r['label']} for r in rows]

def select_fit(rows,names,grid=None):
    grid=list(GRID if grid is None else grid);groups=folds_for(rows);candidates=[]
    for basis,l1,l2 in grid+[( 'identity',0,None)]:
        folds=[];seed_losses=[]
        for group in groups:
            training=[r for r in rows if r['seed'] not in group];held=[r for r in rows if r['seed'] in group]
            head=fit_constant(training,names) if l2 is None else fit(training,names,l2,basis,l1)
            pred=predictions(held,head,names);constant=calibration([{'prediction':head['training_prevalence'],'label':r['label']} for r in held])
            by_seed=[]
            for seed in group:
                score=calibration([p for r,p in zip(held,pred) if r['seed']==seed])
                by_seed.append({'seed':seed,'score':score});seed_losses.append(score['log_loss'])
            folds.append({'held_out_seed':group[0] if len(group)==1 else None,'held_out_seeds':group,
                'training_seeds':sorted({r['seed'] for r in training},key=str),'score':calibration(pred),
                'seed_scores':by_seed,'constant_baseline':constant,'optimizer_converged':head['optimizer_converged'],
                'optimizer_attempts':head.get('optimizer_attempts',[]),'kkt_max_per_row':head.get('kkt_max_per_row',0)})
        candidates.append({'basis':basis,'l1':l1,'l2':l2,'mean_seed_log_loss':sum(seed_losses)/len(seed_losses),'folds':folds})
    def preference(c):return (c['mean_seed_log_loss'],0 if c['l2'] is None else 1,
        len(lifted_names(names,c['basis'])),-(c['l1'] or 0),-(c['l2'] or 0),c['basis'])
    best=min(candidates,key=preference)
    head=fit_constant(rows,names) if best['l2'] is None else fit(rows,names,best['l2'],best['basis'],best['l1'])
    return head,{'selection':'six-fold (or fewer) whole-seed/pool groups, equal seed log loss; no validation/final rows',
        'selected_basis':head['basis'],'selected_l1':head['l1'],'selected_l2':head['l2'],
        'selected_estimator':head['estimator'],'candidates':candidates,
        'warning':'Selected recorded introductions only; no population, causal or IPS claim.'}

def fit_duration(rows,names,alpha):
    basis='compact';x=np.asarray([lift(r['x'],names,basis) for r in rows]);y=np.asarray([r['hold_days']/40 for r in rows])
    xm=x.mean(axis=0);ym=y.mean();xc=x-xm
    w=np.linalg.solve(xc.T@xc+alpha*np.eye(x.shape[1]),xc.T@(y-ym))
    return {'basis':basis,'feature_names':lifted_names(names,basis),'weights':w.tolist(),
        'intercept':float(ym-xm@w),'alpha':alpha,'kind':'scheduled_hold_proxy_days','scale':40,'bounds':[8,40],
        'n':len(rows),'constant_days':float(40*ym)}

def duration_predict(head,x,names):
    v=head['intercept']+sum(w*v for w,v in zip(head['weights'],lift(x,names,head['basis'])))
    return min(40,max(8,40*v))

def select_duration(rows,names):
    candidates=[]
    for alpha in (100,1000):
        folds=[]
        for group in folds_for(rows):
            train=[r for r in rows if r['seed'] not in group];held=[r for r in rows if r['seed'] in group]
            h=fit_duration(train,names,alpha)
            mse=sum((duration_predict(h,r['x'],names)-r['hold_days'])**2 for r in held)/len(held)
            constant=sum((h['constant_days']-r['hold_days'])**2 for r in held)/len(held)
            folds.append({'held_out_seeds':group,'mse_days':mse,'constant_mse_days':constant})
        candidates.append({'alpha':alpha,'mean_fold_mse':sum(x['mse_days'] for x in folds)/len(folds),'folds':folds})
    best=min(candidates,key=lambda c:(c['mean_fold_mse'],-c['alpha']))
    head=fit_duration(rows,names,best['alpha']);head['use_constant']=best['mean_fold_mse']>=sum(f['constant_mse_days'] for f in best['folds'])/len(best['folds'])
    return head,{'selected_alpha':best['alpha'],'use_constant':head['use_constant'],'candidates':candidates}
