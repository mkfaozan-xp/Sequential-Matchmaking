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


def auxiliary_pair_label(intro,feedback,as_of):
    """Unconditional recorded mutual Yes after qualifying date, including late Yes.

    Complete fixed cohorts only. No-date/no-response is no recorded pair success,
    not a negative individual preference. Official msmi_label is unchanged.
    """
    if as_of<intro['assigned_day']+40:return None
    events=[e for e in feedback if e['introduction_id']==intro['introduction_id'] and e['observed_day']<=as_of]
    dates=[e for e in events if e['event']=='date_happened' and e['value'] is True
           and 0<=e['occurred_day']-intro['assigned_day']<=30]
    for date in dates:
        yes={e['member_id'] for e in events if e['event']=='second_meeting_intention'
             and e['value']=='yes' and e['occurred_day'] is not None and e['occurred_day']>=date['occurred_day']}
        if {intro['user_a'],intro['user_b']}<=yes:return 1
    return 0


def scheduled_hold_label(intro,feedback,as_of):
    """Public protocol's scheduled hold proxy, not hidden actual availability."""
    if as_of<intro['assigned_day']+40:return None
    events=[e for e in feedback if e['introduction_id']==intro['introduction_id'] and e['observed_day']<=as_of]
    dates=[e for e in events if e['event']=='date_happened']
    days=max(8,dates[0]['occurred_day']-intro['assigned_day']+6) if dates else 8
    return min(40,days)
