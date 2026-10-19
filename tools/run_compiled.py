"""Run the verified CPython 3.12 runtime bytecode with original assets and sources."""
import hashlib
import importlib.abc
import importlib.machinery
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys

ROOT=Path(__file__).resolve().parents[1]
BUNDLE=ROOT/'compiled/cpython312'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def verified_runtime_entries():
    manifest=json.loads((BUNDLE/'COMPILED_MANIFEST.json').read_text(encoding='utf-8'))
    if (sys.implementation.name!='cpython' or sys.version_info[:2]!=(3,12)
            or manifest['magic_hex']!=importlib.util.MAGIC_NUMBER.hex()):
        raise ValueError('This bytecode needs CPython 3.12. On Windows use py -3.12.')
    entries={}
    for entry in manifest['files']:
        if not entry['source'].startswith('runtime/'):continue
        for field in ('source','bytecode'):
            name=entry[field];path=PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or '\\' in name or path.as_posix()!=name:
                raise ValueError('Unsafe compiled manifest path.')
        source=ROOT/entry['source'];bytecode=BUNDLE/entry['bytecode']
        if source.is_symlink() or bytecode.is_symlink():raise ValueError('Unexpected symbolic link.')
        original=source.read_bytes();raw=bytecode.read_bytes()
        if sha(original)!=entry['source_sha256'] or sha(raw)!=entry['bytecode_sha256']:
            raise ValueError('Compiled/source checksum mismatch: '+entry['source'])
        if raw[:4]!=importlib.util.MAGIC_NUMBER or int.from_bytes(raw[4:8],'little')!=3:
            raise ValueError('Invalid compiled header.')
        if raw[8:16]!=importlib.util.source_hash(original):raise ValueError('Compiled source header mismatch.')
        entries[entry['source']]=entry
    actual={p.relative_to(ROOT).as_posix() for p in (ROOT/'runtime').rglob('*.py')}
    if set(entries)!=actual:raise ValueError('Incomplete compiled runtime inventory.')
    return entries


class CompiledRuntimeFinder(importlib.abc.MetaPathFinder):
    def __init__(self,entries):self.entries=entries;self.loaded=[]
    def find_spec(self,fullname,path=None,target=None):
        if fullname!='blackbox' and not fullname.startswith('blackbox.'):return None
        base='runtime/'+fullname.replace('.','/')
        source=base+'/__init__.py' if base+'/__init__.py' in self.entries else base+'.py'
        if source not in self.entries:raise ImportError('Module is outside the compiled runtime: '+fullname)
        loader=importlib.machinery.SourcelessFileLoader(fullname,str(BUNDLE/self.entries[source]['bytecode']))
        # Registry/model verification reads source files beside __file__. Preserve
        # those exact paths; only executed code comes from the checked bytecode.
        locations=[str((ROOT/source).parent)] if source.endswith('/__init__.py') else None
        spec=importlib.util.spec_from_file_location(fullname,str(ROOT/source),loader=loader,
                                                 submodule_search_locations=locations)
        self.loaded.append(fullname)
        return spec


def install():
    if any(name=='blackbox' or name.startswith('blackbox.') for name in sys.modules):
        raise ValueError('Start the compiled runtime in a fresh Python process.')
    entries=verified_runtime_entries();finder=CompiledRuntimeFinder(entries)
    sys.meta_path.insert(0,finder)
    return entries,finder


def main():
    try:
        entries,_=install()
        entry=entries['runtime/policy.py']
        loader=importlib.machinery.SourcelessFileLoader('__main__',str(BUNDLE/entry['bytecode']))
        code=loader.get_code('__main__')
        namespace={'__name__':'__main__','__file__':str(ROOT/'runtime/policy.py'),
                   '__package__':None,'__builtins__':__builtins__}
        exec(code,namespace)
    except (OSError,ValueError,ImportError,KeyError,TypeError) as error:
        print(json.dumps({'status':'failed','message':str(error)[:240]}),file=sys.stderr);return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
