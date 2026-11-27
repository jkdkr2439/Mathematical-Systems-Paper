"""Extract only published second and TTFB from three time slices of each day."""
import gzip
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DESIGN = ROOT / 'design.json'
PLAN = json.loads(DESIGN.read_text())
LOCK = '0ea1da41d2671714240ee9ffc1bddd0cc04c2ccaafc8dfcc2c7d2fe98a342344'


def extract(day):
    url = f'https://analytics.wikimedia.org/published/datasets/caching/2019/text/cache-t-{day:02}.gz'
    destination = ROOT/'inputs'/f'day-{day:02}.json'
    if destination.exists():
        saved=json.loads(destination.read_text())
        assert saved['design_sha256']==LOCK and all(len(a)==PLAN['records_per_stratum'] for a in saved['slices'].values())
        return
    slices = {hour:[] for hour in PLAN['hours']}
    req = Request(url,headers={'User-Agent':'LatencyWindowResearch/1.0','Accept-Encoding':'identity'})
    with urlopen(req,timeout=75) as src, gzip.GzipFile(fileobj=src) as data:
        if src.status!=200:
            raise ValueError(f'Expected complete stream for day {day}, got {src.status}')
        header=data.readline().strip().split(b'\t')
        ti,vi=header.index(b'relative_unix'),header.index(b'time_firstbyte')
        hour_index=0
        first_row={}
        for i,line in enumerate(data,1):
            hour=PLAN['hours'][hour_index]
            parts=line.rstrip(b'\n').split(b'\t')
            second=int(parts[ti])
            if second < day*86400 + hour*3600:
                continue
            rows=slices[hour]
            if not rows:
                if second >= day*86400 + (hour+1)*3600:
                    raise ValueError('Missing requested hour')
                first_row[hour]=i
            elif second < rows[-1][0]:
                raise ValueError('Non-monotone times within slice')
            ns=Decimal(parts[vi].decode())*10**9
            if ns!=int(ns) or ns<0:
                raise ValueError('Bad latency')
            rows.append((second,int(ns)))
            if len(rows)==PLAN['records_per_stratum']:
                hour_index+=1
                if hour_index==len(slices):
                    break
        if hour_index!=len(slices):
            raise ValueError('Short source file')
        receipt=dict(source=url,design_sha256=LOCK,etag=src.headers.get('ETag'),
                     source_bytes=src.headers.get('Content-Length'),first_row=first_row,slices=slices)
    tmp=destination.with_suffix('.tmp')
    tmp.write_text(json.dumps(receipt,separators=(',',':')),encoding='ascii')
    tmp.replace(destination)
    print(f'Day {day} extracted and checked',flush=True)


if __name__=='__main__':
    assert hashlib.sha256(DESIGN.read_bytes()).hexdigest()==LOCK
    (ROOT/'inputs').mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(extract,PLAN['days']))
