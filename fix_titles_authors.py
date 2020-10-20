"""
Simply fetch the PID (paper id) for each contribution and prepend it to the
contribution title. This is done entirely in the database.
"""
import argparse
import os
import sys
from bs4 import BeautifulSoup
import psycopg2


CODES = {
 'P': 'Poster',
 'O': 'Oral Contribution',
 'B': 'BoF',
 'D': 'Focus Demo',
 'I': 'Invited Talk',
 'H': 'Software Prize Talk',
}

SELECT = '''\
SELECT
    submission_submission.id,
    submission_submission.code,
    submission_submission.paper_id,
    submission_submission.title,
    person_user.name
FROM
    submission_submission,
    person_user
WHERE
    submission_submission.state not in ('deleted', 'withdrawn')
    AND submission_submission.main_author_id = person_user.id
ORDER BY
    submission_submission.id
'''


def mkcssclass(s):
    s = s.strip().replace(' ', '_')
    return s.lower()


def fix_auth_order(first_author, all_authors):
    if first_author not in all_authors:
        print(first_author, all_authors)
    all_authors.remove(first_author)
    return ','.join(
        [first_author] + sorted(all_authors, key=lambda s: s.split()[-1])
    )


def edit_files(event, changes, root):
    schedule_dir = os.path.join(root, event, 'schedule')
    # export_dir = os.path.join(schedule_dir, 'export')

    index_path = os.path.join(schedule_dir, 'index.html')

    with open(index_path) as f:
        soup = BeautifulSoup(f, 'html.parser')
        for container in soup.find_all('div', 'pretalx-schedule-talk'):
            code = container['id']
            if code not in changes:
                continue

            spans = container.div.find_all('span')
            title_span = spans[0]
            if 'pretalx-schedule-talk-title' not in title_span['class']:
                continue

            authors_span = spans[1]
            if 'pretalx-schedule-talk-speakers' not in authors_span['class']:
                continue
            all_authors = [s.strip() for s in
                           authors_span.string.strip()[1:-1].split(',')]

            new_title, first_author = changes[code]

            # Now make the changes
            title_span.string = new_title
            authors_span.string = fix_auth_order(first_author, all_authors)
            container['class'].append(mkcssclass(new_title.split(' (')[0]))
    print(soup.prettify())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--event', '-e', type=str, help='event name')
    parser.add_argument('root', metavar='HTML_ROOT', type=str, nargs=1,
                        help='root of the pretalx HTML export')
    args = parser.parse_args()
    root = args.root[0]

    conn = psycopg2.connect(database="pretalx",
                            user="pretalx",
                            password="",
                            host="localhost",
                            port="5432")
    cur = conn.cursor()
    cur.execute(SELECT)

    # Submission code -> new title
    changes = {}
    for row in cur:
        (pk, code, pid, title, first_author) = row
        if pid is None:
            print(f'{title}: SKIPPED', file=sys.stderr)
            continue
        typ = CODES[pid[0]]
        new_title = f'{typ} ({pid}) - {title}'
        assert code not in changes
        changes[code] = (new_title, first_author)

    # Now edit the HTML/iCal etc.
    # The HTML dump has this structure:
    #   event_name/
    #       schedule/
    #           index.html
    #           feed.xml
    #           export/
    #               schedule.[ics|json|xcal|xml]
    # Plus other files we do not want to change.
    edit_files(args.event, changes, root)
