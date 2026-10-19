"""Fit a separate public-data response candidate; never changes deployment pointers."""
import copy
import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blackbox.domain import HARD
from blackbox.features import DIRECTION_NAMES, direction_features
from blackbox.metrics import calibration
from blackbox.model import sigmoid
from blackbox.basis import lift
from blackbox.storage import atomic_json, digest
from train import select_fit


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decision_members(snapshot, day):
    """A conservative timestamp mask, never a backward join of current profiles.

    Public v1 fields are static truths; a later reconfirmation is masked even if
    it might have been known earlier. No simulator seed reconstruction is used.
    Availability at day 30 is not a predictive feature.
    """
    members = {}
    for source in snapshot['members']:
        if source['arrived_day'] > day:
            continue
        member = copy.deepcopy(source)
        for field in member['fields']:
            observed = member['field_observed_day'][field]
            if observed is None or observed > day:
                member['fields'][field] = None
        members[member['member_id']] = member
    return members


def rows_for_pool(snapshot, pool):
    rows = []
    excluded = 0
    for intro in snapshot['introductions']:
        # Cohort maturity is fixed independently of an early positive/negative.
        # This avoids selecting only early responses from still-pending cohorts.
        if intro['response_deadline_day'] > snapshot['day']:
            excluded += 2
            continue
        day = intro['assigned_day']
        members = decision_members(snapshot, day)
        if intro['user_a'] not in members or intro['user_b'] not in members:
            raise ValueError('introduction precedes member arrival')
        state = {'day': day, 'introductions':[i for i in snapshot['introductions'] if i['assigned_day']<day], 'feedback': [e for e in snapshot['feedback']
                 if e['observed_day'] <= day
                 and e['introduction_id'] != intro['introduction_id']]}
        for actor, other in ((intro['user_a'], intro['user_b']),
                             (intro['user_b'], intro['user_a'])):
            responses = [e for e in snapshot['feedback']
                         if e['introduction_id'] == intro['introduction_id']
                         and e['member_id'] == actor
                         and e['event'] == 'introduction_response'
                         and e['observed_day'] <= snapshot['day']]
            if len(responses) != 1:
                raise ValueError('mature response event missing or duplicated')
            label = int(responses[0]['value'] == 'yes')
            rows.append({'seed': pool, 'row_id': intro['introduction_id'] + ':' + actor,
                         'assigned_day': day, 'label': label,
                         'x': direction_features(members[actor], members[other], state)})
    return rows, excluded


def evaluate(rows, head):
    predictions = [{'prediction': sigmoid(head['intercept'] + sum(w*x for w,x in
        zip(head['weights'], lift(r['x'], DIRECTION_NAMES, head.get('basis', 'identity'))))),
        'label': r['label']} for r in rows]
    return calibration(predictions)


def main():
    kit = ROOT / 'starter'
    manifest = json.loads((kit/'data_manifest.json').read_text())
    checks = json.loads((kit/'data_checksums.json').read_text())
    splits = manifest['splits']
    sets = [set(splits[k]) for k in ('train', 'validation', 'development_test')]
    if any(sets[i] & sets[j] for i in range(3) for j in range(i)):
        raise ValueError('overlapping organiser splits')
    records, inventories, donors = {}, {}, []
    # Do not open development-test pools in this fitting/selection workflow.
    for split in ('train', 'validation'):
        records[split] = []
        for pool in splits[split]:
            relative = 'data/' + pool + '/state.json'
            path = kit/relative
            if sha(path) != checks[relative]:
                raise ValueError('official input checksum mismatch: ' + relative)
            snapshot = json.loads(path.read_text())
            if not snapshot['synthetic'] or snapshot['day'] != 30:
                raise ValueError('unsupported snapshot contract')
            rows, pending = rows_for_pool(snapshot, pool)
            records[split].extend(rows)
            inventories[pool] = {'split': split, 'sha256': sha(path),
                'members': len(snapshot['members']), 'mature_response_rows': len(rows),
                'pending_response_rows_excluded': pending}
            if split == 'train':
                for m in snapshot['members']:
                    if all(m['fields'][k] is not None for k in HARD):
                        donors.append({'age': m['age'], 'zone': m['zone'],
                            'fields': {k: m['fields'][k] for k in HARD}})
    head, selection = select_fit(records['train'], DIRECTION_NAMES)
    constant = dict(head, intercept=__import__('math').log(head['training_prevalence'] /
        (1-head['training_prevalence'])), weights=[0.0]*len(head['weights']))
    code = {'official_data_training/train_public.py': sha(Path(__file__)),
        **{p: sha(ROOT/p) for p in ('train.py', 'blackbox/features.py',
           'blackbox/domain.py', 'blackbox/basis.py', 'blackbox/metrics.py',
           'blackbox/model.py', 'blackbox/storage.py', 'blackbox/outcome_history.py','blackbox/fitting.py')}}
    lineage = {'official_commit': 'a8e26b35118cfa8e886a02f93984923e43ab64f6',
        'inputs': inventories, 'manifest_sha256': sha(kit/'data_manifest.json'),
        'source': code, 'row_sha256': digest(records['train']),
        'runtime': {'python': platform.python_version(),
                    'packages': {p: importlib.metadata.version(p) for p in ('numpy','scipy')}},
        'train_pools': splits['train'], 'validation_pools': splits['validation'],
        'development_test_pools_not_read': splits['development_test']}
    model = {'schema_version': 1, 'task': 'recorded_introduction_response_by_deadline',
        'status': 'experimental_not_deployed', 'direction': head, 'lineage': lineage}
    target = ROOT/'official_data_training/results'
    atomic_json(target/'response_model.json', model)
    atomic_json(target/'model_selection.json', selection)
    atomic_json(target/'answers.json', {'donors': donors, 'train_pools': splits['train'],
        'scope': 'empirical complete observed hard bundles at day 30; selected disclosure bias; no IPS'})
    result = {'schema_version': 1, 'lineage': lineage,
        'train_rows': len(records['train']), 'train_positives': sum(r['label'] for r in records['train']),
        'validation_rows': len(records['validation']), 'donors': len(donors),
        'selected_basis': head.get('basis', 'identity'), 'selected_l2': head['l2'],
        'validation': evaluate(records['validation'], head),
        'validation_constant': evaluate(records['validation'], constant),
        'validation_by_pool': {p: evaluate([r for r in records['validation'] if r['seed']==p], head)
                               for p in splits['validation']},
        'model_sha256': sha(target/'response_model.json'),
        'deployment_changed': False,
        'limits': ['Response acceptance is not MSMI or preference truth.',
          'Unknown historical propensities; selected introductions only.',
          'No historical MSMI negatives fabricated from day-30 censoring.',
          'Conservative timestamp masking may lose previously known reconfirmed fields.',
          'Validation has two independent pools; no superiority claim or automatic promotion.',
          'Candidate is separate from the frozen simulator-policy experiments.']}
    atomic_json(target/'training_report.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
