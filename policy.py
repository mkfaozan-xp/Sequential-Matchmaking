"""Two public policy choices; original hard validation and two-phase JSON contract."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'runtime'))
sys.path.insert(0,str(ROOT))
from blackbox.contracts import LIMIT


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['conservative','coordinated'],default='conservative')
    a=p.parse_args();started=time.monotonic()
    try:
        raw=sys.stdin.buffer.read(LIMIT+1)
        if len(raw)>LIMIT:raise ValueError('request exceeds 1 MiB')
        def reject(v):raise ValueError('non-finite JSON '+v)
        request=json.loads(raw,parse_constant=reject)
        if a.mode=='coordinated':
            from coordinated.engine import decide
        else:from blackbox.policy import decide
        response=decide(request)
        output=json.dumps(response,allow_nan=False,separators=(',',':'))
        if len(output.encode())>LIMIT:raise ValueError('response exceeds 1 MiB')
        print(output)
        print(json.dumps({'elapsed_seconds':time.monotonic()-started,'mode':a.mode,
                          'diagnostics':response['memory'].get('diagnostics',{})}),file=sys.stderr)
        return 0
    except (OSError,ValueError,KeyError,TypeError,RecursionError) as error:
        print(json.dumps({'status':'failed','error':str(error)[:240]}),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
