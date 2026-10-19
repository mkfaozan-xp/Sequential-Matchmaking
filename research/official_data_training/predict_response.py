"""Standard-library diagnostic inference for the public-data response head.

Accepts the existing refreshed match request, emits diagnostics, never actions.
"""
import hashlib
import itertools
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blackbox.basis import lift, lifted_names
from blackbox.contracts import LIMIT, validate_request
from blackbox.domain import eligibility
from blackbox.features import DIRECTION_NAMES, direction_features, response_history
from blackbox.model import sigmoid


def main():
    raw = sys.stdin.buffer.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('request exceeds 1 MiB')
    request = json.loads(raw)
    validate_request(request)
    if request['phase'] != 'match':
        raise ValueError('diagnostics require refreshed match observations')
    folder = ROOT/'official_data_training/results'
    report = json.loads((folder/'training_report.json').read_text())
    model_bytes = (folder/'response_model.json').read_bytes()
    if hashlib.sha256(model_bytes).hexdigest() != report['model_sha256']:
        raise ValueError('response model integrity mismatch')
    model = json.loads(model_bytes)
    for name in ('blackbox/features.py', 'blackbox/domain.py', 'blackbox/basis.py', 'blackbox/model.py','blackbox/outcome_history.py'):
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != model['lineage']['source'][name]:
            raise ValueError('inference feature/basis source mismatch')
    head = model['direction']
    basis = head.get('basis', 'identity')
    if head['feature_names'] != lifted_names(DIRECTION_NAMES, basis) or len(head['weights']) != len(head['feature_names']):
        raise ValueError('response head dimensions')
    if not all(math.isfinite(x) for x in [head['intercept'], *head['weights']]):
        raise ValueError('nonfinite response head')
    state = request['state']
    history = response_history(state)
    past = {frozenset((i['user_a'], i['user_b'])) for i in state['introductions']}
    output = []
    for a, b in itertools.combinations(state['members'], 2):
        if not a['available'] or not b['available'] or frozenset((a['member_id'], b['member_id'])) in past:
            continue
        if eligibility(a, b)['status'] != 'feasible':
            continue
        predictions = {}
        for actor, other in ((a, b), (b, a)):
            x = lift(direction_features(actor, other, state, history), DIRECTION_NAMES, basis)
            predictions[actor['member_id']] = sigmoid(head['intercept'] + sum(w*v for w,v in zip(head['weights'], x)))
        output.append({'pair': [a['member_id'], b['member_id']], 'recorded_yes_probability': predictions})
        if len(output) == 10:
            break
    print(json.dumps({'status': 'experimental_diagnostics_only', 'model_sha256': report['model_sha256'],
        'pairs_in_input_order_up_to_10': output,
        'warning': 'Directional response estimates are not a joint MSMI probability or an action recommendation.'}, allow_nan=False))


if __name__ == '__main__':
    main()
