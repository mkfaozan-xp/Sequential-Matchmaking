"""Fixed matrix definitions keep runtime selection separate from test outcomes."""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blackbox.provenance import execution_identity
from scripts.select_candidate import RANK_PILOT

def command(matrix,jobs):
    if matrix=='selection':seeds=[2953,2954];methods=RANK_PILOT;output='selection_pilot';extra=[]
    else:
        selection=json.loads((ROOT/'results/selection.json').read_text())
        if selection['identity']!=execution_identity():raise ValueError('selection source/assets mismatch')
        candidate=selection['selected_mode'];extra=[]
        if matrix=='validation':seeds=[3051,3052];methods=('baseline_greedy','baseline_no_asks','baseline_random','conservative',candidate);output='validation'
        elif matrix=='final':seeds=list(range(3701,3711));methods=('conservative',candidate);output='final_test';extra=['--locked-test-plan','plans/final_test.json']
        elif matrix=='subprocess':seeds=[101];methods=('conservative',candidate);output='subprocess';extra=['--transport','subprocess']
        else:raise ValueError('unknown matrix')
    return [sys.executable,'evaluate.py','--seeds',','.join(map(str,seeds)),'--methods',','.join(methods),
            '--output','results/'+output+'.json','--jobs',str(jobs)]+extra

def main():
    p=argparse.ArgumentParser();p.add_argument('--matrix',required=True,choices=['selection','validation','final','subprocess']);p.add_argument('--jobs',type=int,choices=[1,2],default=2);a=p.parse_args()
    return subprocess.run(command(a.matrix,a.jobs),cwd=ROOT).returncode
if __name__=='__main__':raise SystemExit(main())
