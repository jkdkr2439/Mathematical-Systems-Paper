"""Apply frozen rules, generate case records, and time hot-path decisions offline."""
from collections import Counter, defaultdict
from itertools import accumulate
from time import perf_counter_ns
import hashlib
import json
from pathlib import Path
import platform
from statistics import median

from fetch import ROOT, DESIGN, PLAN, LOCK

Q=PLAN['quantum_ns']
W=PLAN['width']
LIMITS=PLAN['tolerances_ns']


def rounded(values):
    return [((2*x+Q)//(2*Q))*Q for x in values]


def window_scores(values):
    prefix=list(accumulate(values,initial=0))
    return [b-a for a,b in zip(prefix,prefix[W:])]


def select(values, check=False):
    scores=window_scores(values)
    best=max(scores)
    i=scores.index(best)
    if not check:
        return i
    margin=min(best-score-Q*min(W,abs(i-j)) for j,score in enumerate(scores) if j!=i)
    return i,margin


def decision(values):
    z=rounded(values)
    i,margin=select(z,True)
    scores=window_scores(values)
    best=max(scores)
    opts=[j for j,s in enumerate(scores) if s==best]
    j=min(opts,key=lambda j:(abs(i-j),j))
    reported=window_scores(z)
    loose=min(reported[i]-s-W*Q for j,s in enumerate(reported) if j!=i)
    regret=best-scores[i]
    # Independent direct check at the realization least favorable to the chosen interval.
    worst=[v-Q//2 if i<=k<i+W else v+Q//2 for k,v in enumerate(z)]
    corner=[sum(worst[k:k+W]) for k in range(len(worst)-W+1)]
    assert margin==corner[i]-max(v for k,v in enumerate(corner) if k!=i)
    assert regret<=max(0,-margin) and loose<=margin
    return dict(selected=i, reference=j, optimal_count=len(opts), overlap=max(0,W-abs(i-j)),
                margin_ns=margin, coarse_margin_ns=loose,regret_ns=regret)


def blocks():
    for day in PLAN['pilot_days']+PLAN['days']:
        if day in PLAN['pilot_days']:
            data=json.loads((ROOT.parent/f'runs/wikimedia-pilot-01/day-{day:02}-inputs.json').read_text())
            slices={0:list(zip(data['seconds'],data['latency_ns']))}
            split='pilot'
        else:
            data=json.loads((ROOT/f'inputs/day-{day:02}.json').read_text())
            assert data['design_sha256']==LOCK
            slices={int(h):r for h,r in data['slices'].items()}
            split='holdout'
        for hour,rows in slices.items():
            assert len(rows)==PLAN['records_per_stratum'] and all(a[0]<=b[0] for a,b in zip(rows,rows[1:]))
            for k in range(0,len(rows),48):
                batch=rows[k:k+48]
                t,x=zip(*batch)
                yield dict(split=split,day=day,hour=hour,group=k//48),t,x


def aggregate(rows):
    r=[a['regret_ns'] for a in rows if a['regret_ns']>0]
    return dict(groups=len(rows),wrong=len(r),regret_median_wrong_ns=median(r) if r else 0,
                regret_max_ns=max(r,default=0),overlap_wrong=dict(sorted(Counter(
                    a['overlap'] for a in rows if a['regret_ns']>0).items())),
                thresholds={str(d):dict(certified=sum(a['margin_ns']>=-d for a in rows),
                    coarse=sum(a['coarse_margin_ns']>=-d for a in rows),
                    actual_over=sum(a['regret_ns']>d for a in rows),
                    certified_over=sum(a['margin_ns']>=-d and a['regret_ns']>d for a in rows)) for d in LIMITS})


def example_set(rows):
    chosen=[]
    for split in ['pilot','holdout']:
        wrong=[r for r in rows if r['split']==split and r['regret_ns']>0]
        criteria=[('smallest positive regret',lambda r:r['regret_ns']),
                  ('largest regret',lambda r:-r['regret_ns']),
                  ('least overlap',lambda r:r['overlap'])]
        for reason,key in criteria:
            row=min((r for r in wrong if r not in [v for _,v in chosen]),key=key)
            chosen.append((reason,row))
    for reason,cert in [('certified optimum',True),('uncertified optimum',False)]:
        row=next(r for r in rows if r['split']=='holdout' and r['regret_ns']==0 and (r['margin_ns']>=0)==cert)
        chosen.append((reason,row))
    return chosen


def benchmark(batches):
    def pass_once(check):
        start=perf_counter_ns()
        for z in batches:
            select(z,check)
        return (perf_counter_ns()-start)/len(batches)
    pass_once(False)
    pass_once(True)
    pairs=[]
    for i in range(9):
        order=[False,True] if i%2==0 else [True,False]
        times={k:pass_once(k) for k in order}
        pairs.append([times[False],times[True]])
    return dict(python=platform.python_version(),platform=platform.system(),processor=platform.machine(),
                unit='ns per batch of 48, pre-rounded, elapsed, no I/O',
                pairs=pairs, baseline_median=median(a for a,b in pairs),
                certified_median=median(b for a,b in pairs),
                paired_extra_median=median(b-a for a,b in pairs))


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--out',required=True,type=Path)
    out=p.parse_args().out
    out.mkdir(parents=True,exist_ok=False)
    rows=[]; data={}; speed=[]; strata=defaultdict(list)
    for meta,t,x in blocks():
        row=dict(**meta,**decision(x))
        rows.append(row)
        key=(row['day'],row['hour'],row['group'])
        data[key]=[t,x]
        if row['split']=='holdout':
            speed.append(rounded(x))
            strata[key[:2]].append(row)
    summary={s:aggregate([r for r in rows if r['split']==s]) for s in ('pilot','holdout')}
    t=summary['pilot']['thresholds']['0']
    assert (t['certified'],t['coarse'],summary['pilot']['wrong'])==(204,186,103)
    summary['strata']={f'{d:02}/{h:02}':aggregate(v) for (d,h),v in sorted(strata.items())}
    summary['design_sha256']=hashlib.sha256(DESIGN.read_bytes()).hexdigest()
    assert summary['design_sha256']==LOCK
    summary['input_sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((ROOT/'inputs').glob('day-*.json'))}
    selected=[]
    for reason,r in example_set(rows):
        times,values=data[(r['day'],r['hour'],r['group'])]
        selected.append(dict(reason=reason,**r,seconds=times,latency_ns=values))
    for filename,value in [('summary',summary),('cases',selected),('benchmark',benchmark(speed))]:
        (out/(filename+'.json')).write_text(json.dumps(value,indent=2),encoding='utf-8')
    with (out/'decisions.jsonl').open('w',encoding='utf-8',newline='\n') as f:
        for row in rows:
            f.write(json.dumps(row)+'\n')
    print(json.dumps(summary['holdout']))


if __name__=='__main__':
    main()
