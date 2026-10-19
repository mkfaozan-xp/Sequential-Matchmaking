"""Create a checked, versioned source/evidence archive without caches or host environments."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blackbox.provenance import execution_identity
from blackbox.storage import atomic_json


def main():
    output=ROOT.parent/'deliverables'
    output.mkdir(exist_ok=True)
    identity=execution_identity()
    summary=json.loads((ROOT/'results/verification_summary.json').read_text())
    if summary.get('identity')!=identity or not summary.get('tests_success') or not summary.get('all_evaluated_valid'):
        raise ValueError('current tests and complete valid policy evidence are required before packaging')
    files=[]
    excluded={'__pycache__','training_cache','.venv','public_snapshot','.git'}
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file():continue
        rel=path.relative_to(ROOT)
        if excluded.intersection(rel.parts) or path.suffix in ('.pyc','.sqlite','.log','.tmp','.lock') or '.sqlite-' in path.name:
            continue
        if path.name=='PACKAGE_SHA256.json':continue
        if rel.parts[0]=='results' and path.suffix not in ('.json','.md'):continue
        if rel.parts[0]=='artifacts' and any(p.startswith('.staging-') for p in rel.parts):continue
        files.append((path,rel.as_posix()))
    manifest={'schema_version':2,'identity':identity,'files':{
        name:hashlib.sha256(path.read_bytes()).hexdigest() for path,name in files}}
    atomic_json(ROOT/'PACKAGE_SHA256.json',manifest)
    files.append((ROOT/'PACKAGE_SHA256.json','PACKAGE_SHA256.json'))
    target=output/'Blackbox_ML_Prototype_v0_3_0.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path,name in files:archive.write(path,'Blackbox_ML_Prototype/'+name)
    with zipfile.ZipFile(target) as archive:
        if archive.testzip():raise ValueError('archive CRC failure')
        if len(archive.namelist())!=len(set(archive.namelist())):raise ValueError('duplicate archive members')
        for name,expected in manifest['files'].items():
            if hashlib.sha256(archive.read('Blackbox_ML_Prototype/'+name)).hexdigest()!=expected:raise ValueError('archive hash mismatch: '+name)
    for source,name in [('WINDOWS_START.md','Blackbox_v0_3_Windows_Start.md'),('results/REPORT.md','Blackbox_v0_3_Report.md')]:
        shutil.copy2(ROOT/source,output/name)
    print(json.dumps({'archive':str(target),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'files':len(files)}))

if __name__=='__main__':main()
