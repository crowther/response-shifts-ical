import csv
import datetime
import argparse
import icalendar
import os

START_DATE = datetime.date(2018, 1, 1)
START_OFFSET = 71

def shift_code_to_name(shift_code):
    match shift_code:
        case 'E': return 'Early'
        case 'L': return 'Late'
        case 'N': return 'Night'
        case 'SN': return 'Super Noon'

def shift_code_to_times(shift_code):
    match shift_code:
        case 'E': return (datetime.time(hour=7, minute=0), datetime.time(hour=16, minute=0))
        case 'L': return (datetime.time(hour=15, minute=0), datetime.time(hour=0, minute=0))
        case 'N': return (datetime.time(hour=22, minute=0), datetime.time(hour=7, minute=0))
        case 'SN': return (datetime.time(hour=16, minute=0), datetime.time(hour=3, minute=0))

with open('template.csv') as f:
    reader = csv.DictReader(f)
    shift_templates = list(reader)

for i, s in enumerate(shift_templates):
    shift_templates[i] = {int(k): v for k, v in s.items() if v != 'R' and v != 'SP'}

def parse_args():
    parser = argparse.ArgumentParser(
        prog="Shift iCal Generator",
        description='generate an iCal calendar based on template.csv')
    
    parser.add_argument('-f', '--from', type=datetime.date.fromisoformat, default=datetime.date.today(), dest='date_from')
    parser.add_argument('-t', '--to', type=datetime.date.fromisoformat, default=(datetime.date.today() + datetime.timedelta(weeks=52)), dest='date_to')

    return parser.parse_args()

args = parse_args()

date_from, date_to = args.date_from, args.date_to
current_date = START_DATE
offset = START_OFFSET

cal = icalendar.Calendar()

while current_date < date_to:
    for i, s in enumerate(shift_templates):
        shift_code = s.get(offset)
        if shift_code and (date_from <= current_date <= date_to):
            times = shift_code_to_times(shift_code)
            shift_start = datetime.datetime.combine(current_date, times[0])

            if shift_code == 'L' or shift_code == 'N' or shift_code == 'SN':
                shift_end = datetime.datetime.combine(current_date + datetime.timedelta(days=1), times[1])
            else:
                shift_end = datetime.datetime.combine(current_date, times[1])
        
            name = shift_code_to_name(shift_code)

            event = icalendar.Event()
            event.add('summary', f'Shift {i + 1} - {name}')
            event.add('dtstart', shift_start)
            event.add('dtend', shift_end)
            event.add('X-SHIFT', str(i + 1))
            event.add('X-SHIFT-NAME', name)
            cal.add_component(event)

    if offset == 140:
        offset = 1
    else:
        offset += 1

    current_date += datetime.timedelta(days=1)

with open(('response.ics'), 'wb') as f:
    f.write(cal.to_ical())
