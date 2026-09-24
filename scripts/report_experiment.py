"""Verify a saved experiment by replaying its ledger and write a local report.

No model calls. Reports only checkpoints already captured by the runner.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.engine import Account, INITIAL, rule_decision


def verify(data):
    accounts = {name: Account() for name in ('selected', 'buy_hold', 'rule')}
    bars = data['candles']
    assert len(data['events']) == len(data['points'])
    for index, (event, point) in enumerate(zip(data['events'], data['points'])):
        cursor = data['warmup'] + index
        bar = bars[cursor]
        assert event['observed_at'] < bar['time'] == event['time']
        assert point['time'] == bar['time'] + 900_000 - 1
        fill = accounts['selected'].rebalance(event['target'], bar['open'])
        assert fill['side'] == event['side']
        for key in ('quantity', 'price', 'fee'):
            assert abs(fill[key] - event[key]) < 1e-7, (index, key)
        if index == 0:
            accounts['buy_hold'].rebalance(100, bar['open'])
        accounts['rule'].rebalance(rule_decision(bars[:cursor])['target'], bar['open'])
        for name, account in accounts.items():
            value = account.snapshot(bar['close'])
            assert abs(value['equity'] - point['equity' if name == 'selected' else name]) < 1e-7
        for key in ('equity', 'fees', 'max_drawdown'):
            assert abs(accounts['selected'].snapshot(bar['close'])[key] - point[key]) < 1e-7
    return True


def render(folder):
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    status_path = folder / 'status.json'
    status = json.loads(status_path.read_text(encoding='utf-8')) if status_path.exists() else {}
    lines = ['# Jev 7일·30일 실험', '',
             f"실험 기간: {manifest['start']} ~ {manifest['end_exclusive']} UTC (종료일 제외).", '',
             f"상태: {status.get('status', 'starting')} · 판단 {status.get('decisions', 0):,}/2,880회 · 요청 {status.get('calls', 0):,}회.", '',
             '동일 계좌의 7일 중간 결과와 30일 최종 결과입니다. 서로 독립된 실험이 아닙니다.', '',
             '초기 자금 10,000 USDT · 15분봉 · 편도 수수료 0.10% · 슬리피지 0.05%.', '']
    for days in (7, 30):
        path = folder / f'day-{days}-summary.json'
        if not path.exists():
            lines += [f'## {days}일 결과', '', '아직 이 시점까지 완료되지 않았습니다.', '']
            continue
        summary = json.loads(path.read_text(encoding='utf-8'))
        data = json.loads((folder / f'day-{days}-run.json').read_text(encoding='utf-8'))
        assert len(data['events']) == days * 96 == summary['decisions']
        verify(data)
        lines += [f'## {days}일 결과', '',
                  f"판단 {summary['decisions']:,}회 · API 요청 {summary['api_calls']:,}회 · 체결/계좌 재계산 검증 통과.", '',
                  '| 전략 | 평가 자산 (USDT) | 수익률 | 최대 낙폭 | 수수료 | 거래 수 |',
                  '| --- | ---: | ---: | ---: | ---: | ---: |']
        for key, label in [('selected', 'Jev'), ('rule', '규칙'), ('buy_hold', '매수 후 보유'), ('cash', '현금')]:
            m = summary['metrics'][key]
            lines.append(f"| {label} | {m['equity']:,.2f} | {m['return_pct']:+.2f}% | {m['max_drawdown']*100:.2f}% | {m['fees']:.2f} | {m['trades']} |")
        lines += ['', f"평균 현금 비중(각 봉 종가 기준): {summary['mean_cash_allocation_pct']:.2f}%.",
                  f"목표 BTC 비중 선택 횟수: {summary['target_counts']}.",
                  f"평균 추론 시간: {summary['mean_latency_ms']:.0f} ms.", '',
                  f'[판단 원본](day-{days}-run.json) · [요약 수치](day-{days}-summary.json)', '']
    lines += ['## 해석 범위', '',
              '미청산 BTC를 포함한 평가 자산이며 마지막 자동 청산은 없습니다. 낙폭은 봉 종가 기준입니다.',
              '과거 추론 지연에 따른 체결 지연은 재현하지 않으며, 모델의 과거 시장 학습 가능성도 남아 있습니다.',
              '한 기간의 결과를 다른 시장 국면이나 실시간 수익성으로 일반화할 수 없습니다.', '',
              f"보고서 생성: {datetime.now(timezone.utc).isoformat()}", '']
    (folder / 'REPORT.ko.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path, nargs='?', default=ROOT / 'data/experiments/2025-01')
    parser.add_argument('--watch', action='store_true', help='Update reports until this batch finishes or stops; makes no API calls')
    args = parser.parse_args()
    while True:
        render(args.folder)
        status_path = args.folder / 'status.json'
        status = json.loads(status_path.read_text(encoding='utf-8')) if status_path.exists() else {}
        if not args.watch or status.get('status') in ('complete', 'stopped'):
            break
        if status and time.time() - status['updated_at_unix'] > 300:
            with (args.folder / 'REPORT.ko.md').open('a', encoding='utf-8') as report:
                report.write('\n5분 이상 진행 상태 갱신이 없습니다. 실행 프로세스를 확인하세요.\n')
            break
        time.sleep(30)
