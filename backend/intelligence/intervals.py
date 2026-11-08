"""Empirical positive-spending bands; separate calibration, no joint cash guarantee."""
import hashlib
import json
from pathlib import Path
import numpy as np

POLICY = Path(__file__).with_name('interval_calibration.json')


def context(history):
    values=history.spending.to_numpy(float)
    positive=history[history.spending>0]
    zero=float(np.mean(values==0))
    concentration=float(positive.date.dt.day.value_counts().head(6).sum()/len(positive)) if len(positive) else 0.
    group='calendar_supported' if zero>=.68 and concentration>=.9 else 'irregular_sparse' if zero>=.68 else 'frequent'
    scale=max(1.,float(np.median(positive.spending))) if len(positive) else 1.
    return group,scale


def policy_for(history,model_dir):
    if not POLICY.exists():return None
    policy=json.loads(POLICY.read_text())
    for name,value in policy['model_sha256'].items():
        path=Path(model_dir)/f'{name}.txt'
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=value:return None
    group,scale=context(history)
    params=policy['groups'].get(group)
    if not params:return None
    return params['q'],scale,group


def positive_upper(upper,point,q,scale):
    return round(max(point,0.,upper+q*scale),2)


def positive_bounds(lower,upper,point,q,scale):
    delta=max(0.,q)*scale
    return round(max(0.,min(point,lower-delta)),2),positive_upper(upper,point,max(0.,q),scale)
