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
    log.info(f"filled {len(participants)} participants")


def fill_speakers():
    fold = Path(folders[1])
    contents = ""
    speakers.sort(key=lambda tup: tup[1])  # sorts in place
    for pack in speakers:
        name, surname, code, affiliation = pack
        contents += f"- <a href='{program_url}/{code}' target='_blank'>{name} {surname}</a> - {affiliation}\n"
    fn = open(base / fold / "contents.lr", "a")
    fn.write(contents)
    fn.close()
    log.info(f"filled {len(speakers)} speakers")


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

# grab speakers
sql = """
SELECT DISTINCT ON (person_user.email) email,
person_user.code
FROM 
submission_submission,
submission_submission_speakers,
person_user
WHERE
submission_submission.id=submission_submission_speakers.submission_id
AND submission_submission_speakers.user_id=person_user.id
AND submission_submission.submission_type_id in(1,3,4,14,15,17)
AND submission_submission.state='confirmed';
"""
pgdf = pd.read_sql_query(sql, conn)
for idx, row in pgdf.iterrows():
    if not participants[participants["Email"] == row["email"]].empty:
        name = participants[participants["Email"] == row["email"]]["Name"].values[0]
        surname = participants[participants["Email"] == row["email"]]["Surname"].values[0]
        affiliation = participants[participants["Email"] == row["email"]]["Affiliation"].values[0]
        speakers.append((name, surname, row["code"], affiliation))


# start filling files
make_folder_structure()
fill_participants()
fill_speakers()

# close connection
conn.close()

