"""Recheck saved deployments independently; run after experiments or extraction."""
from pathlib import Path
import hashlib
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.dataset_generator import load_instance, dzn_digests
from src.optimization import verify

ROOT=Path(__file__).resolve().parents[1]


def main():
    checked=0
    stale=set()
    groups=[('results/benchmark/benchmark.json',ROOT/'data'),
            ('results/accuracy/accuracy.json',ROOT/'results/accuracy/instances'),
            ('results/coverage_sweep/coverage_sweep.json',ROOT/'results/coverage_sweep/instances')]
    for filename,folder in groups:
        rows=json.loads((ROOT/filename).read_text(encoding='utf-8'))
        for r in rows:
            meta=load_instance(folder/(r['instance']+'.dzn'))
            assert r['instance_sha256']==meta['dzn_sha256']
            if r.get('model_sha256') and r['model_sha256'] not in dzn_digests((ROOT/'src/radio_coverage.mzn').read_bytes()):
                stale.add(filename)
            if r['verified']:
                actual=verify(meta,r['x'],r['objective'])
                assert actual['selected']==r['selected']
                assert actual['covered_points']==r['covered_points']
                assert actual['critical_support']==r['critical_support']
                checked+=1
    print(f'Independently revalidated {checked} saved experiment deployments.')
    for filename in sorted(stale):
        print(f'WARNING: {filename} was produced by a different version of radio_coverage.mzn '
              '(solutions still re-checked above; re-run the experiment for exact provenance).')


if __name__=='__main__': main()
