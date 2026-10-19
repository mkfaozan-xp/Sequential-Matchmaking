"""Official restart-per-call JSON entrypoint. Diagnostics only on stderr."""
import argparse,json,sys,time,os
from blackbox.policy import decide,MODES
from blackbox.contracts import LIMIT

def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=MODES,default=None)
    p.add_argument('--baseline',choices=['greedy','no_asks','random'],default=None)
    a=p.parse_args();started=time.perf_counter()
    try:
        raw=sys.stdin.buffer.read(LIMIT+1)
        if len(raw)>LIMIT:raise ValueError('request exceeds 1 MiB')
        def reject(v):raise ValueError('non-finite JSON: '+v)
        request=json.loads(raw,parse_constant=reject)
        from blackbox.registry import selected
        mode=a.mode or os.environ.get('BLACKBOX_POLICY_MODE') or selected()[0]['mode']
        if mode not in MODES:raise ValueError('unknown configured policy mode')
        response=decide(request,mode)
        output=json.dumps(response,allow_nan=False,separators=(',',':'))
        if len(output.encode())>LIMIT:raise ValueError('response exceeds 1 MiB')
        print(output)
        print(json.dumps({'elapsed_ms':round((time.perf_counter()-started)*1000,3),
            'phase':request['phase'],'day':request['state']['day'],'mode':mode,'release_id':response['memory']['release_id'],'diagnostics':response['memory']['diagnostics']}),file=sys.stderr)
        return 0
    except (ValueError,TypeError,KeyError,OSError,RecursionError) as error:
        print(json.dumps({'status':'failed','error_type':type(error).__name__,'message':str(error)[:240]}),file=sys.stderr)
        return 2
if __name__=='__main__':raise SystemExit(main())
