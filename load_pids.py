"""
Add PID (paper ID) values to the relevant entries in the pretalx DB.

Usage:
    load_pids.py papers.tab
"""
import sys
import psycopg2


SQL = "UPDATE submission_submission SET paper_id = '{}' WHERE id = {}"


# This could/should be better :-)
try:
    fname = sys.argv[1]
except IndexError:
    print('usage: load_pids.py /path/to/papers.tab', file=sys.stderr)
    sys.exit(1)

with psycopg2.connect(database="pretalx", user="pretalx", password="",
                      host='localhost') as conn:
    with conn.cursor() as cur, open(fname) as f:
        # Here we are in a transaction
        # The papers.tab format is:
        # submission.id, "submission.title"\s*; PID
        for row in f:
            if row.startswith('#'):
                continue
            aid, the_rest = row.split(',', maxsplit=1)
            title, pid = the_rest.rsplit(';', maxsplit=1)

            aid = int(aid.strip())
            title = title.strip()[1:-1]            # remove quotes
            pid = pid.strip()
            assert int(pid.split('-')[-1]) == aid
            cur.execute(SQL.format(pid, aid))
