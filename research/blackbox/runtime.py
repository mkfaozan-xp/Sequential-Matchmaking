"""Explicit runtime capability status instead of rejecting newer interpreters."""
import platform,sys,importlib.metadata

def runtime_info(version=None):
    version=tuple(version or sys.version_info[:3])
    if version[:2]<(3,12):raise ValueError('Python 3.12 or newer required')
    return {'python':'.'.join(map(str,version)),'implementation':platform.python_implementation(),
        'platform':platform.system(),'machine':platform.machine(),
        'reference_runtime':version[:2]==(3,12),
        'status':'reference family; inspect actual tests' if version[:2]==(3,12) else 'compatibility run; not reference certification'}

def installed_dependencies():
    out={}
    for name in ('numpy','scipy'):
        try:out[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:out[name]=None
    return out
