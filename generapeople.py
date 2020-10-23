"""
Build different lektor files with lists of people.
The different files account for lists of participants and speakers.
"""
import logging
import psycopg2
from pathlib import Path
import gspread
import pandas as pd

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

base = "/Users/jer/git/adassweb/website/content"
program_url = "https://schedule.adass2020.es/adass2020/speaker/"
folders = ["participants", "speakers"]
speakers = []
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

def make_folder_structure():
    for item in folders:
        fold = Path(item)
        content = template
        content = content.replace("title:", f"title: {item.capitalize()}")
        content = content.replace("description:", f"description: {item.capitalize()}")
        Path.mkdir(base / fold, parents=True, exist_ok=True)
        fn = open(base / fold / "contents.lr", "w")
        fn.write(content)
        fn.close()
    log.info(" making folders successful")


def fill_participants():
    fold = Path(folders[0])
    contents = ""
    for idx, row in participants.iterrows():
        contents += f"- {row['Name']} {row['Surname']} - {row['Affiliation']}\n"
    fn = open(base / fold / "contents.lr", "a")
    fn.write(contents)
    fn.close()


def fill_speakers():
    fold = Path(folders[1])
    contents = ""
    for pack in speakers:
        name, institution, code = pack
        contents += f"- <a href='{program_url}/{code}' target='_blank'>{name}</a> - {institution}\n"
    fn = open(base / fold / "contents.lr", "a")
    fn.write(contents)
    fn.close()


gc = gspread.service_account()
wks = gc.open('ADASS XXX Registrations').sheet1
gdf = pd.DataFrame(wks.get_all_records())[1:]

# fetch participants
invited = gdf[gdf["INVITED"] == "Yes"]
not_invited = gdf[gdf["INVITED"] == ""]
payed = not_invited[not_invited["Amount"] != 0]
df = pd.concat([invited, payed])
participants = df.sort_values("Surname")

conn = psycopg2.connect(database="pretalx",
                        user="pretalx",
                        password="",
                        host="pretalx.adass2020.es",
                        port="5432")

# # build listings data structure
# sql = """
# SELECT
# title, abstract, submission_submission.code, name
# FROM
# submission_submission,
# person_user
# WHERE
# submission_submission.main_author_id=person_user.id
# AND submission_submission.state='confirmed'
# """

# # fill participants
# sql_bofs = sql
# sql_bofs += """
# AND submission_submission.submission_type_id=4
# ORDER BY title
# """
# cur = conn.cursor()
# cur.execute(sql_bofs)
# for row in cur:
#     bofs.append(row)
#
# # fill speakers
# sql_demos = sql
# sql_demos += """
# AND submission_submission.submission_type_id=15
# ORDER BY title
# """
# cur = conn.cursor()
# cur.execute(sql_demos)
# for row in cur:
#     demos.append(row)

# start filling files
make_folder_structure()
fill_participants()
# fill_speakers()

# close connection
conn.close()
