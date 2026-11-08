"""Explicit real-data refresh; no secret values printed."""
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import dotenv_values
from pathlib import Path
import os
from backend.intelligence.economic_data import refresh,ROOT


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--as-of',default=datetime.now(ZoneInfo('America/Chicago')).date().isoformat())
    parser.add_argument('--fred-only',action='store_true');args=parser.parse_args()
    config={**dotenv_values(ROOT/'.env'),**dotenv_values(ROOT/'backend/.env'),**os.environ}
    result=refresh(args.as_of,config.get('FRED_API_KEY'),not args.fred_only)
    print('Snapshot:',args.as_of,'available:',list(result['series']),'unavailable:',result['errors'])


if __name__=='__main__':main()
