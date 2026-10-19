"""Build deterministic CPython bytecode without modifying measured sources or weights."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import py_compile
import sys

ROOT=Path(__file__).resolve().parents[1]


def sha(raw):return hashlib.sha256(raw).hexdigest()


def compile_bundle(output):
    if sys.implementation.name!='cpython' or sys.version_info[:2]!=(3,12):
        raise ValueError('Build this bytecode target using CPython 3.12 (reference 3.12.14).')
    output=output.resolve()
    if output==ROOT or ROOT in output.parents:
        raise ValueError('Rebuild output must be outside the frozen submission directory.')
    if output.exists():raise ValueError('Choose a new output directory; existing builds are not overwritten.')
    sources=sorted([*(ROOT/'runtime').rglob('*.py'),*(ROOT/'research').rglob('*.py')])
    entries=[]
    for source in sources:
        name=source.relative_to(ROOT).as_posix()
        compiled=name+'c'
        target=output/compiled;target.parent.mkdir(parents=True,exist_ok=True)
        py_compile.compile(str(source),cfile=str(target),dfile=name,doraise=True,optimize=0,
                           invalidation_mode=py_compile.PycInvalidationMode.CHECKED_HASH)
        raw=target.read_bytes()
        if raw[:4]!=importlib.util.MAGIC_NUMBER or int.from_bytes(raw[4:8],'little')!=3:
            raise ValueError('Unexpected checked-hash bytecode header: '+name)
        if raw[8:16]!=importlib.util.source_hash(source.read_bytes()):
            raise ValueError('Bytecode source-header mismatch: '+name)
        entries.append({'source':name,'source_sha256':sha(source.read_bytes()),
                        'bytecode':compiled,'bytecode_sha256':sha(raw),'bytes':len(raw)})
    result={'schema_version':1,'target':'CPython 3.12 bytecode','compiler_python':platform.python_version(),
            'implementation':sys.implementation.name,'cache_tag':sys.implementation.cache_tag,
            'magic_hex':importlib.util.MAGIC_NUMBER.hex(),'optimization':0,'invalidation':'checked_hash',
            'virtual_filenames':True,'compiled_files':len(entries),'files':entries,
            'weights_retrained':False,'native_executable':False,
            'research_bytecode_scope':'Compilation/syntax artifacts only; research reproduction uses the retained original sources.',
            'runtime_bytecode_scope':'tools/run_compiled.py loads verified runtime bytecode while preserving original source paths for asset integrity checks.'}
    (output/'COMPILED_MANIFEST.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    try:
        result=compile_bundle(a.output)
        print(json.dumps({'passed':True,'target':result['target'],'compiled_files':result['compiled_files']}));return 0
    except (OSError,ValueError,py_compile.PyCompileError) as error:
        print(str(error),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
