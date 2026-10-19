"""Verify the frozen distribution, declared mode and recorded comparison coverage."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]


def sha(raw):return hashlib.sha256(raw).hexdigest()


def verify(root=ROOT):
    raw=(root/'SUBMISSION_MANIFEST.json').read_bytes()
    manifest=json.loads(raw)
    if manifest.get('schema_version')!=1 or manifest.get('submitted_mode')!='conservative':
        raise ValueError('unexpected submission declaration')
    inventory=manifest['files']
    for name,digest in inventory.items():
        p=PurePosixPath(name)
        if (p.is_absolute() or '..' in p.parts or '\\' in name or p.as_posix()!=name
                or name=='SUBMISSION_MANIFEST.json' or len(digest)!=64
                or any(c not in '0123456789abcdef' for c in digest)):
            raise ValueError('invalid submission manifest path/hash')
    files=set()
    for p in root.rglob('*'):
        if p.is_symlink():raise ValueError('unexpected symbolic link')
        if p.is_file() and '__pycache__' not in p.relative_to(root).parts:
            files.add(p.relative_to(root).as_posix())
    if files!=set(inventory)|{'SUBMISSION_MANIFEST.json'}:
        raise ValueError('submission inventory changed; keep validation output outside this folder')
    if len({p.casefold() for p in files})!=len(files):raise ValueError('Windows path collision')
    for name,digest in inventory.items():
        if sha((root/name).read_bytes())!=digest:raise ValueError('checksum mismatch: '+name)
    for directory in ('runtime','research'):
        config=json.loads((root/directory/'artifacts/deployment.json').read_text())
        if config['mode']!='conservative' or config['release_id']!=manifest['release_id']:
            raise ValueError('deployment mode/assets mismatch')
    validation=json.loads((root/'research/results/validation.json').read_text())
    expected={(s,v,m) for s in validation['seeds'] for v in validation['variants']
              for m in ('baseline_greedy','baseline_no_asks','baseline_random','conservative','rank_aux')}
    actual={(r['seed'],r['variant'],r['method']) for r in validation['episodes']}
    if not validation['complete'] or not validation['all_valid'] or expected!=actual:
        raise ValueError('baseline/method comparison incomplete')
    for row in validation['episodes']:
        if (not row['valid'] or len(row['first_introduction_wait_days'])!=row['served_members']
                or row['served_members']+row['unserved_members']!=row['arrived_members']):
            raise ValueError('invalid service/waiting-time record')
    ablation=json.loads((root/'results/asking_ablation.json').read_text())
    if not ablation['complete'] or not ablation['all_valid'] or len(ablation['episodes'])!=24:
        raise ValueError('asking ablation incomplete')
    sys.path.insert(0,str(root/'research'))
    from blackbox.provenance import source_hash
    if source_hash(root/'research')!=manifest['research_source_sha256']:
        raise ValueError('measured research source identity changed')
    return {'passed':True,'files_verified':len(files),'submitted_mode':'conservative',
            'release_id':manifest['release_id'],'manifest_sha256':sha(raw),
            'runtime_checks_closed':False,
            'note':'Frozen contents verified; actual Windows/container evidence is separate and not implied.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path)
    p.add_argument('--sha256',help='expected exact archive SHA-256, required with --archive')
    a=p.parse_args()
    try:
        if bool(a.archive)!=bool(a.sha256):raise ValueError('supply --archive and --sha256 together')
        result=verify()
        if a.archive:
            if sha(a.archive.read_bytes())!=a.sha256:raise ValueError('archive SHA-256 mismatch')
            result['archive_sha256']=a.sha256
        print(json.dumps(result,sort_keys=True));return 0
    except (OSError,ValueError,KeyError,TypeError) as error:
        print(json.dumps({'passed':False,'error':str(error)[:240]}),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
