"""A v0.3 report generated from actual, identity-matched evidence only."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blackbox.provenance import execution_identity
from blackbox.registry import load_artifact,selected
from blackbox.storage import atomic_json
from blackbox.metrics import paired_interval


def read(name):
    path=ROOT/'results'/name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def main():
    current=execution_identity();config,manifest=selected();model=load_artifact('model.json')
    tests=read('tests.json');validation=read('validation.json');data=read('data_check.json')
    container=read('container_attestation.json');gate=read('release_readiness.json');training=read('training.json')
    tests_current=bool(tests and tests.get('identity')==current)
    validation_current=bool(validation and validation.get('config',{}).get('identity')==current)
    container_current=bool(container and container.get('identity')==execution_identity(mode='conservative'))
    lines=['# Blackbox v0.3 - engineering and ML evidence','',
        'All outcomes are synthetic. Validation is distinct from candidate promotion and production readiness.','',
        '## Build changes','',
        '- Strict typed hard constraints and observable timestamps; malformed hard fields fail before matching.',
        '- Content-addressed training caches bind generator, collection policy, feature/label code and runtime version.',
        '- Model and answer sampler are published together in an immutable, hash-verified release directory.',
        '- Deployment selection and rollback are atomic pointer changes; fitting does not imply promotion.',
        '- SQLite ownership leases, heartbeats, stale-owner rejection and append-only attempt history.',
        '- Tests, validation matrices, frozen plans and Docker attestations bind exact code and inference assets.',
        '- Windows/WSL runner supervises child processes within a requested maximum 120-minute budget.',
        '- Test-pass counts are read from real test results, never hardcoded.','',
        '- Hard-killed episode owners recover through OS-held owner locks without a lease wait; legacy owners retain lease fallback.',
        '- Docker base-image preparation precedes training; baseline and learned container assessments precede validation, with downstream reservations.',
        '- Joint and directional regularization use leave-one-training-seed-out selection; final-test outcomes never enter fitting.',
        '- Promotion requires independent learned-policy container evidence, in addition to statistical and service gates.','',
        '## Current identity','',f'Release: `{config["release_id"]}`.',f'Model: `{model["model_id"]}`.',
        f'Full source/configuration: `{current["source_sha256"]}`.','',
        '## Training','',f'Bundle model training rows: {model["joint"]["n"]}; positive MSMI outcomes: {model["joint"]["positives"]}.',
        'Training lineage and package versions are embedded in the immutable release manifest. Imported v0.1 assets are identified explicitly when applicable.']
    if training and training.get('release_id')==config['release_id']:
        lines += [f'Training evidence covers {len(training["episodes"])} episodes; training-pipeline wall time (cache reuse may apply) {training["wall_seconds"]:.1f} seconds.']
    selection=read('model_selection.json')
    if selection and selection.get('release_id')==config['release_id']:
        lines+=['','Training-only regularization selection (equal seed weight):','',
                '| Head | L2 | Seed-held-out log loss | Constant-prevalence log loss |','| --- | --- | --- | --- |']
        for head in ('joint','direction'):
            detail=selection[head];chosen=next(c for c in detail['candidates'] if c['l2']==detail['selected_l2'])
            constant=sum(f['constant_baseline']['log_loss'] for f in chosen['folds'])/len(chosen['folds'])
            lines += [f'| {head} | {detail["selected_l2"]} | {chosen["mean_seed_log_loss"]:.6f} | {constant:.6f} |']
        lines+=['','These are predictive diagnostics on selected introductions, not evidence that the policy improves MSMI.']
    lines += ['', '## Tests and data','']
    if tests_current:
        lines += [f'Actual tests run: {tests["tests_run"]}; success: {tests["success"]}.']
        for suite in tests['suites']:
            lines += [f'- {suite["suite"]}: {suite["tests_run"]} tests, {suite["failures"]} failures, {suite["errors"]} errors, {suite["skipped"]} skipped.']
    else:lines += ['Current tests are missing or belong to a different code/asset identity. No pass is inferred.']
    data_ok=bool(data and data.get('identity')==current and data.get('verified') is True)
    lines += [f'Public-byte checksum verification: {"passed for "+str(data["files"])+" files" if data_ok else "unverified for this identity"}.','',
        '## Policy validation','']
    if validation_current:
        lines += [f'Episodes present: {len(validation["episodes"])} / {validation["expected_episodes"]}; complete: {validation["complete"]}; all valid including prior failed attempts: {validation["all_valid"]}.',
                  'Methods share worlds. Repeated policy runs are executions, not independent populations. Confidence intervals resample seed blocks.','',
                  '| Method | MSMI pairs | MSMI per 100 | Coverage |','| --- | --- | --- | --- |']
        for name in validation['methods']:
            rows=[r for r in validation['episodes'] if r['method']==name]
            if rows and all(r['valid'] for r in rows):
                from blackbox.experiment import summarise
                summary=summarise(rows)
                lines += [f'| {name} | {sum(r["mutual_second_meeting_intention"] for r in rows)} | {summary["primary_score"]:.4f} | {100*summary["overall"]["coverage"]:.2f}% |']
            else:lines += [f'| {name} | incomplete/invalid | n/a | n/a |']
        if {'conservative','learned'}<=set(validation['methods']):
            interval=paired_interval(validation['episodes'],'learned')
            lines += ['',f'Learned-minus-conservative paired pilot result: `{json.dumps(interval)}`.',
                      'A pilot does not establish statistical power or justify test-seed tuning.']
        lines+=['','Per-family pilot scores (MSMI per 100):','','| Family | Conservative | Learned |','| --- | --- | --- |']
        for variant in validation['variants']:
            means={m: [r['msmi_per_100_arrived_members'] for r in validation['episodes'] if r['method']==m and r['variant']==variant and r['valid']] for m in ('conservative','learned')}
            if all(means.values()):lines += [f'| {variant} | {sum(means["conservative"])/len(means["conservative"]):.4f} | {sum(means["learned"])/len(means["learned"]):.4f} |']
    else:lines += ['No current validation matrix is available; older results are not attributed to this build.']
    lines += ['', '## Container and release state','',
        f'Container evidence: {container.get("status") if container_current else "unverified or stale"}.',
        f'Validation gate: {gate.get("status") if gate and gate.get("identity")==current else "not assessed for this identity"}.',
        'Attestation records bind local content hashes and immutable image IDs. They are not digitally signed certificates.',
        'No candidate is automatically promoted by this workflow. The default remains conservative.',
        'The Docker image must run on the Windows/WSL2 host before Docker/resource compliance can be claimed. Hosted CI and native PowerShell execution are not inferred from supplied configuration.','',
        '## Remaining research limits','',
        '- Rare positive labels, selective collection and simulator transfer remain unresolved statistical issues.',
        '- The answer model is a selected empirical bundle approximation, not unbiased exact EVSI.',
        '- Equal-compute complementary-question tests and controlled allocation tie ablations remain necessary.',
        '- A larger frozen final test is not automatically included in the two-hour pilot budget.',
        '- Episode JSON includes mature feature missingness, score quantiles, calibration and service slices by family; selective labels still limit interpretation.',
        '- Base-image digest pinning and a full third-party dependency-license audit remain release-hardening tasks.','',
        'Prior v0.1/v0.2 evidence is archived under evidence and is not counted as v0.3 verification.','']
    final=read('final_test.json');plan=ROOT/'plans/final_test.json'
    if final and final.get('config',{}).get('identity')==current:
        lines+=['## Frozen final test','',f'Complete: {final["complete"]}; valid: {final["all_valid"]}; episodes: {len(final["episodes"])}.',
                f'Paired learned-minus-conservative result: `{json.dumps(paired_interval(final["episodes"],"learned"))}`.',
                'Ten seed blocks meet the minimum gate count; this does not establish adequate statistical power.']
        if gate and gate.get('identity')==current:lines += ['',f'Promotion assessment: `{json.dumps(gate["candidate_promotion"])}`.']
        lines+=['']
    (ROOT/'results').mkdir(exist_ok=True)
    (ROOT/'results/REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    atomic_json(ROOT/'results/verification_summary.json',{'schema_version':2,'identity':current,
        'tests_run':tests['tests_run'] if tests_current else None,'tests_success':tests['success'] if tests_current else False,
        'public_data_verified':data_ok,'evaluated_episodes':len(validation['episodes']) if validation_current else 0,
        'validation_complete':validation['complete'] if validation_current else False,
        'all_evaluated_valid':validation['all_valid'] if validation_current else False,
        'container_verified':bool(container_current and container.get('validated') is True),
        'candidate_promoted':False})
    print(ROOT/'results/REPORT.md')

if __name__=='__main__':main()
