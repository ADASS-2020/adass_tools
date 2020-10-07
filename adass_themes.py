"""
Grab all poster, talk, poster / talk waiting list, focus demo abstracts from
pretalx.adass2020.es, organise them in themes and make sure that the groups are
more or less equal in size.

Some abstracts are associated to more than one theme. We use those to fill the
groups that are a bit under-represented.
"""
from dataclasses import dataclass, field
from typing import List
import psycopg2


# These come from the raw database
THEME_QUESTION_ID = 3
TUTORIAL_TYPE = 14
# select * from submission_answeroption where question_id = 3
THEMES = {
 7: "Science Platforms and Data Lakes",
 8: "Cloud Computing at Different Scales",
 9: "Cross-Discipline Projects",
 20: "Multi-Messenger Astronomy",
 21: "Machine Learning, Statistics, and Algorithms",
 22: "Time-Domain Ecosystem",
 23: "Citizen Science Projects in Astronomy",
 24: "Data Processing Pipelines and Science-Ready Data",
 25: "Data Interoperability",
 26: "Open Source Software and Community Development in Astronomy",
 27: "Other",
}
# select id, name from submission_submissiontype;
CODES = {
 13: 'P',       # "Poster",
 3: 'O',        # "Talk",
 4: 'B',        # "BoF",
 15: 'D',       # "Focus Demo",
 1: 'I',        # "Invited Talk",
 17: 'H',       # "Software Prize Talk",
 18: 'P',       # "Poster / Talk Waiting List",
}
SQL = f'''\
SELECT
    submission_submission.id,
    submission_submission.title,
    submission_submission.submission_type_id,
    submission_answer_options.answeroption_id
FROM
    submission_submission,
    submission_answer,
    submission_answer_options
WHERE
    submission_submission.state not in ('deleted', 'withdrawn')
    AND submission_submission.submission_type_id != {TUTORIAL_TYPE}
    AND submission_submission.id = submission_answer.submission_id
    AND submission_answer_options.answer_id = submission_answer.id
    AND submission_answer.question_id = {THEME_QUESTION_ID}
ORDER BY
    submission_submission.id,
    submission_answer_options.answeroption_id
'''


@dataclass
class Abstract:
    pk: int
    title: str
    type_id: int
    themes: List[str] = field(default_factory=list)


conn = psycopg2.connect(database="pretalx",
                        user="pretalx",
                        password="",
                        host="localhost",
                        port="5432")
cur = conn.cursor()
cur.execute(SQL)

title_maxlen = 0
abstracts = {}
for row in cur:
    (pk, title, type_id, theme_id) = row
    if pk not in abstracts:
        abstracts[pk] = Abstract(pk, title, type_id, themes=[theme_id, ])
        title_maxlen = max(title_maxlen, len(title))
    else:
        assert abstracts[pk].title == title, f'Ops! issues with titles {pk}'
        abstracts[pk].themes.append(theme_id)

# Let's first distribute abstract with on;ly one theme to themes:
spares = []
themes = {pk: [] for pk in THEMES}
for abstract in abstracts.values():
    if len(abstract.themes) == 0:
        raise Exception(f'Abstract {abstract.pk} has no theme!')
    elif len(abstract.themes) > 1:
        spares.append(abstract)
        continue

    themes[abstract.themes[0]].append(abstract.pk)

# n = 0
# for theme_id in themes:
#     m = len(themes[theme_id])
#     print(f'{THEMES[theme_id]}: {m}')
#     n += m
# print(f'Total: {n} abstracts plus {len(spares)} not assigned yet')

# Now the ones where we could choose either way
while spares:
    a = spares.pop()
    poorest = sorted((len(vals), _id) for _id, vals in themes.items()
                     if _id in a.themes)[0][1]
    themes[poorest].append(a.pk)

# n = 0
# for theme_id in themes:
#     m = len(themes[theme_id])
#     print(f'{THEMES[theme_id]}: {m}')
#     n += m
# print(f'Total: {n} abstracts plus {len(spares)} not assigned yet')

# Reassign an id to the themes so that they are all single digit
new_tid = 0
print('# ID, Title; PID')
for old_tid, alist in themes.items():
    new_tid += 1
    print(f'# Theme {new_tid}: {THEMES[old_tid]}')
    for aid in alist:
        a = abstracts[aid]
        qtitle = f'"{a.title}"'
        print(f'{a.pk:3}, {qtitle:{title_maxlen}}; ' +
              f'{CODES[a.type_id]}{new_tid}-{a.pk}')
