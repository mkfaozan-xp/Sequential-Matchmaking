"""Mature recorded-event labels, never inferred psychological preferences."""

def msmi_label(intro,feedback,as_of):
    events=[e for e in feedback if e['introduction_id']==intro['introduction_id'] and e['observed_day']<=as_of]
    dates=[e for e in events if e['event']=='date_happened' and e['value'] is True
           and e['occurred_day']-intro['assigned_day']<=30]
    for date in dates:
        seconds={e['member_id'] for e in events if e['event']=='second_meeting_intention'
                 and e['value']=='yes' and e['occurred_day'] is not None
                 and 0<=e['occurred_day']-date['occurred_day']<=3}
        if {intro['user_a'],intro['user_b']}<=seconds:return 1
    # Conservative maximum window: date by +30, on-time intentions by +33.
    if as_of>=intro['assigned_day']+33:return 0
    return None

def response_label(intro,actor,feedback,as_of):
    found=[e for e in feedback if e['introduction_id']==intro['introduction_id']
           and e['member_id']==actor and e['event']=='introduction_response' and e['observed_day']<=as_of]
    if found:return int(found[-1]['value']=='yes')
    return 0 if as_of>=intro['response_deadline_day'] else None
