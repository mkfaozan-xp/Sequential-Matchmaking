"""Verify flat historical inputs or refit unchanged models in a separate copy."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'research'))
from blackbox.storage import digest
from blackbox.features import FEATURE_VERSION,NAMES
from blackbox.registry import feature_digest


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def dataset(root=ROOT):
    research=root/'research';folder=research/'artifacts/datasets/collector_source'
    manifest=json.loads((folder/'MANIFEST.json').read_text())
    original='d8c14e493f46c63613f0769050f432c524cf4cc4a710a3172d123faa44cf585a'
    if manifest['original_archive_sha256']!=original:raise ValueError('collector lineage')
    actual={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p.name!='MANIFEST.json'}
    if actual!=set(manifest['members']):raise ValueError('collector membership')
    for name,expected in manifest['members'].items():
        p=(folder/name).resolve()
        if folder.resolve() not in p.parents or sha(p)!=expected:raise ValueError('collector source integrity')
    pointer=json.loads((folder/'artifacts/deployment.json').read_text());release=pointer['release_id']
    base=folder/'artifacts/releases'/release
    model=json.loads((base/'model.json').read_text());answers=json.loads((base/'answers.json').read_text())
    previous=json.loads((folder/'results/training.json').read_text())
    if model['feature_version']!=FEATURE_VERSION or model['feature_source_sha256']!=feature_digest():raise ValueError('raw feature implementation changed')
    for name in ('blackbox/labels.py','starter/kit.py'):
        if (folder/name).read_bytes()!=(research/name).read_bytes():raise ValueError('outcome definition changed')
    bundle=research/'artifacts/datasets/v06_observations.json.gz'
    with gzip.open(bundle,'rb') as f:raw=f.read(256*1024**2+1)
    if len(raw)>256*1024**2:raise ValueError('observation bound')
    saved=json.loads(raw)
    if saved['original_archive_sha256']!=original:raise ValueError('observation lineage')
    rows=[];files=[]
    if set(saved['records'])!=set(model['config']['cache_ids']):raise ValueError('observation membership')
    for key in model['config']['cache_ids']:
        item=saved['records'][key];record=item['record']
        if digest(record['identity'])!=key or digest(record['payload'])!=record['payload_sha256']:raise ValueError('observation integrity')
        for name,expected in record['identity']['source'].items():
            if manifest['members'].get(name)!=expected:raise ValueError('collector source mismatch')
        rows.extend(record['payload']['joint'])
        files.append({'cache_id':key,'sha256':item['original_cache_sha256'],'payload_sha256':record['payload_sha256']})
    if len(files)!=288 or digest(rows)!=model['config']['data_hash']:raise ValueError('dataset content mismatch')
    if len({r['row_id'] for r in rows})!=len(rows):raise ValueError('duplicate observation')
    if any(len(r['x'])!=len(NAMES) or r.get('label') not in (0,1) or r.get('auxiliary_label') not in (0,1) for r in rows):raise ValueError('dataset schema')
    lineage={'observation_bundle_sha256':sha(bundle),'archive_sha256':original,'original_release':release,'raw_feature_schema':FEATURE_VERSION,
             'raw_rows':len(rows),'row_sha256':digest(rows),'collection_episodes':288,'new_collection_episodes':0,'cache_files':files}
    recorded=json.loads((root/'coordinated/model.json').read_text())['lineage']
    if lineage!=recorded:raise ValueError('current-model dataset lineage mismatch')
    return rows,model,answers,previous,lineage


def main():
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--verify-data',action='store_true')
    mode.add_argument('--output',type=Path,help='New external working copy; recorded evidence is never overwritten.')
    p.add_argument('--funnel',action='store_true',help='Refit the staged scorer in the new external copy.')
    a=p.parse_args();rows,*_=dataset()
    if a.verify_data:
        print(json.dumps({'passed':True,'rows':len(rows),'official_positives':sum(r['label'] for r in rows),'auxiliary_positives':sum(r['auxiliary_label'] for r in rows),'nested_archives_required':False}));return 0
    target=a.output.resolve()
    if target.exists() or target==ROOT or ROOT in target.parents:p.error('choose a new directory outside this frozen project')
    shutil.copytree(ROOT,target,ignore=shutil.ignore_patterns('__pycache__'))
    import scripts.train_rankers as legacy
    legacy.dataset=lambda:dataset(target)
    runpy.run_path(str(target/('funnel/train.py' if a.funnel else 'coordinated/train.py')),run_name='__main__')
    return 0


if __name__=='__main__':raise SystemExit(main())
