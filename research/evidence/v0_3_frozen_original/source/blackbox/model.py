"""Safe JSON model loading; no pickle or training dependencies in inference."""
import hashlib,json,math
from pathlib import Path
from .features import FEATURE_VERSION,NAMES,DIRECTION_NAMES,pair_features
from .domain import SOFT

ROOT=Path(__file__).resolve().parent.parent

def sigmoid(z):
    return 1/(1+math.exp(-max(-40,min(40,z))))

class LinearModel:
    def __init__(self,artifact):
        if artifact['feature_version']!=FEATURE_VERSION:raise ValueError('feature version mismatch')
        self.artifact=artifact
        for name,names in [('joint',NAMES),('direction',DIRECTION_NAMES)]:
            head=artifact[name]
            if len(head['weights'])!=len(names) or head['feature_names']!=names:raise ValueError('model dimensions')
            if not all(math.isfinite(v) for v in [head['intercept'],*head['weights']]):raise ValueError('non-finite model')
    def predict(self,x,head='joint'):
        h=self.artifact[head]
        if len(x)!=len(h['weights']) or not all(math.isfinite(v) for v in x):raise ValueError('invalid features')
        return sigmoid(h['intercept']+sum(w*v for w,v in zip(h['weights'],x)))
    @property
    def version(self):return self.artifact['model_id']


def load_model(path=None):
    if path is None:
        from .registry import load_artifact
        return LinearModel(load_artifact('model.json'))
    path=Path(path)
    raw=path.read_bytes()
    expected=path.with_suffix('.sha256').read_text().strip()
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('model hash mismatch')
    return LinearModel(json.loads(raw))

def score_pair(a,b,state,mode='soft',model=None,history=None):
    if mode=='constant':return 1.0
    if mode=='learned':return model.predict(pair_features(a,b,state,history))
    return float(sum(a['fields'].get(k) is not None and a['fields'].get(k)==b['fields'].get(k) for k in SOFT))
