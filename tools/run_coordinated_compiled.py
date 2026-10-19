"""Verified CPython 3.12 entrypoint for the frozen coordinated controller."""
import importlib.abc
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_compiled import install as install_foundation,sha
BUNDLE=ROOT/'compiled/cpython312/coordinated_controller'


class Finder(importlib.abc.MetaPathFinder):
    def __init__(self,entries):self.entries=entries
    def find_spec(self,fullname,path=None,target=None):
        if fullname not in ('coordinated','coordinated.engine'):return None
        name='coordinated/__init__.py' if fullname=='coordinated' else 'coordinated/engine.py'
        loader=importlib.machinery.SourcelessFileLoader(fullname,str(BUNDLE/self.entries[name]['bytecode']))
        return importlib.util.spec_from_file_location(fullname,str(ROOT/name),loader=loader,
                  submodule_search_locations=[str(ROOT/'coordinated')] if fullname=='coordinated' else None)


def install():
    install_foundation()
    manifest=json.loads((BUNDLE/'MANIFEST.json').read_text())
    if manifest['magic_hex']!=importlib.util.MAGIC_NUMBER.hex():raise ValueError('CPython bytecode magic mismatch')
    entries={e['source']:e for e in manifest['files']}
    if set(entries)!={'policy.py','coordinated/__init__.py','coordinated/engine.py'}:
        raise ValueError('compiled coordinated inventory mismatch')
    for name,entry in entries.items():
        if entry['bytecode']!=name+'c':raise ValueError('compiled coordinated path mismatch')
        source=(ROOT/name).read_bytes();raw=(BUNDLE/entry['bytecode']).read_bytes()
        if (sha(source)!=entry['source_sha256'] or sha(raw)!=entry['bytecode_sha256']
                or raw[:4]!=importlib.util.MAGIC_NUMBER or int.from_bytes(raw[4:8],'little')!=3
                or raw[8:16]!=importlib.util.source_hash(source)):
            raise ValueError('compiled coordinated source/header/hash mismatch')
    sys.meta_path.insert(0,Finder(entries))
    return entries


def main():
    try:
        entries=install()
        loader=importlib.machinery.SourcelessFileLoader('__main__',str(BUNDLE/entries['policy.py']['bytecode']))
        namespace={'__name__':'__main__','__file__':str(ROOT/'policy.py'),'__package__':None,'__builtins__':__builtins__}
        exec(loader.get_code('__main__'),namespace)
    except (OSError,ValueError,KeyError,TypeError,ImportError) as error:
        print(json.dumps({'status':'failed','error':str(error)[:240]}),file=sys.stderr);return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
