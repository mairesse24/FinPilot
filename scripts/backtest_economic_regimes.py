"""Real vintage replay. No current-revised fallback and no fabricated labels."""
import json
import os
from dotenv import dotenv_values
from backend.intelligence.economic_data import ROOT,refresh,cached,CACHE
from backend.intelligence.regimes import classify

PERIODS={'2008-10-31':'financial crisis','2009-03-31':'financial crisis trough period',
         '2020-04-30':'COVID shock','2022-06-30':'inflation acceleration',
         '2023-07-31':'monetary tightening','2017-06-30':'comparison expansion period'}


def main():
    config={**dotenv_values(ROOT/'.env'),**dotenv_values(ROOT/'backend/.env'),**os.environ}
    rows=[]
    # Preserve current display pointer; historical snapshots remain separately versioned.
    pointer=CACHE/'latest.json';original=pointer.read_bytes() if pointer.exists() else None
    try:
        for as_of,description in PERIODS.items():
            snapshot=cached(as_of)
            if not snapshot['series'] and config.get('FRED_API_KEY'):
                snapshot=refresh(as_of,config.get('FRED_API_KEY'),include_market=False)
            result=classify(snapshot,as_of,historical=True)
            rows.append({'period':description,**result})
            print(as_of,result['status'],result['evidence_quality'],flush=True)
    finally:
        if original is not None:pointer.write_bytes(original)
    folder=ROOT/'reports/economic_intelligence';folder.mkdir(parents=True,exist_ok=True)
    (folder/'historical_regimes.json').write_text(json.dumps(rows,indent=2,allow_nan=False))


if __name__=='__main__':main()
