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

The special group all is the only one that cannot be used in conjuction with
any other group (to avoid easy mistakes).

Special care is taken to avoid sending duplicate emails.
"""
import argparse
import csv
from email.message import EmailMessage
import os
import smtplib
import sys
import time


def isattendee(record, operator=all):
    keys = ('isspeaker', 'istrainer', 'isposterauth', 'isadmin', 'isloc',
            'ispoc', 'isvolunteer')
    return operator(record[key].lower() == 'false' for key in keys)


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

We are less than one week away from ADASS 2020 and time is passing fast!

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
use in the ADASS Discord #registration channel (you can paste it as is):

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
               user=SMTP_USER, passwd=SMTP_PASSWD, dryrun=True):

    with smtplib.SMTP_SSL(host, port) as s:
        s.login(user, passwd)
        writer = csv.DictWriter(sys.stdout, fieldnames=records[0].keys())
        writer.writeheader()
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
            if dryrun:
                print(message)
            else:
                s.send_message(message)
            writer.writerow(rec)
            time.sleep(.1)


def select_people(regfile, groups, operator=all):
    def selector(record, operator):
        return operator(GROUPS[g](record) for g in groups)

    people = []
    emails = set()
    with open(regfile) as f:
        reader = csv.DictReader(f)
        for record in reader:
            if selector(record, operator) and record['email'] not in emails:
                people.append(record)
                emails.add(record['email'])
    return people


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--operator', required=False, type=str,
                        choices=('and', 'or'), default='and',
                        help='logical op [defaults to and]')
    parser.add_argument('--subject', '-s', required=False, type=str,
                        help='custom email subject')
    parser.add_argument('--body', '-b', required=False, type=str,
                        help='custom text file with email body')
    parser.add_argument('--group', '-g', required=True, action='append',
                        choices=list(GROUPS))
    parser.add_argument('--exclude', '-e', required=False, type=str,
                        help='cvs reg file with records to exclude')
    parser.add_argument('regfile', metavar='REG_CSV', nargs=1,
                        help='registration csv file')
    parser.add_argument('--dry-run', dest='dryrun', action='store_true',
                        help='simulation mode: do not send emails')
    args = parser.parse_args()

    groups = args.group
    if 'all' in groups and len(groups) > 1:
        parser.error('You cannot specify `all` together with any other group')

    if args.body:
        body = open(args.body).read()
    else:
        body = EMAIL_BODTY
    if args.subject:
        subject = args.subject
    else:
        subject = EMAIL_SUBJECT
    if args.operator == 'or':
        logicalfn = any
    else:
        logicalfn = all

    records = select_people(args.regfile[0], groups, operator=logicalfn)

    if args.exclude:
        exclude_records = select_people(args.exclude, ['all'])
        exclude_set = set(','.join(v.lower() for v in rec.values())
                          for rec in exclude_records)
        clean = []
        while records:
            rec = records.pop()
            key = ','.join(v.lower() for v in rec.values())
            if key not in exclude_set:
                clean.append(rec)
        clean.reverse()
    else:
        clean = records

    send_email(records=clean, body=body, subject=subject, dryrun=args.dryrun)
