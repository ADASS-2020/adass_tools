# ADASS 2020 Emailing

Always get a copy of all emails yourself!


## Sync registration list

    % scp hello@bots.adass2020.es:registration_desk/registration.csv /tmp/registration.csv


## Setup the env
    % cd /path/to/adass_tools && source .env
    % <activate the virtual env!>


## Send new registration email to all new registered people: 

    % python3 ./email_groups.py --dry-run -g all -e ./registration-email-sent.csv /tmp/registration.csv

    % python3 ./email_groups.py -g all -e ./registration-email-sent.csv /tmp/registration.csv > new_emails.csv

    % cat new_emails.csv >> registration-email-sent.csv

Make sure that you then remove your email address and the duplicate header from ```registration-email-sent.csv```.


## Send volunteer info to all new volunteer/loc/poc etc members

    % python3 ./email_groups.py --dry-run -g volunteer -g loc -g poc --operator=or -b ./speaker_training_volunteers.email --subject="ADASS 2020 Speaker Training Sessions" -e speaker_training_sent_emails.csv /tmp/registration.csv

    % python3 ./email_groups.py  -g volunteer -g loc -g poc --operator=or -b ./speaker_training_volunteers.email --subject="ADASS 2020 Speaker Training Sessions" -e speaker_training_sent_emails.csv /tmp/registration.csv > new_emails.csv

    % cat new_emails.csv >> speaker_training_sent_emails.csv

Make sure that you then remove your email address and the duplicate header from ```speaker_training_sent_emails.csv```.


## Send speaker info to all newly registered speakers

    % python3 ./email_groups.py --dry-run -g speaker -b ./speaker_training_speakers.email --subject="ADASS 2020 Speaker Training Sessions" -e speaker_training_sent_emails.csv /tmp/registration.csv

    % python ./email_groups.py -g speaker -b ./speaker_training_speakers.email --subject="ADASS 2020 Speaker Training Sessions" -e speaker_training_sent_emails.csv /tmp/registration.csv > new_emails.csv

    % cat new_emails.csv >> speaker_training_sent_emails.csv


Make sure that you then remove your email address and the duplicate header from ```speaker_training_sent_emails.csv```.