"""
Build three lektor files with lists of contributions.

The different files account for lists of posters, talks and other oral
contributions. Each list is composed of different theme blocks, so
contributions are grouped into the different themes. Each item in
the list is a link to its own record in the ADASS program.
"""
import logging
import psycopg2
from pathlib import Path

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

base = "/Users/jer/git/adassweb/website/content"
program_url = "https://schedule.adass2020.es/adass2020/talk"
folders = ["posters", "talks", "invited-talks", "BOFs", "demos", "tutorials"]
themes = {
    "1": "Science Platforms and Data Lakes",
    "2": "Cloud Computing at Different Scales",
    "3": "Cross-Discipline Projects",
    "4": "Multi-Messenger Astronomy",
    "5": "Machine Learning, Statistics, and Algorithms",
    "6": "Time-Domain Ecosystem",
    "7": "Citizen Science Projects in Astronomy",
    "8": "Data Processing Pipelines and Science-Ready Data",
    "9": "Data Interoperability",
    "10": "Open Source Software and Community Development in Astronomy",
    "11": "Other",
}
template = """
 _model: page
---
title: 
---
description: 
---
_template: page-md.html
---
body:   
"""
listings = {}
demos = []
tutos = []
bofs = []


def make_folder_structure():
    for item in folders:
        fold = Path(item)
        content = template
        item = item.replace("-", " ")
        content = content.replace("title:", f"title: {item.capitalize()}")
        content = content.replace("description:", f"description: {item.capitalize()}")
        Path.mkdir(base / fold, parents=True, exist_ok=True)
        fn = open(base / fold / "contents.lr", "w")
        fn.write(content)
        fn.close()
    log.info(" making folders successful")


def fill_posters():
    fold = Path(folders[0])
    contents = ""
    for number, label in themes.items():
        bag = listings[number]["posters"]
        contents += f"\n**{label.upper()}**\n\n"
        for pack in bag:
            title, abstract, code, author = pack
            contents += f"- <a href='{program_url}/{code}' target='_blank'>{title}</a>, {author}\n"
    fn = open(base / fold / "contents.lr", "a")
    fn.write(contents)
    fn.close()


def fill_talks():
    fold = Path(folders[1])
    contents = ""
    for number, label in themes.items():
        bag = listings[number]["talks"]["contributed"]
        contents += f"\n**{label.upper()}**\n\n"
        for pack in bag:
            title, abstract, code, author = pack
            contents += f"- <a href='{program_url}/{code}' target='_blank'>{title}</a>, {author}\n"
    fn = open(base / fold / "contents.lr", "a")
    fn.write(contents)
    fn.close()


def fill_invited():
    fold = Path(folders[2])
    contents = ""
    for number, label in themes.items():
        bag = listings[number]["talks"]["invited"]
        if len(bag):
            contents += f"\n**{label.upper()}**\n\n"
            for pack in bag:
                title, abstract, code, author = pack
                contents += f"- <a href='{program_url}/{code}' target='_blank'>{title}</a>, {author}\n"
    fn = open(base / fold / "contents.lr", "a")
    fn.write(contents)
    fn.close()


conn = psycopg2.connect(database="pretalx",
                        user="pretalx",
                        password="",
                        host="pretalx.adass2020.es",
                        port="5432")


# build listings data structure
sql = """
SELECT
title, abstract, submission_submission.code, name
FROM
submission_submission,
person_user
WHERE
submission_submission.main_author_id=person_user.id
AND submission_submission.state='confirmed'
"""
for number, label in themes.items():
    listings[number] = {
        "posters": [],
        "talks": {
            "invited": [],
            "contributed": [],
        }
    }
    # add poster for each theme
    sql_posters = sql
    sql_posters += f"""
        AND submission_submission.submission_type_id in (13, 18)
        AND submission_submission.paper_id LIKE 'P{number}-%'
        ORDER BY title
        """
    cur = conn.cursor()
    cur.execute(sql_posters)
    for row in cur:
        listings[number]["posters"].append(row)

    # add invited talks for each theme
    sql_invited_talks = sql
    sql_invited_talks += f"""
        AND submission_submission.submission_type_id=1
        AND submission_submission.paper_id LIKE 'I{number}-%'
        ORDER BY title
        """
    cur = conn.cursor()
    cur.execute(sql_invited_talks)
    for row in cur:
        listings[number]["talks"]["invited"].append(row)

    # add contributed talks for each theme
    sql_talks = sql
    sql_talks += f"""
        AND submission_submission.submission_type_id=3
        AND submission_submission.paper_id LIKE 'O{number}-%'
        ORDER BY title
        """
    cur = conn.cursor()
    cur.execute(sql_talks)
    for row in cur:
        listings[number]["talks"]["contributed"].append(row)

# fill demos
sql_demos = sql
sql_demos += """
AND submission_submission.submission_type_id=15
ORDER BY title
"""
cur = conn.cursor()
cur.execute(sql_demos)

# fill tutos
sql_tutos = sql
sql_tutos += """
AND submission_submission.submission_type_id=14
ORDER BY title
"""
cur = conn.cursor()
cur.execute(sql_tutos)

# fill bofs
sql_bofs = sql
sql_bofs += """
AND submission_submission.submission_type_id=4
ORDER BY title
"""
cur = conn.cursor()
cur.execute(sql_bofs)



# start filling files
make_folder_structure()
fill_posters()
fill_talks()
fill_invited()
# fill_demos()
# fill_bofs()
# fill_tutorials()

# close connection
conn.close()
