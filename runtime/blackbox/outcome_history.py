"""Observed post-date history; null answers are never negative preferences."""

def summarize(state):
    day=state['day'];introductions={i['introduction_id']:i for i in state.get('introductions',[]) if 'introduction_id' in i}
    out={}
    def member(ident):
        return out.setdefault(ident,{'yes':0,'answered':0,'records':0,'timely_yes':0,'dates':0,'date_records':0})
    dates={};date_seen=set()
    for e in state['feedback']:
        if e['observed_day']>day:continue
        intro=introductions.get(e['introduction_id'])
        if intro is None:continue
        if e['event']=='date_happened':
            if e['introduction_id'] in date_seen:continue
            date_seen.add(e['introduction_id'])
            for ident in (intro['user_a'],intro['user_b']):
                m=member(ident);m['date_records']+=1;m['dates']+=e['value'] is True
            if e['value'] is True:dates[e['introduction_id']]=e['occurred_day']
    seen=set()
    for e in state['feedback']:
        if e['observed_day']>day or e['event']!='second_meeting_intention':continue
        ident=e['member_id'];key=(e['introduction_id'],ident)
        if key in seen:continue
        seen.add(key)
        if e['introduction_id'] not in dates or ident is None:continue
        m=member(ident);m['records']+=1
        if e['value'] in ('yes','no'):
            m['answered']+=1;m['yes']+=e['value']=='yes'
        date=dates[e['introduction_id']]
        if e['value']=='yes' and e['occurred_day'] is not None and 0<=e['occurred_day']-date<=3:
            m['timely_yes']+=1
    return out


def vector(ident,history):
    m=history.get(ident,{})
    yes=m.get('yes',0);n=m.get('answered',0);records=m.get('records',0)
    return [(yes+1)/(n+2),min(n,10)/10,float(records==0),min(records,10)/10,
        (m.get('timely_yes',0)+1)/(records+2),
        n/max(1,records),min(m.get('dates',0),10)/10,
        (m.get('dates',0)+1)/(m.get('date_records',0)+2)]

NAMES=['second_yes_rate','second_answer_count','second_no_history','second_record_count','timely_recorded_yes_rate',
       'second_response_coverage','observed_date_count','observed_date_rate']
