"""
Group abstracts of a given submission type (e.g. Talk) in themes and list their
compatible time slots (defined in the code itself for now).

Output a CSV table (to STDOUT) of the form

# PID,Title,(Time Slot)+

e.g.

# PID,Title,06-09,12-15,17-20
O3-14,Test Talk Title,True,False,True
...
"""
import argparse
import csv
import sys
import psycopg2
# from adass_themes import Abstract


# These come from the raw database
TIME_QUESTION_ID = 12
SUB_TYPE_IDS = '''
  1 | Invited Talk
  3 | Talk
  4 | BoF
 13 | Poster
 14 | Tutorial
 15 | Focus Demo
 17 | Software Prize Talk
 18 | Poster / Talk Waiting List
'''
TIME_SLOTS = {
    '06:00 to 09:00 UTC': lambda row: row[-3],
    '11:00 to 14:00 UTC': lambda row: row[-2],
    '17:00 to 20:00 UTC': lambda row: row[-1],
}
FIELDS = {
    'PID': lambda row: row[0],
    'Title': lambda row: row[1],
}
FIELDS.update(TIME_SLOTS)
SQL = f'''\
SELECT
    submission_submission.paper_id,
    submission_submission.title,
    submission_submission.submission_type_id,
    submission_answer.answer
FROM
    submission_submission,
    submission_answer
WHERE
    submission_submission.state not in ('deleted', 'withdrawn')
    AND submission_submission.submission_type_id = %d
    AND submission_submission.id = submission_answer.submission_id
    AND submission_answer.question_id = {TIME_QUESTION_ID}
ORDER BY
    submission_submission.paper_id
'''


parser = argparse.ArgumentParser()
parser.add_argument('sub_type_id', metavar='TYPE_ID', type=int, nargs=1,
                    help='submission type: ' + SUB_TYPE_IDS)
args = parser.parse_args()
type_id = args.sub_type_id[0]

conn = psycopg2.connect(database="pretalx",
                        user="pretalx",
                        password="",
                        host="localhost",
                        port="5432")
cur = conn.cursor()
cur.execute(SQL % (type_id, ))

writer = csv.DictWriter(sys.stdout, fieldnames=FIELDS)
writer.writeheader()
for row in cur:
    # [pid, title, _, answer] = rec
    row += tuple(slot not in row[-1] for slot in TIME_SLOTS)
    writer.writerow({k: fn(row) for k, fn in FIELDS.items()})
