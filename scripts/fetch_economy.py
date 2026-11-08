"""Explicit public FRED CSV refresh for the intelligence research cache; no API key."""
import argparse
from datetime import datetime, timezone
from io import StringIO
import json
from urllib.request import Request, urlopen
import pandas as pd
from backend.intelligence.data import ROOT

SERIES = ('CPIAUCSL', 'UNRATE', 'FEDFUNDS', 'SP500')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(ROOT / 'data/economy'))
    args = parser.parse_args()
    from pathlib import Path
    folder = Path(args.output)
    folder.mkdir(parents=True, exist_ok=True)
    frames, provenance = [], {}
    for name in SERIES:
        url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={name}&cosd=2000-01-01'
        request = Request(url, headers={'User-Agent': 'FinPilot-HackUTD-research/1.0'})
        with urlopen(request, timeout=25) as response:
            raw = response.read().decode('utf-8-sig')
        frame = pd.read_csv(StringIO(raw), na_values=['.'])
        frame.columns = ['date', name]
        frame['date'] = pd.to_datetime(frame.date)
        frame[name] = pd.to_numeric(frame[name], errors='coerce')
        frames.append(frame.set_index('date'))
        provenance[name] = {'url': url, 'last_observation': str(frame.dropna().date.max().date()),
                            'source_page': f'https://fred.stlouisfed.org/series/{name}'}
        print(f'{name}: {len(frame)} rows', flush=True)
    combined = pd.concat(frames, axis=1, sort=True).sort_index()
    combined.to_csv(folder / 'fred.csv', index_label='date')
    metadata = {'retrieved_at': datetime.now(timezone.utc).isoformat(), 'series': provenance,
                'vintage': 'current_revised; not point-in-time', 'synthetic': False}
    (folder / 'provenance.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(f'Saved research cache to {folder}. Review FRED/SP500 data-use terms before redistribution.')


if __name__ == '__main__':
    main()
