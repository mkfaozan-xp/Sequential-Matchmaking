"""Content-addressed, immutable local releases; atomic deployment selection."""
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from .features import FEATURE_VERSION
from .storage import atomic_json, canonical, digest

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def feature_digest(root=None):
    root = Path(root) if root else ROOT
    return digest({name:sha(root/'blackbox'/name) for name in ('features.py','domain.py')})


def publish(model, answers, lineage, root=None):
    root = Path(root) if root else ROOT
    folder = root/'artifacts/releases'
    folder.mkdir(parents=True, exist_ok=True)
    payloads = {'model.json':canonical(model).encode(), 'answers.json':canonical(answers).encode()}
    body = {
        'schema_version':2, 'feature_version':FEATURE_VERSION,
        'feature_source_sha256':feature_digest(root), 'lineage':lineage,
        'status':'experimental_not_promoted',
        'files':{name:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for name,raw in payloads.items()},
    }
    release_id = digest(body)
    manifest = dict(body, release_id=release_id)
    destination = folder/release_id
    if destination.exists():
        verify(release_id, root)
        return release_id
    stage = Path(tempfile.mkdtemp(prefix='.staging-', dir=folder))
    try:
        for name,raw in payloads.items():
            with (stage/name).open('wb') as f:
                f.write(raw);f.flush();os.fsync(f.fileno())
        atomic_json(stage/'manifest.json', manifest)
        # tempfile directories begin at 0700; assessed inference runs as UID 65534.
        os.chmod(stage,0o755)
        for file in stage.iterdir():os.chmod(file,0o644)
        try:
            os.rename(stage, destination)
        except OSError:
            if not destination.exists():
                raise
            verify(release_id, root)
    finally:
        if stage.exists():shutil.rmtree(stage)
    return release_id


def verify(release_id, root=None):
    root = Path(root) if root else ROOT
    if not isinstance(release_id,str) or len(release_id)!=64 or any(c not in '0123456789abcdef' for c in release_id):
        raise ValueError('invalid release ID')
    folder = root/'artifacts/releases'/release_id
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    body = {k:v for k,v in manifest.items() if k!='release_id'}
    if manifest.get('release_id')!=release_id or digest(body)!=release_id:
        raise ValueError('release manifest identity mismatch')
    if manifest.get('schema_version')!=2 or manifest.get('feature_version')!=FEATURE_VERSION:
        raise ValueError('release schema mismatch')
    if manifest.get('feature_source_sha256')!=feature_digest(root):
        raise ValueError('training/inference feature code mismatch')
    if set(manifest['files'])!={'model.json','answers.json'}:
        raise ValueError('release file allowlist mismatch')
    for name,meta in manifest['files'].items():
        path=folder/name
        if path.is_symlink() or not path.is_file() or path.stat().st_size!=meta['bytes'] or sha(path)!=meta['sha256']:
            raise ValueError('release artifact integrity mismatch: '+name)
    return manifest


def select(release_id, mode='conservative', root=None):
    root = Path(root) if root else ROOT
    from .policy import MODES
    if mode not in MODES:
        raise ValueError('unknown deployment mode')
    verify(release_id, root)
    deployment={'schema_version':2,'release_id':release_id,'mode':mode}
    atomic_json(root/'artifacts/deployment.json',deployment)
    return deployment


def selected(root=None):
    root = Path(root) if root else ROOT
    config=json.loads((root/'artifacts/deployment.json').read_text(encoding='utf-8'))
    if set(config)!={'schema_version','release_id','mode'} or config['schema_version']!=2:
        raise ValueError('deployment schema')
    from .policy import MODES
    if config['mode'] not in MODES:
        raise ValueError('deployment mode')
    manifest=verify(config['release_id'],root)
    return config,manifest


def identity(root=None):
    config,manifest=selected(root)
    return {'deployment':config,'manifest_sha256':digest(manifest)}


def load_artifact(name, root=None):
    if name not in ('model.json','answers.json'):
        raise ValueError('unknown inference artifact')
    root = Path(root) if root else ROOT
    config,_=selected(root)
    return json.loads((root/'artifacts/releases'/config['release_id']/name).read_text(encoding='utf-8'))
