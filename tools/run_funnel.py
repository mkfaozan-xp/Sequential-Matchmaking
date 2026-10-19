"""Source-only experimental staged scorer; official JSON protocol unchanged."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'runtime'));sys.path.insert(0,str(ROOT))
from blackbox.contracts import LIMIT
from funnel.controller import FunnelController

def main():
 try:
  raw=sys.stdin.buffer.read(LIMIT+1)
  if len(raw)>LIMIT:raise ValueError('request exceeds 1 MiB')
  def reject(value):raise ValueError('nonfinite JSON')
  response=FunnelController().decide(json.loads(raw,parse_constant=reject));out=json.dumps(response,allow_nan=False,separators=(',',':'))
  if len(out.encode())>LIMIT:raise ValueError('response exceeds 1 MiB')
  print(out);return 0
 except (OSError,ValueError,KeyError,TypeError,RecursionError) as error:
  print(json.dumps({'status':'failed','error':str(error)[:240]}),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
