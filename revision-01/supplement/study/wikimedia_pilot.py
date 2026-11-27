"""Bounded replay of two public CDN trace prefixes; keep only latency and time."""
import argparse
from decimal import Decimal
import gzip
import hashlib
from io import BytesIO
import json
from pathlib import Path
from urllib.request import Request, urlopen

from windows import evaluate

URL = 'https://analytics.wikimedia.org/published/datasets/caching/2019/text/cache-t-{:02}.gz'
DAYS = (0, 14)
N = 9600


def download(day):
    req = Request(URL.format(day), headers={'Range':'bytes=0-1048575','User-Agent':'LatencyResearch/1.0'})
    with urlopen(req, timeout=30) as response:
        raw = response.read(1048576)
    stamps, latency = [], []
    with gzip.GzipFile(fileobj=BytesIO(raw)) as f:
        fields = f.readline().decode().strip().split('\t')
        clock, ttfb = fields.index('relative_unix'), fields.index('time_firstbyte')
        for _ in range(N):
            parts = f.readline().decode().strip().split('\t')
            stamps.append(int(parts[clock]))
            ns = Decimal(parts[ttfb]) * 10**9
            if ns < 0 or ns != int(ns):
                raise ValueError('Unexpected time precision or negative time')
            latency.append(int(ns))
    return dict(source=URL.format(day), prefix_sha256=hashlib.sha256(raw).hexdigest(),
                prefix_bytes=len(raw), seconds=stamps, latency_ns=latency)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--from-dir', type=Path)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    records = []
    for day in DAYS:
        filename=f'day-{day:02}-inputs.json'
        data = (json.loads((args.from_dir/filename).read_text()) if args.from_dir else download(day))
        (args.out/filename).write_text(json.dumps(data),encoding='ascii')
        stamps=data['seconds']
        # Preserve the order within each one-second timestamp. Retain only whole blocks.
        inversions=sum(a>b for a,b in zip(stamps, stamps[1:]))
        order=sorted(range(N),key=stamps.__getitem__)
        values=[data['latency_ns'][i] for i in order]
        for q_ms in (2,8,24):
            tests=[evaluate(values[i:i+48],6,q_ms*10**6) for i in range(0,N,48)]
            (args.out/f'day-{day:02}-q{q_ms}-decisions.json').write_text(json.dumps(tests),encoding='ascii')
            records.append(dict(day=day, batch_size=48, window=6, quantum_ms=q_ms,
                groups=len(tests), certified=sum(t['certified'] for t in tests),
                coarse=sum(t['coarse_certified'] for t in tests),
                wrong=sum(t['regret']>0 for t in tests),
                certified_wrong=sum(t['certified'] and t['regret']>0 for t in tests),
                original_timestamp_inversions=inversions,
                first_second=min(stamps),last_second=max(stamps)))
    (args.out/'summary.json').write_text(json.dumps(records,indent=2),encoding='ascii')
    for r in records:
        print(r)


if __name__=='__main__':
    main()
