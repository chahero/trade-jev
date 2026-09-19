import {ArrowDownLeft,ArrowUpRight,Download} from 'lucide-react';
import {initial,money,stamp} from '../types';
import type {Account,Decision,Run} from '../types';

export function Metrics({account=initial}:{account?:Account}) {
  return <section className="metrics" aria-label="계좌 요약">
    <div><span>총 자산 (USDT)</span><strong>{money(account.equity)} <small>USDT</small></strong></div>
    <div><span>수익률</span><strong className={account.return_pct>0?'accent':account.return_pct<0?'negative':''}>{account.return_pct>0?'+':''}{money(account.return_pct)}%</strong></div>
    <div><span>최대 낙폭 (MDD)</span><strong>{money(account.max_drawdown*100)}%</strong></div>
    <div><span>거래 수수료</span><strong>{money(account.fees)} <small>USDT</small></strong></div>
  </section>;
}

export function DecisionPanel({run,decision,account}:{run:Run|null;decision:Decision|null;account:Account}) {
  const hasProb=decision && Object.keys(decision.probabilities).length>0;
  const live=run?.mode==='live';
  return <aside className="panel decision"><div className="panel-heading"><h2>현재 판단</h2><span className="muted">{decision?stamp(decision.observed_at):'판단 대기'}</span></div>
    <div className="allocation"><span>목표 자산 비중 (BTC)</span><strong>{decision?`${decision.target}%`:'—'}</strong><span className="decision-source">{decision?.source==='jev'?'Jev · TypeSafe':decision?'규칙 전략 · 이동평균':'관찰할 전략을 선택하세요'}</span></div>
    <div className="probabilities"><p>선택 확률 <span>· 수익 확률이 아닙니다</span></p>
      {[0,25,50,75,100].map(target=><div className="probability" key={target}><label>{target}%</label><div><i className={decision?.target===target?'selected':''} style={{width:hasProb?`${(decision.probabilities[String(target)]??0)*100}%`:'0%'}}/></div><b>{hasProb?`${Math.round((decision.probabilities[String(target)]??0)*100)}%`:'—'}</b></div>)}
      <small>{hasProb?'모델이 반환한 행동별 선택 확률':decision?'규칙 전략은 확률을 생성하지 않습니다.':'첫 판단 후 실제 결과가 표시됩니다.'}</small>
    </div>
    <div className="account-grid"><div><span>추론 지연 시간</span><b>{decision?.source==='jev'?`${money(decision.latency_ms,0)} ms`:'—'}</b><span>모델 호출 / 한도</span><b>{run?.calls??0} <em>/ {run?.max_calls??100}</em></b></div><div><span>계좌 현황 (USDT)</span><dl><dt>보유 현금</dt><dd>{money(account.cash)}</dd><dt>보유 BTC</dt><dd>{money(account.btc,6)}</dd><dt>누적 거래</dt><dd>{account.trades}회</dd></dl></div></div>
    {live && <p className="live-note">{run.running?'서버가 실행 중이면 창을 닫아도 관찰을 계속합니다.':'연결하면 최근 마감 봉부터 판단합니다.'}</p>}
  </aside>;
}

export function Journal({events,onExport}:{events:Decision[];onExport:()=>void}) {
  return <section className="panel journal"><div className="panel-heading"><h2>판단 / 거래 기록 <span className="count">{events.length}</span></h2><button className="icon-button" onClick={onExport} disabled={!events.length} aria-label="실험 JSON 내보내기" title="실험 JSON 내보내기"><Download size={16}/></button></div><div className="table-scroll"><table><thead><tr><th>체결 시간 (UTC)</th><th>판단</th><th>액션</th><th>체결가 (USDT)</th><th>수량 (BTC)</th></tr></thead><tbody>{events.slice(-100).reverse().map(e=><tr key={e.index} title={`${e.note} · 관찰 ${stamp(e.observed_at)} UTC · 수수료 ${money(e.fee)} USDT`}><td>{stamp(e.time)}</td><td>{e.target}%</td><td className={e.side==='buy'?'accent':e.side==='sell'?'negative':'muted'}>{e.side==='buy'?<ArrowDownLeft size={13}/>:e.side==='sell'?<ArrowUpRight size={13}/>:null}{e.side==='buy'?'매수':e.side==='sell'?'매도':'유지'}</td><td>{e.side==='hold'?'—':money(e.price)}</td><td>{e.side==='hold'?'—':money(e.quantity,6)}</td></tr>)}</tbody></table>{!events.length && <div className="empty-journal"><span>아직 기록된 판단이 없습니다.</span><small>한 단계씩 진행하며 Jev의 선택을 관찰하세요.</small></div>}</div></section>;
}
