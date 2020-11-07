"""
For each day and time slot create a CSV of all panelists for that slot.
"""
import csv
from datetime import datetime
import os
import psycopg2


# Just the start times
DAYS = {
    'Sunday-morning': (datetime(2020, 11, 8, 5, 50),
                       datetime(2020, 11, 8, 9, 30)),
    'Sunday-afternoon': (datetime(2020, 11, 8, 10, 40),
                         datetime(2020, 11, 8, 14, 45)),
    'Sunday-evening': (datetime(2020, 11, 8, 16, 40),
                       datetime(2020, 11, 8, 20, 30)),

    'Monday-morning': (datetime(2020, 11, 9, 5, 50),
                       datetime(2020, 11, 9, 9, 30)),
    'Monday-afternoon': (datetime(2020, 11, 9, 10, 40),
                         datetime(2020, 11, 9, 14, 45)),
    'Monday-evening': (datetime(2020, 11, 9, 16, 40),
                       datetime(2020, 11, 9, 20, 30)),

    'Tuesday-morning': (datetime(2020, 11, 10, 5, 50),
                        datetime(2020, 11, 10, 9, 30)),
    'Tuesday-afternoon': (datetime(2020, 11, 10, 10, 40),
                          datetime(2020, 11, 10, 14, 45)),
    'Tuesday-evening': (datetime(2020, 11, 10, 16, 40),
                        datetime(2020, 11, 10, 20, 30)),

    'Wednesday-morning': (datetime(2020, 11, 11, 5, 50),
                          datetime(2020, 11, 11, 9, 30)),
    'Wednesday-afternoon': (datetime(2020, 11, 11, 10, 40),
                            datetime(2020, 11, 11, 14, 45)),
    'Wednesday-evening': (datetime(2020, 11, 11, 16, 20),
                          datetime(2020, 11, 11, 21, 30)),

    'Thursday-morning': (datetime(2020, 11, 12, 5, 50),
                         datetime(2020, 11, 12, 9, 30)),
    'Thursday-afternoon': (datetime(2020, 11, 12, 10, 40),
                           datetime(2020, 11, 12, 14, 45)),
    'Thursday-evening': (datetime(2020, 11, 12, 16, 40),
                         datetime(2020, 11, 12, 20, 30)),
}


def write_csv(root_name, authors):
    fname = f'{root_name}.csv'

    if os.path.exists(fname):
        raise Exception(f'File {fname} already exists!')

    with open(fname, 'w') as f:
        writer = csv.writer(f)
        for row in authors:
            writer.writerow(row)


def find_authors(talk_ids, conn):
    print(f'finding authors for {talk_ids}')
    cur = conn.cursor()
    cur.execute('''
select
    u.email,
    u.name
from
    person_user u,
    submission_submission s
where
    s.id in ({}) and
    s.main_author_id=u.id'''.format(','.join(str(i) for i in talk_ids)))
    return cur.fetchall()


def _fetch_n_fix_record(cur):
    start, talk_id = next(cur)
    # there is a problem with the pretalx database: its times should be
    # UTC but they actually have a 1 our shift!
    start = datetime(
        start.year,
        start.month,
        start.day,
        hour=start.hour + 1,
        minute=start.minute
    )
    return start, talk_id


if __name__ == '__main__':
    conn = psycopg2.connect(database="pretalx",
                            user="pretalx",
                            password="",
                            host="localhost",
                            port="5432")
    cur = conn.cursor()

    # Step 1: find all the slots of the latest schedule version, excluding
    # breaks.
    cur.execute('''
select
    start, submission_id
from
    schedule_talkslot
where
    room_id = 1 and
    schedule_id = (select max(schedule_id) from schedule_talkslot) and
    is_visible = true and
    description is null
order by start''')

    # Dictionaries are insertion-ordered in python 3.6+ :-)
    talk_ids = []
    start, talk_id = _fetch_n_fix_record(cur)
    for slot_name, (slot_start, slot_end) in DAYS.items():
        while slot_start <= start <= slot_end:
            # Still in this slot
            print(f'{start} between {slot_start} and {slot_end}')
            talk_ids.append(talk_id)
            try:
                start, talk_id = _fetch_n_fix_record(cur)
            except StopIteration:
                break

        # Next time slot: close the current one and reset talk_ids
        write_csv(slot_name, find_authors(talk_ids, conn))
        talk_ids = []
