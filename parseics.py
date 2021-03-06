"""
Parse the ics calendar generated by pretalx to remove poster contributions.
"""
from ics import Calendar, Event
import requests

url = "https://schedule.adass2020.es/adass2020/schedule/export/schedule.ics"
cal = Calendar(requests.get(url).text)

c = Calendar()
e = Event()
for ev in cal.events:
    if ev.location != "Posters":
        c.events.add(ev)

with open('talks_schedule.ics', 'w') as f:
    f.write(str(c))
