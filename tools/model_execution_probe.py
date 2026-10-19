"""Parity probe of existing model heads; no fitting and no performance estimate."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--compiled',action='store_true')
    a=p.parse_args();finder=None
    if a.compiled:
        from run_compiled import install
        _,finder=install()
    else:sys.path.insert(0,str(ROOT/'runtime'))
    from blackbox.model import load_model
    model=load_model();rows=json.load(sys.stdin);predictions=[]
    rank_heads=['rank_official','rank_auxiliary','rank_reference','rank_nohistory','rank_legacy_aux']
    for x in rows:
        predictions.append({'joint':model.predict(x),'auxiliary_msmi':model.predict_auxiliary_msmi(x),
                            'duration':model.predict_duration(x),
                            'ridge':model.predict(x,'joint_ridge'),'nohistory':model.predict(x,'joint_nohistory'),
                            'ranking':{name:model.rank_nudge(x,name) for name in rank_heads}})
    modules={name:type(module.__loader__).__name__ for name,module in sys.modules.items()
             if name=='blackbox' or name.startswith('blackbox.')}
    if a.compiled and any(loader!='SourcelessFileLoader' for loader in modules.values()):
        raise ValueError('A runtime module fell back to source execution.')
    print(json.dumps({'model_id':model.version,'predictions':predictions,'module_loaders':modules},
                     allow_nan=False,sort_keys=True))
    return 0


if __name__=='__main__':raise SystemExit(main())
