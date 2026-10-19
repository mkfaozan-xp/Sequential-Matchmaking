"""Bounded memoization of public hard checks, scoped to trusted host episodes."""
from contextvars import ContextVar
from contextlib import contextmanager
import hashlib,json
from .domain import HARD,eligibility

_CACHE=ContextVar('observed_hard_compatibility',default=None)

@contextmanager
def episode_cache(limit=20000):
    if _CACHE.get() is not None:raise ValueError('nested eligibility cache')
    if not 1<=limit<=20000:raise ValueError('bounded eligibility cache required')
    token=_CACHE.set(({},limit))
    try:yield
    finally:_CACHE.reset(token)

def prepared(members):
    active=_CACHE.get()
    if active is None:return eligibility
    cache,limit=active;keys={}
    for m in members:
        observed={k:m[k] for k in ('member_id','pool_id','age','gender','zone')}
        observed['fields']={k:m['fields'].get(k) for k in HARD}
        keys[id(m)]=hashlib.sha256(json.dumps(observed,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).digest()
    def check(a,b):
        key=(keys[id(a)],keys[id(b)])
        result=cache.get(key)
        if result is None:
            result=eligibility(a,b)
            if len(cache)>=limit:cache.clear()
            cache[key]=result
        return {k:v[:] if isinstance(v,list) else v for k,v in result.items()}
    return check
