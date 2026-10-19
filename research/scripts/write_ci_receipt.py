"""Hash a real CI validation job's evidence; signing happens only in GitHub Actions."""
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blackbox.provenance import execution_identity
from blackbox.registry import sha
from blackbox.storage import atomic_json
from scripts.release_gate import assess,container_valid

def main():
    names=('tests.json','validation.json','container_attestation.json','container_candidate.json','data_check.json','environment.json','selection.json')
    records={name:json.loads((ROOT/'results'/name).read_text()) for name in names}
    if records['environment.json'].get('identity')!=execution_identity() or records['environment.json'].get('verified') is not True:raise ValueError('current verified dependency inventory required')
    mode=records['container_attestation.json']['mode']
    gate=assess(records['tests.json'],records['validation.json'],records['container_attestation.json'],mode,
        data_check=records['data_check.json'])
    if gate['status']!='validation_checks_passed':raise ValueError('No signed-ready receipt without actual complete validation and Docker evidence')
    candidate=records['selection.json']['selected_mode']
    if records['selection.json']['identity']!=execution_identity() or not container_valid(records['container_candidate.json'],candidate):
        raise ValueError('actual exact selected-candidate container required')
    atomic_json(ROOT/'results/ci-receipt.json',{'schema_version':1,'identity':execution_identity(mode=mode),
        'checks':dict(gate['checks'],exact_selected_candidate_container=True),'selected_candidate':candidate,'evidence_sha256':{n:sha(ROOT/'results'/n) for n in names},
        'workflow':{k:os.environ.get(k) for k in ('GITHUB_REPOSITORY','GITHUB_SHA','GITHUB_RUN_ID')},
        'proof_type':'unsigned receipt until an external GitHub attestation is generated and verified',
        'claim':'validation evidence only; neither promotion nor Windows certification'})
if __name__=='__main__':main()
