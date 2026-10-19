"""One declared pilot choice; final outcomes cannot select or refit it."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blackbox.provenance import execution_identity
from blackbox.storage import atomic_json
from scripts.release_gate import valid_matrix
ELIGIBLE=('hybrid','aux_hybrid','outcome','rate')
PILOT=('conservative','hybrid','aux_hybrid','outcome','rate','ridge_tie','nohistory_tie','goal_tie')

def choose(data):
    if not valid_matrix(data) or data['seeds']!=list(range(2601,2605)) or tuple(data['methods'])!=PILOT:
        raise ValueError('complete bound predeclared selection pilot required')
    scores={}
    for mode in PILOT:
        rows=[r for r in data['episodes'] if r['method']==mode]
        scores[mode]={'msmi_pairs':sum(r['mutual_second_meeting_intention'] for r in rows),
            'mean_msmi_per_100':sum(r['msmi_per_100_arrived_members'] for r in rows)/len(rows),
            'ask_cost':sum(r['ask_cost'] for r in rows),'episodes':len(rows)}
    mode=min(ELIGIBLE,key=lambda m:(-scores[m]['mean_msmi_per_100'],scores[m]['ask_cost'],m))
    return {'schema_version':1,'identity':execution_identity(),'selected_mode':mode,'pilot_scores':scores,
        'eligible_modes':list(ELIGIBLE),'selection_rule':'highest official MSMI mean, fewer question units, lexical name',
        'selection_seeds':data['seeds'],'frozen_before_final':True,
        'warning':'Pilot-selected candidate; selection results are exploratory, final is independent. No automatic deployment.'}

RANK_PILOT=('conservative','rank_tie','rank_aux','rank_ref','rank_nohistory','rank_legacy')
RANK_ELIGIBLE=('rank_tie','rank_aux','rank_ref','rank_nohistory')

def choose_ranking(data):
    if not valid_matrix(data) or data['seeds']!=[2953,2954] or tuple(data['methods'])!=RANK_PILOT:
        raise ValueError('complete bound v0.8 score-matched pilot required')
    scores={}
    for mode in RANK_PILOT:
        rows=[r for r in data['episodes'] if r['method']==mode]
        scores[mode]={'msmi_pairs':sum(r['mutual_second_meeting_intention'] for r in rows),
            'mean_msmi_per_100':sum(r['msmi_per_100_arrived_members'] for r in rows)/len(rows),
            'ask_cost':sum(r['ask_cost'] for r in rows),'episodes':len(rows)}
    mode=min(RANK_ELIGIBLE,key=lambda m:(-scores[m]['mean_msmi_per_100'],scores[m]['ask_cost'],m))
    return {'schema_version':2,'identity':execution_identity(),'selected_mode':mode,'pilot_scores':scores,
        'eligible_modes':list(RANK_ELIGIBLE),'selection_rule':'highest official MSMI mean, fewer question units, lexical name',
        'selection_seeds':data['seeds'],'frozen_before_final':True,
        'warning':'Ranking utility is not calibrated probability. Pilot selection is exploratory; final is independent. No automatic deployment.'}


def main():
    data=json.loads((ROOT/'results/selection_pilot.json').read_text());record=choose_ranking(data)
    path=ROOT/'results/selection.json'
    if path.exists() and json.loads(path.read_text())!=record:raise ValueError('do not overwrite a different frozen selection')
    atomic_json(path,record)
    subprocess.run([sys.executable,str(ROOT/'scripts/freeze_plan.py'),'--seeds',','.join(map(str,range(3701,3711))),
        '--methods','conservative,'+record['selected_mode'],'--reuse-if-matching'],cwd=ROOT,check=True)
    print(json.dumps(record))
if __name__=='__main__':main()
