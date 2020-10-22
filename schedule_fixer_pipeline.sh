#!/bin/bash
set -ex

# Step 0: use the ADASS tools dir as wd and make sure that the Python env 
# is in the PATH.
cd /root/adass_tools
export PATH=/root/env/bin:$PATH

# Step 1: copy the original HTML export to a staging area
/usr/bin/rsync -av --delete /var/pretalx/data/htmlexport/adass2020/ /tmp/adass2020/

# Step 2: fix the index.html file with the info from the database (PIDs etc)
/root/env/bin/python3 ./fix_titles_authors.py -e adass2020 /tmp/adass2020 -i /tmp/index.html -t /tmp/talk.html -s /tmp/speaker.html

# Step 3: copy the modified index.html file to staging
/bin/mv /tmp/index.html /tmp/adass2020/adass2020/schedule/index.html
/bin/mv /tmp/talk.html /tmp/adass2020/adass2020/talk/index.html
/bin/mv /tmp/speaker.html /tmp/adass2020/adass2020/speaker/index.html

# Step 4: fix all calendar files to use UTC instead of CEST/CET/Madrid time
./fix_calendars.sh -r /tmp/adass2020 -e adass2020

# Step 5: Copy staging to prod
/usr/bin/rsync -av --delete /tmp/adass2020/ /var/www/schedule/
