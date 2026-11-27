"""Replay the study from its distributed inputs and compare deterministic outputs."""
import argparse
import filecmp
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def run(args):
    subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, check=True)


def matches(first, second):
    if not filecmp.cmp(first, second, shallow=False):
        raise ValueError(f'Replay mismatch: {first.name}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    out = parser.parse_args().out.resolve()
    if not __debug__:
        parser.error('Use Python without optimization so verification assertions run.')
    out.mkdir(parents=True, exist_ok=False)
    run(['run.py', '--out', out/'simulation'])
    for filename in ('hardware.jsonl', 'network.jsonl', 'windows.jsonl'):
        matches(ROOT/'runs/01'/filename, out/'simulation'/filename)
    recorded = json.loads((ROOT/'runs/01/summary.json').read_text())
    actual = json.loads((out/'simulation/summary.json').read_text())
    for key in ('hardware','network','windows'):
        if actual[key] != recorded[key]:
            raise ValueError(f'Numerical mismatch: {key}')
    run(['wikimedia-followup/analyze.py', '--out', out/'cdn'])
    for filename in ('decisions.jsonl', 'cases.json', 'summary.json'):
        matches(ROOT/'wikimedia-followup/results'/filename, out/'cdn'/filename)
    print('PASS: three simulator traces and three deterministic CDN outputs matched.')


if __name__ == '__main__':
    main()
