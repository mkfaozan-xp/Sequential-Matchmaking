"""Verify pinned installed distributions and record licence inventory; no CVE/legal claim."""
import base64,hashlib,importlib.metadata,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blackbox.runtime import runtime_info
from blackbox.provenance import execution_identity
from blackbox.storage import atomic_json

def main():
    records=[];ok=True
    pins=[line.strip().split('==') for line in (ROOT/'requirements-train.txt').read_text().splitlines() if '==' in line and not line.startswith('#')]
    for name,version in pins:
        dist=importlib.metadata.distribution(name);checked=0;failures=[];licenses=[]
        for item in dist.files or []:
            path=Path(dist.locate_file(item))
            if item.hash and item.hash.mode=='sha256':
                checked+=1
                if not path.is_file() or base64.urlsafe_b64encode(hashlib.sha256(path.read_bytes()).digest()).decode().rstrip('=')!=item.hash.value:failures.append(str(item))
            if ('license' in str(item).lower() or 'copying' in str(item).lower()) and path.is_file():
                licenses.append({'path':str(item),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        valid=dist.version==version and checked>0 and not failures;ok=ok and valid
        records.append({'name':name,'version':dist.version,'expected_version':version,'record_hashes_checked':checked,
            'valid':valid,'mismatches':failures,'license_expression':dist.metadata.get('License-Expression'),
            'license_summary':(dist.metadata.get('License') or '').splitlines()[:1],'license_files':licenses})
    atomic_json(ROOT/'results/environment.json',{'identity':execution_identity(),'runtime':runtime_info(),'verified':ok,
        'distributions':records,'scope':'installed RECORD integrity and licence inventory; not a vulnerability scan or complete legal audit'})
    print(json.dumps({'verified':ok,'packages':[{k:r[k] for k in ('name','version','record_hashes_checked','valid')} for r in records]}))
    return 0 if ok else 2
if __name__=='__main__':raise SystemExit(main())
