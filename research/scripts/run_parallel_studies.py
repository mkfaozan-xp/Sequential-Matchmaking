"""Two study processes, each with exactly one episode worker."""
import os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    children=[];streams=[]
    try:
        for matrix,name in [('final','final_test'),('research','research')]:
            stream=(ROOT/'results'/f'{name}.log').open('w');streams.append(stream)
            p=subprocess.Popen([sys.executable,'scripts/run_matrix.py','--matrix',matrix,'--jobs','1'],cwd=ROOT,
                stdout=stream,stderr=subprocess.STDOUT,env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1'))
            children.append((name,p))
        while any(p.poll() is None for _,p in children):time.sleep(.2)
        codes={name:p.returncode for name,p in children};print(codes,flush=True)
        return 0 if all(c==0 for c in codes.values()) else 2
    finally:
        for _,p in children:
            if p.poll() is None:p.kill()
            p.wait()
        for s in streams:s.close()
if __name__=='__main__':raise SystemExit(main())
