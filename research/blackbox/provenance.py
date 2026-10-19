"""Full executable/configuration identity plus the exact inference release."""
from pathlib import Path
from .storage import digest
from .registry import sha, identity
ROOT=Path(__file__).resolve().parent.parent


def source_files(root=None):
    root=Path(root) if root else ROOT
    files=list(root.glob('*.py'))
    for directory in ('blackbox','scripts','starter','official_data_training'):
        files += [p for p in (root/directory).rglob('*.py') if '__pycache__' not in p.parts]
    files += list(root.glob('*.ps1'))+list(root.glob('requirements*.txt'))+list(root.glob('Dockerfile*'))
    files += list((root/'.github/workflows').glob('*.yml'))
    files += list(root.glob('.dockerignore'))
    files += list(root.glob('.gitattributes'))
    files += [root/'starter/data_manifest.json',root/'starter/data_checksums.json']
    if (root/'plans/REVIEW_PROTOCOL.md').exists():files.append(root/'plans/REVIEW_PROTOCOL.md')
    return sorted(set(files))


def source_hash(root=None):
    root=Path(root) if root else ROOT
    return digest({p.relative_to(root).as_posix():sha(p) for p in source_files(root)})


def execution_identity(mode=None, root=None):
    root=Path(root) if root else ROOT
    result={'source_sha256':source_hash(root),'inference_release':identity(root)}
    if mode is not None:result['mode']=mode
    return result
