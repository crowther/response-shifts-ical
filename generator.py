# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "icalendar>=6.3.2",
# ]
# ///
import csv
import datetime
import argparse
import sys
import icalendar
from typing import Optional

TEMPLATE_CYCLE_LENGTH = 140
START_DATE = datetime.date(2018, 1, 1)
EXCLUDED_SHIFT_CODES = {'R', 'SP'}

def shift_code_to_name(shift_code: str) -> str:
    match shift_code:
        case 'E': return 'Early'
        case 'L': return 'Late'
        case 'N': return 'Night'
        case 'SN': return 'Super Noon'
        case _: raise ValueError(f'Unknown shift code: {shift_code}')

def shift_code_to_times(shift_code: str) -> tuple[datetime.time, datetime.time]:
    match shift_code:
        case 'E': return (datetime.time(hour=7, minute=0), datetime.time(hour=16, minute=0))
        case 'L': return (datetime.time(hour=15, minute=0), datetime.time(hour=0, minute=0))
        case 'N': return (datetime.time(hour=22, minute=0), datetime.time(hour=7, minute=0))
        case 'SN': return (datetime.time(hour=16, minute=0), datetime.time(hour=3, minute=0))
        case _: raise ValueError(f'Unknown shift code: {shift_code}')

def calculate_shift_end(start_date: datetime.date, start_time: datetime.time, end_time: datetime.time) -> datetime.datetime:
    if end_time <= start_time:
        return datetime.datetime.combine(start_date + datetime.timedelta(days=1), end_time)
    else:
        return datetime.datetime.combine(start_date, end_time)

def generate_calendar(
    template_file: str,
    date_from: datetime.date,
    date_to: datetime.date,
    selected_shifts: Optional[set[int]] = None
) -> icalendar.Calendar:
    """
    Generate an iCalendar object from a shift template.

    Args:
        template_file: Path to the CSV template file
        date_from: Start date for calendar generation
        date_to: End date for calendar generation
        selected_shifts: Optional set of shift numbers to include (e.g., {1, 3, 5})
                        If None, all shifts are included

    Returns:
        icalendar.Calendar object containing shift events

    Raises:
        ValueError: If date_from > date_to
        FileNotFoundError: If template_file doesn't exist
    """
    if date_from > date_to:
        raise ValueError(f'Start date ({date_from}) must be before the end date ({date_to})')

    days_diff: int = (date_from - START_DATE).days
    current_date: datetime.date = date_from
    offset: int = (days_diff % TEMPLATE_CYCLE_LENGTH) + 1

    cal: icalendar.Calendar = icalendar.Calendar()

    with open(template_file) as f:
        reader = csv.DictReader(f)
        shift_templates: list[dict[int, str]] = [
            {int(k): v for k, v in s.items() if v not in EXCLUDED_SHIFT_CODES}
            for s in list(reader)
        ]

    while current_date < date_to:
        for shift_number, s in enumerate(shift_templates, start=1):
            if selected_shifts is not None and shift_number not in selected_shifts:
                continue

            shift_code: Optional[str] = s.get(offset)  # None when R/SP filtered out
            if shift_code:
                times: tuple[datetime.time, datetime.time] = shift_code_to_times(shift_code)
                shift_start: datetime.datetime = datetime.datetime.combine(current_date, times[0])
                shift_end: datetime.datetime = calculate_shift_end(current_date, times[0], times[1])
                shift_type: str = shift_code_to_name(shift_code)

                event: icalendar.Event = icalendar.Event()
                event.add('UID', f'shift-{shift_number}-{current_date.isoformat()}@shift-calendar-generator')
                event.add('DTSTAMP', datetime.datetime.now(datetime.timezone.utc))
                event.add('SUMMARY', f'Shift {shift_number} - {shift_type}')
                event.add('DTSTART', shift_start)
                event.add('DTEND', shift_end)
                event.add('X-SHIFT-NUMBER', str(shift_number))
                event.add('X-SHIFT-TYPE', shift_type)
                cal.add_component(event)

        offset = (offset % TEMPLATE_CYCLE_LENGTH) + 1
        current_date += datetime.timedelta(days=1)

    return cal

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="Shift iCal Generator",
        description='generate an iCal calendar based on a template file')

    parser.add_argument('-of', '--output-file', type=str, default='shifts.ics', dest='output_file')
    parser.add_argument('-tf', '--template-file', type=str, default='template.csv', dest='template_file')
    parser.add_argument('-s', '--shifts', type=str, help='Comma-separated shift numbers to include (e.g., "1,3,5"). If not specified, all shifts are included.', dest='shifts')
    parser.add_argument('-f', '--from', type=datetime.date.fromisoformat, default=datetime.date.today(), dest='date_from')
    parser.add_argument('-t', '--to', type=datetime.date.fromisoformat, default=(datetime.date.today() + datetime.timedelta(weeks=52)), dest='date_to')

    return parser.parse_args()

def main() -> None:
    args: argparse.Namespace = parse_args()

    template_file: str = args.template_file
    output_file: str = args.output_file
    date_from: datetime.date = args.date_from
    date_to: datetime.date = args.date_to

    # Parse shift filter if provided
    selected_shifts: Optional[set[int]] = None
    if args.shifts:
        try:
            selected_shifts = {int(s.strip()) for s in args.shifts.split(',')}
        except ValueError:
            print(f'Invalid shift numbers: {args.shifts}. Must be comma-separated integers.', file=sys.stderr)
            sys.exit(1)

        # Validate shift numbers are in valid range (1-5)
        invalid_shifts = {s for s in selected_shifts if s < 1 or s > 5}
        if invalid_shifts:
            print(f'Error: Invalid shift numbers: {sorted(invalid_shifts)}. Valid shifts are 1-5.', file=sys.stderr)
            sys.exit(1)

    try:
        cal = generate_calendar(template_file, date_from, date_to, selected_shifts)

        with open(output_file, 'wb') as f:
            f.write(cal.to_ical())

        print(f'Calendar written to {output_file}')
    except ValueError as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f'Error: Template file "{template_file}" not found', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
