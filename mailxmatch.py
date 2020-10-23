"""
Build different lists of people registered in pretalx and/or google
spread sheet. The script makes a crossmatch between both registries
and displays the following lists.

- People in Google spreadsheet not registered in ADASS
- Main authors in pretalx not registered in ADASS
- Main authors with contributions confirmed in pretalx not registered in ADASS
- Main authors with contributions confirmed in pretalx registered in ADASS
"""
import psycopg2
from sshtunnel import SSHTunnelForwarder
import pandas as pd
import gspread

PASSWD = "*****"
KEYFILE = "/users/jer/.ssh/id_rsa"
GOOGLE_DOC = "*****"

# create an ssh tunnel
tunnel = SSHTunnelForwarder(
    ("www.adass2020.es", 22),
    ssh_username="root",
    ssh_pkey=KEYFILE,
    ssh_private_key_password=PASSWD,
    remote_bind_address=("localhost", 5432),
    local_bind_address=("localhost", 6543),
)

# start the tunnel
tunnel.start()

# create a database connection
conn = psycopg2.connect(database="pretalx", user="pretalx", host=tunnel.local_bind_host, port=tunnel.local_bind_port,)

sql = """
SELECT 
submission_submission.title, submission_submission.state, submission_submission.paper_id, person_user.email
FROM 
submission_submission,
person_user
WHERE
submission_submission.main_author_id=person_user.id
AND submission_submission.state not in ('deleted', 'withdrawn')
ORDER BY email;
"""
postgredf = pd.read_sql_query(sql, conn)
conn.close()

# stop the tunnel
tunnel.stop()

# open google spreadsheet
gc = gspread.service_account()
wks = gc.open('ADASS XXX Registrations').sheet1
gdf = pd.DataFrame(wks.get_all_records())[1:]

invited = gdf[gdf["INVITED"] == "Yes"]
not_invited = gdf[gdf["INVITED"] == ""]
not_registered = not_invited[not_invited["Amount"] == 0]
payed = not_invited[not_invited["Amount"] != 0]
registered = pd.concat([invited, payed])

print("-------------------------------------------")
print("People in Google spreadsheet not registered")
print("-------------------------------------------")
print(not_registered["Email"])

i = 1
print("---------------------------")
print("Main authors not registered")
print("---------------------------")
for idx, row in postgredf.iterrows():
    if registered[registered["Email"] == row["email"]].empty:
        print(f"{i}; {row['email']}; {row['title']}")
        i += 1

i = 1
print("--------------------------------------------------------")
print("Main authors not registered with contributions confirmed")
print("--------------------------------------------------------")
for idx, row in postgredf.iterrows():
    if registered[registered["Email"] == row["email"]].empty and row["state"] == "confirmed":
        print(f"{i}; {row['email']}; {row['title']}")
        i += 1

i = 1
print("----------------------------------------------------")
print("Main authors registered with contributions confirmed")
print("----------------------------------------------------")
for idx, row in postgredf.iterrows():
    if not registered[registered["Email"] == row["email"]].empty and row["state"] == "confirmed":
        print(f"{i}; {row['email']}; {row['paper_id']}; {row['title']}")
        i += 1
