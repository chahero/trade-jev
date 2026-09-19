import {useEffect,useState} from 'react';
import {Activity,ChevronRight,Database,LoaderCircle,Pause,Play,Radio,RotateCcw,SkipForward,X} from 'lucide-react';
import {useTrader} from './useTrader';
import {DecisionPanel,Journal,Metrics} from './components/Panels';
import {EquityChart,PriceChart} from './components/Charts';
import {initial,money,stamp} from './types';
import type {Config} from './types';

export default function App(){
  const t=useTrader();
  const [config,setConfig]=useState<Config>({mode:'historical',strategy:'rule',start:'2025-01-01',end:'2025-01-08',max_calls:100});
  const run=t.run;
  useEffect(()=>{if(run)setConfig({mode:run.mode,strategy:run.strategy,start:run.start,end:run.end,max_calls:run.max_calls});},[run?.id]);
  const count=t.view??run?.points.length??0;
  const replay=t.view!==null;
  const points=run?.points.slice(0,count)??[];
  const events=run?.events.slice(0,count)??[];
  const account=replay?(points.at(-1)??initial):(run?.account??initial);
  const decision=events.at(-1)??null;
  const candles=run?.mode==='historical'?run.candles.slice(0,run.warmup+count):run?.candles??[];
  const budgetReached=run?.strategy==='jev' && run.calls>=run.max_calls;
  const canAdvance=!!run && run.mode==='historical' && !t.busy && !t.playing && (replay?count<run.points.length:!run.finished&&!budgetReached);
  const estimate=Math.max(0,Math.round((Date.parse(config.end)-Date.parse(config.start))/86400000))*96;
  const changeMode=(mode:Config['mode'])=>{if(run?.running)return;if(mode!==config.mode)t.clear();t.setPlaying(false);setConfig({...config,mode});};
  const exportRun=()=>{if(run)window.location.assign(`/api/runs/${run.id}/export`);};
  const currentMode=run?.mode??config.mode;
  return <><header className="topbar"><a className="brand" href="/">JEV <span>/ TRADER</span></a><nav aria-label="모드"><button className={config.mode==='historical'?'active':''} onClick={()=>changeMode('historical')} disabled={t.busy}>과거 시뮬레이션</button><button className={config.mode==='live'?'active':''} onClick={()=>changeMode('live')} disabled={t.busy}>실시간 모의매매</button></nav><div className="local-status"><i/> LOCAL PAPER ACCOUNT</div></header>
    <main><section className="setup"><div className="intro"><h1>{config.mode==='historical'?'시장을 되감고, 판단을 관찰하다.':'흐르는 시장, 이어지는 판단.'}</h1><p>BTC / USDT <span>·</span> Binance Spot <span>·</span> 15분봉</p></div><form className="setup-form" onSubmit={e=>{e.preventDefault();void t.create(config);}}>
      {config.mode==='historical' && <div className="date-group"><label>기간 (UTC)<input aria-label="시작일" type="date" value={config.start} onChange={e=>setConfig({...config,start:e.target.value})} required disabled={t.busy}/></label><span className="date-separator">~</span><label>종료일 미포함<input aria-label="종료일" type="date" value={config.end} onChange={e=>setConfig({...config,end:e.target.value})} required disabled={t.busy}/></label></div>}
      <label>전략<select aria-label="전략" value={config.strategy} onChange={e=>setConfig({...config,strategy:e.target.value as Config['strategy']})} disabled={t.busy}><option value="rule">규칙 전략</option><option value="jev" disabled={!t.ready}>Jev · TypeSafe{!t.ready?' (키 필요)':''}</option></select></label>
      <label className="limit-label">Jev 호출 한도<input aria-label="Jev 호출 한도" type="number" min="1" max="3000" value={config.max_calls} onChange={e=>setConfig({...config,max_calls:Number(e.target.value)})} required disabled={t.busy}/></label>
      <button className="primary load" disabled={t.busy||!!run?.running} type="submit">{t.busy?<LoaderCircle className="spin" size={16}/>:config.mode==='historical'?<Database size={16}/>:<Radio size={16}/>} {config.mode==='historical'?'데이터 불러오기':'모의계좌 만들기'}</button>
    </form></section>
    <div className="session-strip"><span><i className={t.ready?'status-dot':'status-dot off'}/>{t.ready?'Jev 키 설정됨':'Jev 키 미설정'}<span className="divider">/</span>{config.mode==='historical'?`${estimate.toLocaleString()}개 봉 · ${config.strategy==='jev'?`최대 ${Math.min(estimate,config.max_calls)}회 호출`:'API 호출 비용 없음'}`:'5초 간격 시세 갱신 · 15분봉 마감 후 판단'}</span><label>저장된 실험<select aria-label="저장된 실험" value={run?.id??''} disabled={t.busy||t.playing||!!run?.running} onFocus={()=>void t.refresh()} onChange={e=>{if(e.target.value)void t.load(e.target.value);}}><option value="">실험 선택</option>{t.saved.map(s=><option key={s.id} value={s.id}>{s.mode==='live'?'LIVE':s.start} · {s.strategy==='jev'?'Jev':'규칙'} · {s.steps}단계 · {new Date(s.created_at).toLocaleTimeString('ko-KR')}</option>)}</select></label></div>
    {t.error && <div className="error" role="alert"><span>{t.error}</span><button className="icon-button" aria-label="오류 닫기" onClick={()=>t.setError('')}><X size={16}/></button></div>}
    <Metrics account={account}/>
    <div className="main-grid"><section className="panel market-panel"><PriceChart candles={candles} events={events}/><div className="playback">
      {currentMode==='historical'?<><button className="primary" disabled={!run||(!t.playing&&(t.busy||(replay?count>=run.points.length:(run.finished||budgetReached))))} onClick={()=>t.setPlaying(!t.playing)}>{t.playing?<Pause size={16}/>:<Play size={16}/>} {t.playing?'일시정지':replay?'기록 재생':'재생'}</button><button disabled={!canAdvance} onClick={()=>{if(replay&&run&&count<run.points.length)t.setView(count+1);else void t.step();}}><SkipForward size={16}/> 한 단계</button><label className="speed">재생 속도<select aria-label="재생 속도" value={t.speed} onChange={e=>t.setSpeed(Number(e.target.value))}><option value={1}>1×</option><option value={4}>4×</option><option value={16}>16×</option></select></label><input className="timeline" aria-label="저장된 판단 탐색" type="range" min="0" max={run?.points.length||1} value={count} disabled={!run?.points.length||t.busy||t.playing} onChange={e=>t.setView(Number(e.target.value))}/><span className="playback-date">{points.length?stamp(points.at(-1)!.time):'판단 대기'}</span><button className="reset" disabled={!run?.points.length||t.busy||t.playing} onClick={()=>t.setView(replay?null:0)} title="저장된 기록은 API 호출 없이 다시 볼 수 있습니다"><RotateCcw size={16}/>{replay?'최신으로':'기록 되감기'}</button></>:<><button className="primary" disabled={!run||t.busy} onClick={()=>void t.toggleLive()}>{run?.running?<Pause size={16}/>:<Radio size={16}/>} {run?.running?'연결 중지':'실시간 연결'}</button><span className="live-price">{run?`${money(run.price)} USDT`:'시세 대기'}</span><span className="muted">{run?.quote_at?`최근 수신 ${stamp(run.quote_at)} UTC`:'연결 후 최신 시세로 모의 체결'}</span></>}
    </div><div className="run-status"><span><Activity size={12}/>{!run?'데이터를 불러온 뒤 재생을 눌러 시작하세요.':run.mode==='live'?run.running?(run.quote_at&&Date.now()-run.quote_at>30000?'시세 지연 · 연결 확인 중':'실시간 모의계좌 관찰 중'):'실시간 모의계좌 대기':replay?'저장된 기록 재생 · 추가 모델 호출 없음':t.busy?'판단 요청 중 · 일시정지 시 현재 요청까지 완료됩니다':run.finished?'실험 완료':budgetReached?'Jev 호출 한도 도달':t.playing?'시뮬레이션 진행 중':'시뮬레이션 일시정지'}</span><span>{run?.mode==='historical'?`${count} / ${run.total} 단계`:'서버 재시작 시 자동 정지'}<ChevronRight size={12}/></span></div></section><DecisionPanel run={run} decision={decision} account={account}/></div>
    <div className="bottom-grid"><EquityChart points={points} strategy={run?.strategy??config.strategy}/><Journal events={events} onExport={exportRun}/></div>
    <footer><span>JEV / TRADER <b>|</b> 실제 시세로 관찰하는 가상 거래 계좌</span><span>현물 · 레버리지 없음 · 모든 시간 UTC</span></footer>
  </main></>;
}
