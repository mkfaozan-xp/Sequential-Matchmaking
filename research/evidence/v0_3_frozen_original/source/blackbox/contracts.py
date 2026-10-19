"""Strict public v1 observation schema and score-independent action validation."""
import json
import re
from .domain import HARD, SOFT, OPTIONS, eligibility

LIMIT = 1024 * 1024
GENDERS = {'woman', 'man', 'non_binary'}
HARD_OPTIONS = {
    'relationship_structure': {'monogamous', 'non_monogamous'},
    'smoking': {'no', 'occasionally', 'yes'},
    'partner_smoking': {'no_smoking', 'any'},
    'partner_children': {'no_children', 'any'},
    'wants_children': {'yes', 'no', 'unsure'},
}
SCHEDULE = {'weekday_evening', 'weekend_day', 'weekend_evening'}
MEMBER_KEYS = {'member_id', 'pool_id', 'synthetic', 'age', 'gender', 'zone', 'arrived_day',
               'available', 'fields', 'field_status', 'field_observed_day', 'source'}
STATE_KEYS = {'schema_version', 'synthetic', 'day', 'ask_budget_remaining', 'members',
              'introductions', 'feedback', 'ask_log'}


def integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(label)


def string(value, label):
    if not isinstance(value, str) or not value or len(value) > 256:
        raise ValueError(label)


def array(value, label, allowed=None):
    if not isinstance(value, list) or not value:
        raise ValueError(label)
    if not all(isinstance(v, str) and v for v in value) or len(value) != len(set(value)):
        raise ValueError(label)
    if allowed is not None and not set(value) <= allowed:
        raise ValueError(label)


def validate_member(member, day):
    if not isinstance(member, dict) or set(member) != MEMBER_KEYS:
        raise ValueError('member schema')
    if not isinstance(member['member_id'], str) or not re.fullmatch(r'syn_[0-9a-f]{32}', member['member_id']):
        raise ValueError('member ID')
    for key in ('pool_id', 'zone'):
        string(member[key], key)
    if member['gender'] not in GENDERS or member['source'] != 'synthetic_questionnaire':
        raise ValueError('member category/provenance')
    if member['synthetic'] is not True or type(member['available']) is not bool:
        raise ValueError('member flags')
    integer(member['age'], 18, 100, 'age')
    integer(member['arrived_day'], 0, day, 'arrival day')
    expected = set(HARD + SOFT)
    for key in ('fields', 'field_status', 'field_observed_day'):
        if not isinstance(member[key], dict) or set(member[key]) != expected:
            raise ValueError('field schema')
    for key in HARD + SOFT:
        value = member['fields'][key]
        status = member['field_status'][key]
        observed = member['field_observed_day'][key]
        if status not in ('not_asked', 'declined', 'observed'):
            raise ValueError('field status')
        if (value is not None) != (status == 'observed'):
            raise ValueError('field/status mismatch')
        if value is None:
            if observed is not None:
                raise ValueError('unknown observation timestamp')
            continue
        integer(observed, member['arrived_day'], day, 'field observation day')
        if key in ('age_min', 'age_max'):
            integer(value, 18, 65, key)
        elif key == 'has_children':
            if type(value) is not bool:
                raise ValueError('has_children must be boolean')
        elif key == 'who_to_meet':
            array(value, key, GENDERS)
        elif key == 'schedule':
            array(value, key, SCHEDULE)
        elif key == 'acceptable_zones':
            array(value, key)
        else:
            allowed = HARD_OPTIONS.get(key, OPTIONS.get(key))
            if not isinstance(value, str) or value not in allowed:
                raise ValueError('field category: ' + key)
    fields = member['fields']
    if fields['age_min'] is not None and fields['age_max'] is not None and fields['age_min'] > fields['age_max']:
        raise ValueError('inverted age range')


def validate_request(request):
    if not isinstance(request, dict) or set(request) != {'schema_version', 'phase', 'state', 'memory'}:
        raise ValueError('request keys')
    # Reject overflow-to-Infinity too, not only the JSON NaN token.
    if len(json.dumps(request, allow_nan=False).encode()) > LIMIT:
        raise ValueError('request exceeds 1 MiB')
    if request['schema_version'] != '1.0.0' or request['phase'] not in ('ask', 'match'):
        raise ValueError('protocol version/phase')
    state = request['state']
    if not isinstance(state, dict) or set(state) != STATE_KEYS:
        raise ValueError('state schema')
    if state['schema_version'] != '1.0.0' or state['synthetic'] is not True:
        raise ValueError('synthetic v1 state required')
    integer(state['day'], 0, 59, 'decision day')
    integer(state['ask_budget_remaining'], 0, 12, 'ask budget')
    for key in ('members', 'introductions', 'feedback', 'ask_log'):
        if not isinstance(state[key], list):
            raise ValueError('state array: ' + key)
    ids = set()
    for member in state['members']:
        validate_member(member, state['day'])
        if member['member_id'] in ids:
            raise ValueError('duplicate member')
        ids.add(member['member_id'])
    introductions = {}
    for intro in state['introductions']:
        expected = {'introduction_id','user_a','user_b','assigned_day','response_deadline_day','logging_policy','propensity'}
        if not isinstance(intro, dict) or set(intro) != expected:
            raise ValueError('introduction schema')
        string(intro['introduction_id'], 'introduction ID')
        if intro['introduction_id'] in introductions or intro['user_a'] == intro['user_b'] or not {intro['user_a'], intro['user_b']} <= ids:
            raise ValueError('introduction references')
        integer(intro['assigned_day'], 0, state['day'], 'assignment day')
        integer(intro['response_deadline_day'], intro['assigned_day'], intro['assigned_day']+30, 'response deadline')
        string(intro['logging_policy'], 'logging policy')
        if intro['propensity'] is not None and (type(intro['propensity']) not in (int,float) or not 0 < intro['propensity'] <= 1):
            raise ValueError('propensity')
        introductions[intro['introduction_id']] = intro
    for event in state['feedback']:
        required = {'introduction_id','member_id','event','value','occurred_day','observed_day'}
        if not isinstance(event, dict) or not required <= set(event) or set(event)-required-{'missing_reason'}:
            raise ValueError('feedback schema')
        intro = introductions.get(event['introduction_id'])
        if intro is None:
            raise ValueError('feedback introduction reference')
        integer(event['observed_day'], intro['assigned_day'], state['day'], 'feedback observation day')
        if event['occurred_day'] is not None:
            integer(event['occurred_day'], intro['assigned_day'], event['observed_day'], 'feedback occurrence day')
        name, value, actor = event['event'], event['value'], event['member_id']
        if name in ('introduction_response','second_meeting_intention'):
            if actor not in (intro['user_a'],intro['user_b']) or value not in ('yes','no',None):
                raise ValueError('directional feedback')
            if value is not None and event['occurred_day'] is None:
                raise ValueError('missing event time')
        elif name in ('date_happened','pause_after_mutual_interest'):
            if actor is not None or type(value) is not bool or event['occurred_day'] is None:
                raise ValueError('pair feedback')
        else:
            raise ValueError('feedback event')
        if event.get('missing_reason') not in (None,'no_response'):
            raise ValueError('feedback missing reason')
    for log in state['ask_log']:
        if not isinstance(log,dict) or set(log) != {'member_id','field','observed_day','values','statuses'}:
            raise ValueError('ask-log schema')
        if log['member_id'] not in ids or log['field'] not in ['constraints'] + SOFT:
            raise ValueError('ask-log reference')
        integer(log['observed_day'],0,state['day'],'ask-log timestamp')
        keys = set(HARD if log['field']=='constraints' else [log['field']])
        if not isinstance(log['values'],dict) or not isinstance(log['statuses'],dict) or set(log['values']) != keys or set(log['statuses']) != keys:
            raise ValueError('ask-log fields')
        # Historic values are observations; they never overwrite current member records.
        for key in keys:
            status = log['statuses'][key]
            if status not in ('observed','declined','not_asked') or (log['values'][key] is not None) != (status=='observed'):
                raise ValueError('ask-log status')
    return state


def validate_actions(state, phase, actions):
    if not isinstance(actions, list):
        raise ValueError('action array')
    members = {m['member_id']:m for m in state['members']}
    used, cost = set(), 0
    past = {tuple(sorted((i['user_a'],i['user_b']))) for i in state['introductions']}
    if phase == 'ask':
        for ask in actions:
            if not isinstance(ask,dict) or set(ask) != {'member_id','field'}:
                raise ValueError('ask schema')
            ident,field = ask['member_id'],ask['field']
            if not isinstance(ident,str) or not isinstance(field,str):
                raise ValueError('ask types')
            if ident not in members or not members[ident]['available'] or (ident,field) in used:
                raise ValueError('ask unavailable/duplicate')
            if field not in ['constraints']+SOFT:
                raise ValueError('ask field')
            used.add((ident,field));cost += 3 if field=='constraints' else 1
        if cost > state['ask_budget_remaining']:
            raise ValueError('ask overspend')
    elif phase == 'match':
        for pair in actions:
            if not isinstance(pair,list) or len(pair)!=2 or not all(isinstance(v,str) for v in pair):
                raise ValueError('pair schema')
            if len(set(pair))!=2 or used.intersection(pair):
                raise ValueError('pair overlap')
            if any(i not in members or not members[i]['available'] for i in pair):
                raise ValueError('pair availability')
            if tuple(sorted(pair)) in past or eligibility(*(members[i] for i in pair))['status']!='feasible':
                raise ValueError('pair not eligible')
            used.update(pair)
    else:
        raise ValueError('action phase')
    return actions
