"""Run the four simulator-backed experiments into a fresh output directory."""
import argparse
import hashlib
import json
import platform
from importlib.metadata import version
from pathlib import Path

import hardware
import network
import windows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    out = parser.parse_args().out
    out.mkdir(parents=True, exist_ok=False)
    summary = {'python':platform.python_version(), 'versions':{
        name:version(name) for name in ('simpy','pandapower','ns.py','pyrtl')}}
    for name, module in [('hardware', hardware), ('network', network), ('windows', windows)]:
        data, counts = module.run()
        target = out / (name+'.jsonl')
        with target.open('w', encoding='utf-8', newline='\n') as f:
            for row in data:
                f.write(json.dumps(row, separators=(',',':'))+'\n')
        summary[name] = counts
        summary[name+'_sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
        print(name,json.dumps(counts),flush=True)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
