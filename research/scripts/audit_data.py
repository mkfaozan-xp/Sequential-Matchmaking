"""Verify actual public bytes with the supplied checker and bind the result to this run."""
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blackbox.provenance import execution_identity
from blackbox.registry import sha
from blackbox.storage import atomic_json


def main():
    proc=subprocess.run([sys.executable,str(ROOT/'starter/verify_data.py')],cwd=ROOT,text=True,capture_output=True)
    result={'schema_version':2,'identity':execution_identity(),'verified':False,
            'checksum_manifest_sha256':sha(ROOT/'starter/data_checksums.json')}
    if proc.returncode:
        result['error']=proc.stderr[-2000:]
    else:
        actual=json.loads(proc.stdout);result.update(actual)
    atomic_json(ROOT/'results/data_check.json',result)
    print(json.dumps(result,indent=2));return 0 if result['verified'] else 2

if __name__=='__main__':raise SystemExit(main())
