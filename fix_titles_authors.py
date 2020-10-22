"""
Simply fetch the PID (paper id) for each contribution and prepend it to the
contribution title. This is done entirely in the database.

This also fixes the SVGs for the calendar integration files.
"""
import argparse
import os
import sys
from bs4 import BeautifulSoup
import psycopg2


# This is a hack
TUTORIAL_IDS = (
    'ECLRSH',
    'GEJ3BT',
    'SKDNHX',
    'WZ9YVR',
)

# Some times we do not want to display all the rooms. In these cases, we just
# index the rooms in the schedule HTML page, starting from 0 as the left-most
# room in the table/divs.
ROOMS_TO_REMOVE = (1, )

# Similarily, in Talks and Speakers we might want to hide some contribution
# types (e.g. posters).
TYPES_TO_REMOVE = (13, 18)

CODES = {
 'P': 'Poster',
 'O': 'Oral Contribution',
 'B': 'BoF',
 'D': 'Focus Demo',
 'I': 'Invited Talk',
 'H': 'Software Prize Talk',
}

# Just make sure that these SVGs are exactly what you want to inject into
# index.html. Typically this means the svg tag and its children.
ICS_SVG = 'schedule-ics.svg'
XML_SVG = 'schedule-xml.svg'

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

FIND_UNWANTED_TYPES = '''\
SELECT
    submission_submission.code
FROM
    submission_submission
WHERE
    submission_submission.submission_type_id in %s
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


def _extract_code(a):
    uri = a['href']
    if uri.endswith('/'):
        uri = uri[:-1]
    code = uri.split('/')[-1]
    return code


def edit_index(event, changes, root):
    index_path = os.path.join(root, event, 'schedule', 'index.html')

    with open(index_path) as f, open(ICS_SVG) as isvg, open(XML_SVG) as xsvg:
        soup = BeautifulSoup(f, 'html.parser')

        # Fix the SVGs
        containers = soup.find_all('div', 'export-qrcode-image')
        assert len(containers) == 2
        for i, fd in enumerate((isvg, xsvg)):
            doc = BeautifulSoup(fd.read(), 'html.parser')
            tag = doc.svg
            tag['width'] = containers[i].svg['width']
            tag['height'] = containers[i].svg['height']
            containers[i].svg.replaceWith(tag)

        # Hide rooms, if needed.
        for class_name in ('pretalx-schedule-day-room-header',
                           'pretalx-schedule-room'):
            for i, div in enumerate(soup.find_all('div', class_name)):
                if i in ROOMS_TO_REMOVE:
                    div['style'] = 'display: none;'

        # Fix titles and authors
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
    return soup.prettify()


def edit_talk(event, subs_to_hide, root):
    talk_path = os.path.join(root, event, 'talk', 'index.html')

    with open(talk_path) as f:
        soup = BeautifulSoup(f, 'html.parser')
        for section in soup.find_all('section'):
            h3 = section.find('h3', 'talk-title')
            if not h3:
                continue

            code = _extract_code(h3.a)
            if code not in subs_to_hide:
                continue

            section['style'] = 'display: none;'
    return soup.prettify()


def edit_speaker(event, subs_to_hide, root):
    talk_path = os.path.join(root, event, 'speaker', 'index.html')

    with open(talk_path) as f:
        soup = BeautifulSoup(f, 'html.parser')
        for section in soup.find_all('section'):
            h3 = section.find('h3', 'talk-title')
            if not h3:
                continue

            p = section.p
            if not p:
                continue

            links = p.find_all('a')
            codes = set(_extract_code(tag) for tag in links)
            bad = codes.intersection(subs_to_hide)

            # Here we have three cases:
            # 1. author has no contribution to hide: leave as is
            if not bad:
                continue

            # 2. author has only contributions we want to hide
            if bad == codes:
                # Hide the author and move on
                section['style'] = 'display: none;'
                continue

            # 3. author has a mixture of contributions, some good, some bad
            new_content = []
            for el in p.contents:
                if el.name == 'a' and _extract_code(el) in bad:
                    # Remove the latest thing we added to new_content if any
                    # because that would be a "|"
                    if new_content:
                        new_content.pop()
                    # and skip ahead
                    continue
                else:
                    new_content.append(el)
            # Now replace the old content with the new one
            p.contents = new_content
    return soup.prettify()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--event', '-e', type=str, required=True,
                        help='event name')
    parser.add_argument('--index', '-i', type=str, required=True,
                        help='new index file')
    parser.add_argument('--talk', '-t', type=str, required=True,
                        help='new talk file')
    parser.add_argument('--speaker', '-s', type=str, required=True,
                        help='new speaker file')
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

        # Hack
        if code in TUTORIAL_IDS:
            new_title = f'Tutorial - {title}'
        elif pid is not None:
            typ = CODES[pid[0]]
            new_title = f'{typ} ({pid}) - {title}'
            assert code not in changes
        else:
            print(f'{title}: SKIPPED', file=sys.stderr)
            continue

        changes[code] = (new_title, first_author)

    # Submissions to hide:
    subs_to_hide = []
    if TYPES_TO_REMOVE:
        cur.execute(FIND_UNWANTED_TYPES % (str(tuple(TYPES_TO_REMOVE))))
        subs_to_hide = set(res[0] for res in cur.fetchall())

    index = edit_index(args.event, changes, root)
    talk = edit_talk(args.event, subs_to_hide, root)
    speaker = edit_speaker(args.event, subs_to_hide, root)

    with open(args.index, 'w') as f:
        f.write(index)
    with open(args.talk, 'w') as f:
        f.write(talk)
    with open(args.speaker, 'w') as f:
        f.write(speaker)
