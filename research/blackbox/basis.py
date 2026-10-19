"""Bounded nonlinear lift of observed features; no training dependency or IDs."""
import itertools
from functools import lru_cache

BASES=('identity','interactions_v1','compact','signal_projection','without_outcome_history')

def indices(names,basis):
    if basis=='compact':return [i for i,n in enumerate(names) if ':count:' not in n]
    if basis=='signal_projection':
        return [i for i,n in enumerate(names) if not any(k in n for k in ('emotional_availability','space_for_relationship','relocate'))]
    if basis=='without_outcome_history':return [i for i,n in enumerate(names) if not n.startswith(('outcome:','actor:'))]
    return list(range(len(names)))

def specifications(names):
    return _specifications(tuple(names))

@lru_cache(maxsize=8)
def _specifications(names):
    agree=[i for i,name in enumerate(names) if name.endswith(':agree')]
    terms=[(f'{names[a]}*{names[b]}',a,b) for a,b in itertools.combinations(agree,2)]
    for name in ('age_gap','wait_min','wait_max','history_count_min','history_count_max'):
        if name in names:
            i=names.index(name);terms.append((name+'^2',i,i))
    if 'history_yes_min' in names and 'history_yes_max' in names:
        terms.append(('history_yes_product',names.index('history_yes_min'),names.index('history_yes_max')))
    return terms

def lifted_names(names,basis='identity'):
    if basis not in BASES:raise ValueError('unknown feature basis')
    return [names[i] for i in indices(names,basis)]+([t[0] for t in specifications(names)] if basis=='interactions_v1' else [])

def lift(x,names,basis='identity'):
    if len(x)!=len(names):raise ValueError('raw feature dimensions')
    if basis not in BASES:raise ValueError('unknown feature basis')
    return [x[i] for i in indices(names,basis)]+([x[a]*x[b] for _,a,b in specifications(names)] if basis=='interactions_v1' else [])
