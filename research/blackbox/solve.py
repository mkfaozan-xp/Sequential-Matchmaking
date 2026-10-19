"""Isolated optional general-graph binary matching; no inference state access."""
import json,sys
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import csc_matrix

def solve(edges):
    nodes=sorted({v for pair,_ in edges for v in pair});index={v:i for i,v in enumerate(nodes)}
    n=len(edges);row=[];col=[]
    for j,(pair,_) in enumerate(edges):
        for v in pair:row.append(index[v]);col.append(j)
    matrix=csc_matrix((np.ones(2*n),(row,col)),shape=(len(nodes),n))
    result=milp(c=-np.array([w for _,w in edges]),integrality=np.ones(n),bounds=Bounds(0,1),
        constraints=LinearConstraint(matrix,0,1),options={'time_limit':.3,'mip_rel_gap':0.0})
    if result.x is None:raise RuntimeError('no feasible incumbent')
    return {'pairs':[list(pair) for (pair,_),v in zip(edges,result.x) if v>.5], 'optimal':bool(result.success)}
if __name__=='__main__':print(json.dumps(solve(json.load(sys.stdin)),allow_nan=False))
