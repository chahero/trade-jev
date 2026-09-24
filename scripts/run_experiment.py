"""Run a 30-day Jev experiment with a day-7 checkpoint (2,880-call cap).

Explicitly opt in with --jev. Resume uses the same saved account and budget;
provider failures stop the process without automatic retries.
"""
import argparse
from collections import Counter
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.app import NewRun, create_run, historical_step, public, read, save, safe_error
from server.engine import Account, INITIAL


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def metrics(run):
    result = {}
    for name, state in run['accounts'].items():
        snapshot = Account(**state).snapshot(run['price'])
        result[name] = {key: snapshot[key] for key in
                        ('equity', 'return_pct', 'max_drawdown', 'fees', 'trades', 'allocation', 'cash', 'btc')}
    result['cash'] = {'equity': INITIAL, 'return_pct': 0, 'max_drawdown': 0,
                      'fees': 0, 'trades': 0, 'allocation': 0, 'cash': INITIAL, 'btc': 0}
    return result


def checkpoint(folder, run, days):
    summary = {'days': days, 'run_id': run['id'], 'decisions': len(run['events']),
               'api_calls': run['calls'], 'start': run['start'],
               'end_exclusive': str(date.fromisoformat(run['start']) + timedelta(days=days)),
               'metrics': metrics(run),
               'target_counts': dict(Counter(str(e['target']) for e in run['events'])),
               'mean_cash_allocation_pct': sum(100 - p['allocation'] for p in run['points']) / len(run['points']),
               'mean_latency_ms': sum(e['latency_ms'] for e in run['events']) / len(run['events'])}
    write_json(folder / f'day-{days}-summary.json', summary)
    write_json(folder / f'day-{days}-run.json', public(run))
    print(json.dumps({'checkpoint': days, **summary}, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', type=date.fromisoformat, default=date(2025, 1, 1))
    parser.add_argument('--output', type=Path, default=ROOT / 'data/experiments/2025-01')
    parser.add_argument('--jev', action='store_true', help='Authorize new Jev requests within the 2,880-call limit')
    args = parser.parse_args()
    if not args.jev:
        parser.error('--jev is required to make paid model requests')
    folder = args.output.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    # OS lock releases on exit/crash and prevents two runners using this output.
    import msvcrt
    with (folder / 'runner.lock').open('a+b') as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b'0')
            lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        manifest_path = folder / 'manifest.json'
        source_hash = hashlib.sha256(b''.join((ROOT / p).read_bytes() for p in
            ('server/policy.py', 'server/engine.py', 'server/app.py', 'server/market.py'))).hexdigest()
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            if manifest['start'] != str(args.start) or manifest['source_sha256'] != source_hash:
                raise ValueError('Dates or implementation changed; use a new experiment folder')
            run = read(manifest['run_id'])
        else:
            config = NewRun(strategy='jev', start=args.start, end=args.start + timedelta(days=30), max_calls=2880)
            run = read(create_run(config)['id'])
            manifest = {'run_id': run['id'], 'start': str(args.start), 'end_exclusive': str(config.end),
                        'max_calls': 2880, 'checkpoints_days': [7, 30],
                        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
                        'source_sha256': source_hash, 'started_at_unix': time.time(),
                        'note': 'Day 7 is a nested checkpoint of the same 30-day account, not an independent trial.'}
            write_json(manifest_path, manifest)
        print(f"Run {run['id']}: {len(run['events'])}/2880 decisions, {run['calls']} calls", flush=True)
        while not run['finished']:
            try:
                historical_step(run)
            except Exception as exc:
                run['error'] = safe_error(exc)
                save(run)
                write_json(folder / 'status.json', {'status': 'stopped', 'run_id': run['id'],
                    'decisions': len(run['events']), 'calls': run['calls'], 'error_type': type(exc).__name__,
                    'updated_at_unix': time.time()})
                print(f"STOPPED: {type(exc).__name__}; decisions={len(run['events'])}, calls={run['calls']}", flush=True)
                return 1
            steps = len(run['events'])
            if steps in (672, 2880):
                checkpoint(folder, run, steps // 96)
            if steps % 24 == 0 or run['finished']:
                status = {'status': 'complete' if run['finished'] else 'running', 'run_id': run['id'],
                          'decisions': steps, 'calls': run['calls'], 'total': run['total'],
                          'updated_at_unix': time.time(), 'metrics': metrics(run)}
                write_json(folder / 'status.json', status)
                print(f"Progress {steps}/2880 | calls {run['calls']} | equity {run['account']['equity']:.2f}", flush=True)
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
