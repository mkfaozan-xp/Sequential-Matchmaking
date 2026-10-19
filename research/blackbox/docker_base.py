"""Resolve a locally verified registry digest before building an assessed image."""
import json,subprocess

def base_reference(recipe):
    lines=recipe.read_text().splitlines()
    return next((line.split('=',1)[1].strip() for line in lines if line.startswith('ARG PYTHON_BASE=')),
        next(line.split()[1] for line in lines if line.startswith('FROM ')))

def resolve(reference):
    try:
        meta=json.loads(subprocess.check_output(['docker','image','inspect',reference],text=True,stderr=subprocess.DEVNULL,timeout=15))[0]
    except subprocess.CalledProcessError:meta={}
    pulled=False
    if not meta.get('RepoDigests'):
        subprocess.run(['docker','pull',reference],check=True,timeout=540);pulled=True
        meta=json.loads(subprocess.check_output(['docker','image','inspect',reference],text=True,timeout=15))[0]
    candidates=sorted(d for d in meta.get('RepoDigests',[]) if '@sha256:' in d and len(d.rsplit('@sha256:',1)[1])==64)
    if not candidates or not meta.get('Id','').startswith('sha256:'):raise ValueError('base image lacks a verified immutable registry digest')
    digest=candidates[0]
    bound=json.loads(subprocess.check_output(['docker','image','inspect',digest],text=True,timeout=15))[0]
    if bound['Id']!=meta['Id']:raise ValueError('base tag/digest image identity mismatch')
    return {'reference':reference,'registry_digest':digest,'image_id':meta['Id'],'pulled':pulled}
