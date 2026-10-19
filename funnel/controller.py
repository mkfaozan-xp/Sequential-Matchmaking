"""Isolated scorer dependency injection into the unchanged common planner."""
import hashlib,importlib.util,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'runtime'));sys.path.insert(0,str(ROOT))
from blackbox.features import pair_features
from blackbox.ranking import project

class FunnelController:
 def __init__(self):
  release=json.loads((ROOT/'funnel/release.json').read_text())
  for name,expected in release['files'].items():
   if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise ValueError('funnel subject changed: '+name)
  self.model=json.loads((ROOT/'funnel/model.json').read_text())
  spec=importlib.util.spec_from_file_location('funnel_isolated_planner',ROOT/'coordinated/engine.py')
  self.planner=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.planner)
  self.planner.estimates=self.estimates;self.planner.load_model=lambda:self.model
 def estimates(self,a,b,state,model,history,constant=False):
  if constant:raise ValueError('unregistered funnel ablation')
  x=project(pair_features(a,b,state,history),'reference')
  def predict(h,v):return 1/(1+math.exp(-max(-40,min(40,h['intercept']+sum(w*t for w,t in zip(h['weights'],v))))))
  p=self.predict_x(x)
  h=model['hold'];hold=max(8,min(40,40*(h['intercept']+sum(w*t for w,t in zip(h['weights'],x)))))
  return p,hold
 def predict_x(self,x):
  model=self.model
  def predict(h,v):return 1/(1+math.exp(-max(-40,min(40,h['intercept']+sum(w*t for w,t in zip(h['weights'],v))))))
  return predict(model['acceptance'],x)*predict(model['conversion'],[x[i] for i in model['conversion_indices']])*model['timeliness_factor']
 def decide(self,request):
  out=self.planner.decide(request);out['memory']['mode']='funnel';out['memory']['diagnostics']['engine']='funnel-common-planner';return out
