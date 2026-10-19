"""Cache identity includes the data generator, collecting policy and feature/label code."""
import platform
from pathlib import Path
from .storage import atomic_json, digest
from .registry import sha

ROOT=Path(__file__).resolve().parent.parent
COLLECTION_FILES=('starter/kit.py','starter/policy.py','blackbox/features.py','blackbox/domain.py',
                  'blackbox/labels.py','blackbox/experiment.py','blackbox/contracts.py','blackbox/cache.py',
                  'blackbox/policy.py','blackbox/clarification.py','blackbox/allocation.py','blackbox/model.py','blackbox/basis.py',
                  'blackbox/outcome_history.py','blackbox/registry.py','blackbox/storage.py')


def collection_identity(seed, variant, method, root=None):
    root=Path(root) if root else ROOT
    return {'schema_version':3,'seed':seed,'variant':variant,'method':method,
            'n':200,'decision_days':60,'follow_up_days':40,'python':platform.python_version(),
            'source':{name:sha(root/name) for name in COLLECTION_FILES}}


def load(path, identity):
    import json
    path=Path(path)
    if not path.exists():return None
    record=json.loads(path.read_text(encoding='utf-8'))
    if record.get('identity')!=identity or record.get('payload_sha256')!=digest(record.get('payload')):
        raise ValueError('training cache identity/integrity mismatch')
    return record['payload']


def save(path, identity, payload):
    atomic_json(path,{'identity':identity,'payload_sha256':digest(payload),'payload':payload})
