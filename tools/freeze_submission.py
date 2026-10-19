"""Export the verified frozen inventory and an external SHA-256 sidecar."""
import argparse
import json
from pathlib import Path
import sys
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

sys.dont_write_bytecode=True
from verify_submission import ROOT, verify, sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();target=a.output.resolve()
    if target==ROOT or ROOT in target.parents:p.error('archive must be outside the frozen folder')
    if target.suffix.lower()!='.zip':p.error('output must end in .zip')
    sidecar=target.with_suffix(target.suffix+'.sha256')
    if target.exists() or sidecar.exists():p.error('choose a new output name; frozen exports are not overwritten')
    verified=verify()
    manifest=json.loads((ROOT/'SUBMISSION_MANIFEST.json').read_text())
    target.parent.mkdir(parents=True,exist_ok=True)
    names=sorted([*manifest['files'],'SUBMISSION_MANIFEST.json'])
    with ZipFile(target,'w',ZIP_DEFLATED,compresslevel=9) as z:
        for name in names:
            info=ZipInfo('Blackbox_Round2_Submission/'+name,date_time=(1980,1,1,0,0,0))
            info.compress_type=ZIP_DEFLATED;info.create_system=3
            info.external_attr=0o100644<<16
            z.writestr(info,(ROOT/name).read_bytes(),compress_type=ZIP_DEFLATED,compresslevel=9)
    with ZipFile(target) as z:
        if z.testzip() is not None:raise ValueError('ZIP CRC check failed')
    digest=sha(target.read_bytes())
    sidecar.write_text(digest+'  '+target.name+'\n',encoding='ascii')
    print(json.dumps({'archive':str(target),'archive_sha256':digest,'bytes':target.stat().st_size,
                      'files':len(names),'manifest_sha256':verified['manifest_sha256'],
                      'runtime_checks_closed':False},sort_keys=True))
    return 0


if __name__=='__main__':raise SystemExit(main())
