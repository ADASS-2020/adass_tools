#!/bin/bash
set -ex

usage() {
    echo "usage: fix_calendars.sh -r|--root HTML_EXPORT_DIR -e|--event EVENT_NAME"
}

if [ $# -ne 4 ]; then
    usage
    exit 2
fi

root=
event=
while [ "$1" != "" ]; do
    case $1 in
        -r | --root )           shift
                                root="$1"
                                ;;
        -e | --event )          shift
                                event="$1"
                                ;;
        -h | --help )           usage
                                exit
                                ;;
        * )                     usage
                                exit 1
    esac
    shift
done

find $root -type f -name \*.xml -exec sed -i.orig 's/\+01:00/\+00:00/g' {} \; -print
find $root -type f -name schedule.json -exec sed -i.orig 's/\+01:00/\+00:00/g' {} \; -print
find $root -type f -name \*.ics -exec sed -i.orig -E 's/;TZID=Europe\/Madrid:([0-9T]+)/:\1Z/g' {} \; -print
find $root -type f -name \*.ics -exec sed -i.orig 's/https:\/\/pretalx\./https:\/\/schedule\./g' {} \; -print

tmp_dir=$(mktemp -d -t ci-XXXXXXXXXX)
schedule_convert $root/$event/schedule/export/schedule.xml -l $tmp_dir https://schedule.adass2020.es
mv $tmp_dir/schedule.adass2020.es.ics $root/$event/schedule/export/schedule.ics
echo "please remove $tmp_dir"
