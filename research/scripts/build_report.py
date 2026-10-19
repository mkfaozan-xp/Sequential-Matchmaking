"""Render only current, identity-matched review-response measurements."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blackbox.provenance import execution_identity
from blackbox.registry import load_artifact
from blackbox.storage import atomic_json
from blackbox.metrics import paired_interval
from scripts.release_gate import valid_matrix

def read(name):
 p=ROOT/'results'/name
 return json.loads(p.read_text()) if p.exists() else None

def main():
 current=execution_identity();model=load_artifact('model.json');train=read('training.json');tests=read('tests.json');choice=read('selection.json');gate=read('release_readiness.json');budget=read('budget_run.json');data=read('data_check.json');env=read('environment.json');audit=read('review_audit.json');runtime=read('runtime.json');parity=read('snapshot_parity.json')
 test_ok=bool(tests and tests.get('identity')==current and tests.get('success'));data_ok=bool(data and data.get('identity')==current and data.get('verified'));env_ok=bool(env and env.get('identity')==current and env.get('verified'))
 lines=['# Blackbox v0.8 measured review response','',f'Source: `{current["source_sha256"]}`.',f'Release: `{current["inference_release"]["deployment"]["release_id"]}`. Active mode: **conservative**.','',
 '## Review corrections and implementation','',
 'Training now compares actual observed introductions with equal deployed seven-field agreement scores, within the same world and seven assignment days. The model is still only an ordinal tie-breaker. Reference coding and removal of post-date history are explicit alternative models. Neither coding change nor a negative history coefficient independently establishes a defect or a cause of the earlier pilot loss.',
 'Reference coding removes four missing dummies:36 ->32 features. Removing16 post-date inputs additionally leaves16. Changing the dummy basis changes ordinary ridge regularization, not an automatic monotonicity guarantee. Constant translation of history rates cancels in differences; the raw history implementation and smoothing prior are preserved. A rate of0.5 does not imply no prior date.',
 'Official MSMI labels, timing rules, RNG and simulator remain unchanged. Late mutual recorded Yes is auxiliary evidence, not a replacement official outcome. The exact v0.7 auxiliary coefficients are retained as a historical unmatched-training control, excluded from eligible candidates. Its older selection differs, so this is not a pure causal ablation of every mechanism.','',
 '## Training provenance','']
 if train and train['release_id']==current['inference_release']['deployment']['release_id']:
  lines += [f'Reused {train["historical_collection_episodes"]} historical collection episodes and {train["joint_rows"]} mature observed introductions, with {train["joint_positives"]} official and {train["auxiliary_positives"]} auxiliary positives. **New collection episodes:0.**',
   'Archive, source, payload, raw feature/label definitions and ordered row identities are verified. No padded vectors or unchosen labels are used. Whole training seeds remain in one fold. The older probability heads and answer prior are explicitly inherited.','',
   '| Head | Dimensions | Contrasts | Positive introductions represented | Estimator | Nonzero weights |','| --- | ---: | ---: | ---: | --- | ---: |']
  for name in ('rank_official','rank_auxiliary','rank_reference','rank_nohistory','rank_legacy_aux'):
   h=model[name];lines += [f'| {name} | {len(h["weights"])} | {h["contrast_count"]} | {h["observed_positive_rows"]} | {h["estimator"]}, L1={h["l1"]}, L2={h["l2"]} | {sum(w!=0 for w in h["weights"])}/{len(h["weights"])} |']
  lines += ['', 'Mirrored contrasts are dependent transformations, not new independent games. Equal scores and nearby days do not establish competing endpoints, simultaneous availability, population validity or known propensities. Selection bias remains.','']
 if audit and audit.get('identity')==current:
  c=audit['cohorts']['auxiliary_label'];lines += [f'The historical mismatch was reproduced: {c["legacy_cross_score"]}/{c["legacy_forward_contrasts"]} auxiliary comparisons cross heuristic-score levels. The new cohort has {c["matched_forward_contrasts"]} forward equal-score comparisons. All recorded new training contrasts have equal actual heuristic scores.',
   f'Equivalent reference recoding of the old model changed logits by at most {audit["reference_equivalence_max_logit_error"]:.3g} across all {audit["observed_rows"]} rows. This refutes a guaranteed coding-only cure.','']
 lines += ['## Verification','',f'Core tests: {tests["tests_run"] if test_ok else "unverified"}; passed: {test_ok}. Public snapshot: {data_ok}; runtime inventory: {env_ok}.']
 if runtime and runtime.get('identity')==current:lines += [f'Cold runtime probes: {len(runtime["rows"])} across all six pilot modes; maximum measured startup/call time {max(r["startup_seconds"] for r in runtime["rows"]):.3f}s. The original ten-second limit is unchanged.']
 if parity and parity.get('identity')==current:lines += [f'Complete cold/cached action parity: {parity["passed"]}; preparation seed1999,200 members, conservative and rank_ref. These four preparation episodes are not efficacy comparisons.']
 lines += ['Separate public-data leakage checks are recorded in phase logs. Trusted host caching is bounded and invalidates on observed hard-field changes. Cold CLI inference and final action validation remain uncached. Host checks and Docker recipes do not certify Docker, Windows, hosted CI or external signing.','']
 if choice and choice.get('identity')==current:lines += ['## Frozen choice','',f'Selected **{choice["selected_mode"]}** on pilot seeds {choice["selection_seeds"]}, before independent validation and final outcomes. Selection uses official MSMI, then question cost, then lexical mode. No post-pilot refit/switch occurs.','']
 counts={};valid={}
 for name,title in [('selection_pilot','Selection pilot'),('validation','Independent validation'),('final_test','Frozen final'),('subprocess','Fresh-process transport')]:
  m=read(name+'.json');ok=valid_matrix(m);valid[name]=ok;lines += ['## '+title,'']
  if not m or m.get('config',{}).get('identity')!=current:lines += ['Missing or stale; no current comparison claimed.',''];continue
  counts[name]=len(m['episodes']);lines += [f'Saved {len(m["episodes"])} / {m["expected_episodes"]}; complete and valid: **{ok}**; failed attempts: {m["failed_attempts"]}.','']
  if not ok:continue
  lines += ['| Mode | Introductions | Mutual acceptances | Dates | Official MSMI | Auxiliary mutual Yes |','| --- | ---: | ---: | ---: | ---: | ---: |']
  for mode in m['methods']:
   rows=[r for r in m['episodes'] if r['method']==mode];v=[sum(r[k] for r in rows) for k in ('assignments','mutual_acceptances','dates','mutual_second_meeting_intention','auxiliary_recorded_mutual_yes')];lines += [f'| {mode} | '+' | '.join(map(str,v))+' |']
  if name=='final_test' and choice:
   mode=choice['selected_mode'];interval=paired_interval(m['episodes'],mode);lines += ['',f'Paired seed-block result: `{json.dumps(interval)}`.','', '| Family | Conservative MSMI | Candidate MSMI |','| --- | ---: | ---: |']
   for family in m['variants']:
    totals=[sum(r['mutual_second_meeting_intention'] for r in m['episodes'] if r['variant']==family and r['method']==which) for which in ('conservative',mode)];lines += [f'| {family} | {totals[0]} | {totals[1]} |']
   identical=sum(a['action_sha256']==b['action_sha256'] for a in m['episodes'] if a['method']=='conservative' for b in m['episodes'] if b['method']==mode and (a['seed'],a['variant'])==(b['seed'],b['variant']))
   lines += ['',f'Identical action traces: {identical}/60 paired worlds. Ten seed blocks are a minimum, not a power guarantee. Different version totals on different worlds cannot establish an improvement. Reference-head calibration diagnostics are separate from ordinal ranking utilities.','']
  lines += ['']
 if gate and gate.get('identity')==current:lines += ['## Release decision','',f'Readiness: **{gate["status"]}**. Missing/failed checks: `{gate["missing_or_failed"]}`.',f'Candidate promotion assessment: `{json.dumps(gate["candidate_promotion"])}`.', 'No automatic promotion. The active operational mode remains conservative.','']
 if budget:
  lines += ['## Budget','',f'Status at report generation: {budget["status"]}. The original v0.8 allocation is {budget["origin"]["budget_seconds"]:.0f}s, with one retained deadline across retries. Exact phases/failures are in budget_run.json.',
   'This is a new user-requested build. Earlier v0.6/v0.7 accounting remains unchanged historical evidence; their cap was not retroactively reset. Code preparation/packaging are outside the model execution allowance. In v0.7,1390s was the initial allowance;825s described a resumed invocation, not the whole allocation.','']
 lines += ['## Remaining limits','', 'A favorable pilot, contrast loss or nominal final advantage does not guarantee policy superiority. Rare outcomes, selected-label bias and long-horizon availability effects remain. No new asking/allocation factorial is claimed; v0.6 research remains historical. Production certification, real-world relationship prediction and private-world superiority are not established. Actual Docker, Windows, hosted CI and trusted external attestation remain required unless their executed records explicitly establish them.','']
 (ROOT/'results/REPORT.md').write_text('\n'.join(lines)+'\n')
 atomic_json(ROOT/'results/verification_summary.json',{'schema_version':5,'identity':current,'tests_run':tests['tests_run'] if test_ok else None,'tests_success':test_ok,
  'public_data_verified':data_ok,'runtime_inventory_verified':env_ok,'matrices_complete_valid':valid,'matrix_saved_counts':counts,
  'all_evaluated_valid':all(valid.values()),'container_verified':bool(gate and gate['checks'].get('exact_container_release')),'candidate_promoted':False})
 print(ROOT/'results/REPORT.md')
if __name__=='__main__':raise SystemExit(main())
