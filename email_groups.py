"""
Send email to a given subset of [ADASS] participants.

Usage:
    % email_groups.py -g GROUP /path/to/registration.csv

GRUP is one of
    speaker, trainer, posterauth, admin, loc, poc, volunteer, attendee, all

To specify more than one group, simply repeat -g GROUP

Two groups deserve special mention: all and attendee.

all means everybody
attendee = all - (speaker + trainer + admin + loc + poc _ volunteer)

Special care is taken to avoid sending duplicate emails.
"""
import argparse
import csv
from email.message import EmailMessage
import os
import smtplib
import time


def isattendee(record):
    keys = ('isspeaker', 'istrainer', 'isposterauth', 'isadmin', 'isloc',
            'ispoc', 'isvolunteer')
    return all(record[key].lower() == 'false' for key in keys)


# The values of GROUPS are function that operate on a single element. They are
# ANDed together in a call to filter(fn, records) where records: List[record]
# and record is a dict containing a single row of the input CSV.
GROUPS = {
    'speaker': lambda rec: rec['isspeaker'].lower() == 'true',
    'trainer': lambda rec: rec['istrainer'].lower() == 'true',
    'posterauth': lambda rec: rec['isposterauth'].lower() == 'true',
    'admin': lambda rec: rec['isadmin'].lower() == 'true',
    'loc': lambda rec: rec['isloc'].lower() == 'true',
    'poc': lambda rec: rec['ispoc'].lower() == 'true',
    'volunteer': lambda rec: rec['isvolunteer'].lower() == 'true',
    'attendee': isattendee,
    'all': lambda rec: True
}
# Email
EMAIL_SUBJECT = 'ADASS 2020 Registration Information'
EMAIL_REPLY_TO = 'ADASS LOC <adass2020@iram.es>'
EMAIL_FROM = 'ADASS 2020 <noreply@iram.es>'
EMAIL_BODTY = '''
Dear {name},

We are less than two weeks away from ADASS 2020 and time is passing fast!

As you probably already know, ADASS will be an online conference this year.
As such, it will make use of a couple of tools to deliver talks and allow for
interaction among participants.

The platform that we use and their usage guidelines are described in

* The User Guide (https://adass2020.es/user-guide/)
* The Speaker Guide (https://adass2020.es/static/files/SpeakerGuide.pdf)

The 2020 LOC encourages you to register on our platform before the conference
and ideally between this and next week.

You will find all details on how to register in the User Guide.

For your convenience, here is the registration command that you will need to
use:

    !register {name}, {reg_code}

IMPORTANT: If you already registered (and we know some of you already did),
you do not need to re-register. Just head over to #social on our Discord
server and enjoy the good company.

For any doubt, please consult the above-mentioned documents as well as our
FAQ page (https://adass2020.es/frequently-asked-questions/). When all fails,
contact the LOC (adass2020@iram.es) ;-)

Thanks and see you soon!
The ADASS 2020 LOC
'''
SMTP_HOST = os.environ['SMTP_HOST']
SMTP_PORT = os.environ['SMTP_PORT']
SMTP_USER = os.environ['SMTP_USER']
SMTP_PASSWD = os.environ['SMTP_PASSWD']


def send_email(subject=EMAIL_SUBJECT, body=EMAIL_BODTY,
               sender=EMAIL_FROM, replyto=EMAIL_REPLY_TO,
               records=None, host=SMTP_HOST, port=SMTP_PORT,
               user=SMTP_USER, passwd=SMTP_PASSWD):

    with smtplib.SMTP_SSL(host, port) as s:
        s.login(user, passwd)
        for rec in records:
            address = f'{rec["name"]} <{rec["email"]}>'
            name = rec['name']
            code = rec['ticket_id']

            message = EmailMessage()
            message.set_content(body.format(name=name, reg_code=code))
            message['Subject'] = subject
            message['From'] = sender
            message['Reply-To'] = replyto
            message['To'] = address
            s.send_message(message)
            print(f'{address}\tMessage sent')
            time.sleep(.1)


def select_people(regfile, groups):
    def selector(record):
        return all(GROUPS[g](record) for g in groups)

    people = []
    emails = set()
    with open(regfile) as f:
        reader = csv.DictReader(f)
        for record in reader:
            if selector(record) and record['email'] not in emails:
                people.append(record)
                emails.add(record['email'])
    return people


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--group', '-g', required=True, action='append',
                        choices=list(GROUPS))
    parser.add_argument('regfile', metavar='REG_CSV', nargs=1,
                        help='registration csv file')
    args = parser.parse_args()

    groups = args.group
    if 'all' in groups:
        groups = ['all']

    records = select_people(args.regfile[0], groups)
    send_email(records=records)
