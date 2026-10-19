"""Safe JSON model loading; no pickle or training dependencies in inference."""
import hashlib,json,math
from pathlib import Path
from .features import FEATURE_VERSION,NAMES,DIRECTION_NAMES,pair_features
from .domain import SOFT
from .basis import lift,lifted_names

ROOT=Path(__file__).resolve().parent.parent

def sigmoid(z):
    return 1/(1+math.exp(-max(-40,min(40,z))))

class LinearModel:
    def __init__(self,artifact):
        if artifact['feature_version']!=FEATURE_VERSION:raise ValueError('feature version mismatch')
        if artifact.get('feature_source_sha256'):
            from .registry import feature_digest
            if artifact['feature_source_sha256']!=feature_digest():raise ValueError('feature implementation mismatch')
        self.artifact=artifact
        if artifact.get('basis_source_sha256') and artifact['basis_source_sha256']!=hashlib.sha256(Path(__file__).with_name('basis.py').read_bytes()).hexdigest():raise ValueError('basis source mismatch')
        for name,names in [('joint',NAMES),('direction',DIRECTION_NAMES)]:
            head=artifact[name]
            expected=lifted_names(names,head.get('basis','identity'))
            if len(head['weights'])!=len(expected) or head['feature_names']!=expected:raise ValueError('model dimensions')
            if not all(math.isfinite(v) for v in [head['intercept'],*head['weights']]):raise ValueError('non-finite model')
        for name in ('auxiliary','joint_ridge','joint_nohistory','duration'):
            if name not in artifact:continue
            head=artifact[name];expected=lifted_names(NAMES,head.get('basis','identity'))
            if head['feature_names']!=expected or len(head['weights'])!=len(expected):raise ValueError('auxiliary model dimensions')
            if not all(math.isfinite(v) for v in [head['intercept'],*head['weights']]):raise ValueError('non-finite auxiliary model')
        if artifact.get('ranking_source_sha256'):
            if artifact['ranking_source_sha256']!=hashlib.sha256(Path(__file__).with_name('ranking.py').read_bytes()).hexdigest():raise ValueError('ranking source mismatch')
        from .ranking import rank_names
        for name in ('rank_official','rank_auxiliary','rank_reference','rank_nohistory','rank_legacy_aux'):
            if name not in artifact:continue
            h=artifact[name]
            names=rank_names(h.get('ranking_projection','full'))
            if h.get('basis')!='identity' or h['feature_names']!=names or len(h['weights'])!=len(names):raise ValueError('ranking model schema')
            if not all(math.isfinite(v) for v in [h['intercept'],*h['weights']]):raise ValueError('non-finite ranking model')
        if not 0<=artifact.get('timeliness_factor',1)<=1:raise ValueError('invalid timeliness factor')
        if 'duration' in artifact and not 8<=artifact['duration'].get('constant_days',0)<=40:raise ValueError('invalid hold proxy')
    def predict(self,x,head='joint'):
        h=self.artifact[head]
        names=DIRECTION_NAMES if head=='direction' else NAMES
        x=lift(x,names,h.get('basis','identity'))
        if len(x)!=len(h['weights']) or not all(math.isfinite(v) for v in x):raise ValueError('invalid features')
        return sigmoid(h['intercept']+sum(w*v for w,v in zip(h['weights'],x)))
    def predict_auxiliary_msmi(self,x):
        return self.predict(x,'auxiliary')*self.artifact['timeliness_factor']
    def predict_duration(self,x):
        h=self.artifact['duration']
        if h.get('use_constant'):return h['constant_days']
        values=lift(x,NAMES,h['basis'])
        return max(8,min(40,40*(h['intercept']+sum(w*v for w,v in zip(h['weights'],values)))))
    def rank_nudge(self,x,head='rank_official'):
        from .ranking import project
        h=self.artifact[head];values=project(x,h.get('ranking_projection','full'))
        return sigmoid(h['intercept']+sum(w*v for w,v in zip(h['weights'],values)))
    @property
    def version(self):return self.artifact['model_id']


def load_model(path=None):
    if path is None:
        from .registry import load_artifact,episode_model
        cached=episode_model()
        return cached if cached is not None else LinearModel(load_artifact('model.json'))
    path=Path(path)
    raw=path.read_bytes()
    expected=path.with_suffix('.sha256').read_text().strip()
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('model hash mismatch')
    return LinearModel(json.loads(raw))

def score_pair(a,b,state,mode='soft',model=None,history=None):
    if mode in ('rank_tie','rank_aux','rank_ref','rank_nohistory','rank_legacy'):
        head={'rank_tie':'rank_official','rank_aux':'rank_auxiliary','rank_ref':'rank_reference',
              'rank_nohistory':'rank_nohistory','rank_legacy':'rank_legacy_aux'}[mode]
        h=model.artifact[head]
        nudge=sigmoid(h['intercept']) if not any(h['weights']) else model.rank_nudge(pair_features(a,b,state,history),head)
        return score_pair(a,b,state,'soft')+.25*nudge
    if mode=='constant':return 1.0
    if mode=='learned':return model.predict(pair_features(a,b,state,history))
    if mode=='goal_tie':
        return score_pair(a,b,state,'soft')+.25*float(a['fields'].get('relationship_goal') is not None and a['fields']['relationship_goal']==b['fields'].get('relationship_goal'))
    if mode in ('aux_hybrid','rate','ridge_tie','nohistory_tie'):
        x=pair_features(a,b,state,history)
        if mode=='rate':return model.predict_auxiliary_msmi(x)/model.predict_duration(x)
        p=(model.predict_auxiliary_msmi(x) if mode=='aux_hybrid' else
           model.predict(x,'joint_ridge' if mode=='ridge_tie' else 'joint_nohistory'))
        return score_pair(a,b,state,'soft')+.25*p
    if mode=='hybrid':
        # ML breaks exact heuristic-score ties; it cannot invert a one-point gap.
        return score_pair(a,b,state,'soft')+.25*model.predict(pair_features(a,b,state,history))
    return float(sum(a['fields'].get(k) is not None and a['fields'].get(k)==b['fields'].get(k) for k in SOFT))
