"""Fit ranking heads on the verified v0.6 observation dataset; no recollection claim."""
import copy,json,sys,time,zipfile,platform,importlib.metadata,gzip,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blackbox.ranking import RANK_NAMES,contrasts,rank_names,heuristic_score
from blackbox.features import FEATURE_VERSION,NAMES
from blackbox.fitting import select_fit
from blackbox.registry import load_artifact,publish,select,sha,feature_digest
from blackbox.provenance import source_hash
from blackbox.storage import atomic_json,digest,WorkflowLock


def dataset():
    archive=ROOT/'evidence/Blackbox_ML_Prototype_v0_6_0_original.zip'
    if sha(archive)!='d8c14e493f46c63613f0769050f432c524cf4cc4a710a3172d123faa44cf585a':raise ValueError('original v0.6 archive identity')
    with zipfile.ZipFile(archive) as z:
        prefix='Blackbox_ML_Prototype/';pointer=json.loads(z.read(prefix+'artifacts/deployment.json'))
        release=pointer['release_id'];base=prefix+'artifacts/releases/'+release+'/'
        model=json.loads(z.read(base+'model.json'));answers=json.loads(z.read(base+'answers.json'))
        previous=json.loads(z.read(prefix+'results/training.json'))
        if model['feature_version']!=FEATURE_VERSION or model['feature_source_sha256']!=feature_digest():raise ValueError('raw feature implementation changed; recollect rather than pad')
        for name in ('blackbox/labels.py','starter/kit.py'):
            if z.read(prefix+name)!=(ROOT/name).read_bytes():raise ValueError('outcome definition changed')
        bundle=ROOT/'artifacts/datasets/v06_observations.json.gz'
        saved=None
        if bundle.exists():
            with gzip.open(bundle,'rb') as f:
                raw=f.read(256*1024**2+1)
            if len(raw)>256*1024**2:raise ValueError('dataset snapshot exceeds bound')
            saved=json.loads(raw)
            if saved['original_archive_sha256']!=sha(archive):raise ValueError('dataset archive lineage')
        rows=[];files=[];records=[]
        for key in model['config']['cache_ids']:
            if saved is not None:
                item=saved['records'].get(key)
                if item is None:raise ValueError('dataset snapshot membership')
                record=item['record'];file_sha=item['original_cache_sha256']
            else:
                p=ROOT/'artifacts/training_cache'/(key+'.json');record=json.loads(p.read_text());file_sha=sha(p)
            records.append((key,{'record':record,'original_cache_sha256':file_sha}))
            if digest(record['identity'])!=key or digest(record['payload'])!=record['payload_sha256']:raise ValueError('dataset payload integrity')
            for name,h in record['identity']['source'].items():
                import hashlib
                if hashlib.sha256(z.read(prefix+name)).hexdigest()!=h:raise ValueError('original collector source mismatch')
            payload=record['payload'];rows.extend(payload['joint']);files.append({'cache_id':key,'sha256':file_sha,'payload_sha256':record['payload_sha256']})
        if len(files)!=288 or digest(rows)!=model['config']['data_hash']:raise ValueError('original dataset membership/content mismatch')
        if len({r['row_id'] for r in rows})!=len(rows):raise ValueError('duplicate observed row')
        if any(len(r['x'])!=len(NAMES) or r.get('label') not in (0,1) or r.get('auxiliary_label') not in (0,1) for r in rows):raise ValueError('incompatible mature dataset')
        if saved is None:
            bundle.parent.mkdir(exist_ok=True);temporary=bundle.with_suffix('.gz.tmp')
            with gzip.GzipFile(filename=str(temporary),mode='wb',compresslevel=6,mtime=0) as f:
                f.write(json.dumps({'original_archive_sha256':sha(archive),'records':dict(records)},sort_keys=True,separators=(',',':')).encode())
            os.replace(temporary,bundle)
        return rows,model,answers,previous,{'observation_bundle_sha256':sha(bundle),'archive_sha256':sha(archive),'original_release':release,'raw_feature_schema':FEATURE_VERSION,
            'raw_rows':len(rows),'row_sha256':digest(rows),'collection_episodes':288,'new_collection_episodes':0,'cache_files':files}


def main():
    start=time.perf_counter()
    with WorkflowLock(ROOT/'artifacts/training_workflow.lock'):
        rows,old,answers,previous,data=dataset();heads={};selection={};counts={}
        for name,target,projection in [('rank_official','label','full'),('rank_auxiliary','auxiliary_label','full'),('rank_reference','auxiliary_label','reference'),('rank_nohistory','auxiliary_label','reference_nohistory')]:
            pairs=contrasts(rows,target,projection=projection,same_score=True);heads[name],selection[name]=select_fit(pairs,rank_names(projection),[('identity',0,10),('identity',2,10),('identity',0,100)])
            heads[name]['ranking_projection']=projection
            heads[name].update(score_semantics='bounded ordinal utility; not a calibrated pair probability',target=target,
                contrast_count=len(pairs),observed_positive_rows=len({p['positive_row_id'] for p in pairs}),window_days=7,negatives_per_positive_cap=5,same_actual_seven_field_score=True)
            counts[name]={'contrast_rows':len(pairs),'unique_observed_positive_rows':heads[name]['observed_positive_rows'],
                'contrast_sha256':digest(pairs)}
        legacy_archive=ROOT/'evidence/Blackbox_ML_Prototype_v0_7_0_original.zip'
        if sha(legacy_archive)!='4c152ced222c8d066c26b6e6a10e707651737cdae82d5a86999f311cc8407685':raise ValueError('original v0.7 archive identity')
        with zipfile.ZipFile(legacy_archive) as z:
            pointer=json.loads(z.read('Blackbox_ML_Prototype/artifacts/deployment.json'))
            prior=json.loads(z.read('Blackbox_ML_Prototype/artifacts/releases/'+pointer['release_id']+'/model.json'))
        heads['rank_legacy_aux']=copy.deepcopy(prior['rank_auxiliary']);heads['rank_legacy_aux']['ranking_projection']='full'
        legacy_pairs=contrasts(rows,'auxiliary_label',same_score=False)
        by_id={r['row_id']:r for r in rows};forward=[p for p in legacy_pairs if p['label']==1]
        counts['historical_unmatched_control']={'archive_sha256':sha(legacy_archive),'inherited_release':pointer['release_id'],
            'contrast_rows':len(legacy_pairs),'cross_score_contrasts':sum(heuristic_score(by_id[p['positive_row_id']]['x'])!=heuristic_score(by_id[p['negative_row_id']]['x']) for p in forward),
            'forward_contrasts':len(forward),'warning':'Frozen historical auxiliary head, excluded from eligible candidates.'}
        config={'protocol_sha256':sha(ROOT/'plans/REVIEW_PROTOCOL.md'),'dataset':data,'ranking':counts,
            'seeds':list(range(1101,1149)),'variants':previous['config']['variants'],
            'target_semantics':'Recorded introduced-pair relative outcomes; no unchosen labels, no propensity correction.',
            'inherited_release':data['original_release'],'new_collection_episodes':0}
        lineage={'source_sha256':source_hash(),'training':config,'python':platform.python_version(),
            'packages':{k:importlib.metadata.version(k) for k in ('numpy','scipy')}}
        model=copy.deepcopy(old);model.update(heads);model.update(model_id='ranking-v08-'+digest({'config':config,'source':source_hash()})[:16],
            ranking_source_sha256=sha(ROOT/'blackbox/ranking.py'),config=config,status='experimental_not_promoted')
        rid=publish(model,answers,lineage);select(rid,'conservative')
        atomic_json(ROOT/'artifacts/candidate.json',{'release_id':rid,'model_id':model['model_id'],'promoted':False})
        atomic_json(ROOT/'results/training.json',{'identity':lineage,'release_id':rid,'dataset':data,'ranking':counts,'new_collection_episodes':0,
            'historical_collection_episodes':288,'joint_rows':len(rows),'joint_positives':sum(r['label'] for r in rows),
            'auxiliary_positives':sum(r['auxiliary_label'] for r in rows),'inherited_probabilistic_heads':data['original_release'],
            'wall_seconds':time.perf_counter()-start,'candidate_promoted':False})
        atomic_json(ROOT/'results/model_selection.json',{'release_id':rid,'config':config,**selection})
        print(json.dumps({'release_id':rid,'ranking':counts,'wall_seconds':time.perf_counter()-start}),flush=True)

if __name__=='__main__':main()
