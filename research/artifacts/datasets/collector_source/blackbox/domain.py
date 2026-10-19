"""Public eligibility semantics adapted without change from the MIT-licensed starter.
See ../starter/LICENSE. No simulator or hidden state is imported.
"""
HARD = ['age_min','age_max','who_to_meet','relationship_structure','smoking',
        'partner_smoking','has_children','partner_children','wants_children',
        'acceptable_zones','schedule']

SOFT = ['relationship_goal','relationship_pace','lifestyle','conversations',
        'emotional_availability','space_for_relationship','relocate']

OPTIONS = {
    'relationship_goal':['long_term','exploring'],
    'relationship_pace':['slow','steady','quick'],
    'lifestyle':['quiet','mixed','social'],
    'conversations':['ideas','stories','practical','playful'],
    'emotional_availability':['ready','taking_time'],
    'space_for_relationship':['limited','moderate','ample'],
    'relocate':['yes','no','unsure'],
}

def eligibility(a,b):
    """Public pair-level hard checks only; availability is separately checked by simulator."""
    if a['member_id']==b['member_id']: return {'status':'infeasible','reasons':['same_member']}
    if a['pool_id']!=b['pool_id']: return {'status':'infeasible','reasons':['different_pool']}
    if min(a['age'],b['age'])<18: return {'status':'infeasible','reasons':['underage']}
    fa,fb=a['fields'],b['fields']; missing=[]; failures=[]
    for member,f in ((a,fa),(b,fb)):
        missing += [member['member_id']+':'+k for k in HARD if f.get(k) is None]
    for x,y,fx,fy in ((a,b,fa,fb),(b,a,fb,fa)):
        if fx.get('who_to_meet') is not None and y['gender'] not in fx['who_to_meet']: failures.append('who_to_meet')
        if fx.get('age_min') is not None and y['age']<fx['age_min']: failures.append('age')
        if fx.get('age_max') is not None and y['age']>fx['age_max']: failures.append('age')
        if fx.get('acceptable_zones') is not None and y['zone'] not in fx['acceptable_zones']: failures.append('geography')
        if fx.get('partner_smoking')=='no_smoking' and fy.get('smoking') in ('yes','occasionally'): failures.append('smoking')
        if fx.get('partner_children')=='no_children' and fy.get('has_children') is True: failures.append('children_present')
    if fa.get('relationship_structure') is not None and fb.get('relationship_structure') is not None and fa['relationship_structure']!=fb['relationship_structure']: failures.append('relationship_structure')
    if {fa.get('wants_children'),fb.get('wants_children')}=={'yes','no'}: failures.append('children_plans')
    if fa.get('schedule') is not None and fb.get('schedule') is not None and not set(fa['schedule'])&set(fb['schedule']): failures.append('schedule')
    return {'status':'infeasible' if failures else ('needs_clarification' if missing else 'feasible'),
            'reasons':sorted(set(failures)),'missing':missing}
