"""Append and audit real Foldit observations. No synthetic play data."""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIELDS = 'timestamp puzzle action before after seconds rank players screenshot note'.split()


def validate(row):
    if float(row['seconds']) <= 0:
        raise ValueError('seconds must be positive')
    if row.get('rank') and row.get('players'):
        if not 1 <= int(row['rank']) <= int(row['players']):
            raise ValueError('rank must be within 1..players')
    return float(row['after']) - float(row['before'])


def analyze(path):
    with path.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    groups = {}
    for row in rows:
        gain = validate(row)
        key = row['puzzle'] + ' / ' + row['action']
        entry = groups.setdefault(key, {'trials': 0, 'gain': 0, 'seconds': 0, 'missing_screenshots': 0})
        entry['trials'] += 1
        entry['gain'] += gain
        entry['seconds'] += float(row['seconds'])
        entry['missing_screenshots'] += int(not row['screenshot'] or not Path(row['screenshot']).is_file())
    for entry in groups.values():
        entry['gain_per_minute'] = entry['gain'] * 60 / entry['seconds']
    return {'status': 'observed' if rows else 'awaiting_real_play', 'events': len(rows), 'groups': groups}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    add = sub.add_parser('add')
    for name in ['puzzle', 'action', 'before', 'after', 'seconds']:
        add.add_argument('--' + name, required=True)
    for name in ['rank', 'players', 'screenshot', 'note']:
        add.add_argument('--' + name, default='')
    sub.add_parser('analyze')
    args = parser.parse_args()
    path = ROOT / 'data' / 'events.csv'
    if args.command == 'add':
        row = {key: getattr(args, key, '') for key in FIELDS}
        row['timestamp'] = datetime.now(timezone.utc).isoformat()
        validate(row)
        with path.open('a', encoding='utf-8', newline='') as stream:
            csv.DictWriter(stream, FIELDS).writerow(row)
    else:
        print(json.dumps(analyze(path), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
