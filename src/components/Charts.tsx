import {useEffect,useId,useRef,useState} from 'react';
import type {Candle,Decision,Point} from '../types';
import {money,stamp} from '../types';

type Series = {name:string;color:string;values:number[];dash?:boolean};
function Plot({times,series,height=230,markers=[]}:{times:number[];series:Series[];height?:number;markers?:{index:number;side:string}[]}) {
  const [hover,setHover]=useState<number|null>(null);
  const container=useRef<HTMLDivElement>(null);
  const [width,setWidth]=useState(1000);
  useEffect(()=>{
    const element=container.current;
    if(!element)return;
    const observer=new ResizeObserver(entries=>setWidth(Math.max(220,entries[0].contentRect.width)));
    observer.observe(element);
    return ()=>observer.disconnect();
  },[times.length>0]);
  const id=useId();
  const w=width,pad={left:12,right:68,top:20,bottom:30};
  const values=series.flatMap(s=>s.values);
  const min=Math.min(...values),max=Math.max(...values),spread=Math.max(max-min,max*.004,1);
  const lo=min-spread*.15,hi=max+spread*.15;
  const x=(i:number)=>pad.left+i/Math.max(1,times.length-1)*(w-pad.left-pad.right);
  const y=(v:number)=>pad.top+(hi-v)/(hi-lo)*(height-pad.top-pad.bottom);
  if(!times.length) return <div className="empty-chart" style={{height}}><div className="empty-cross"/><span>데이터를 불러오면 관찰이 시작됩니다.</span><small>실제 BTC/USDT 시세 · 가상 자금 10,000 USDT</small></div>;
  const active=hover!==null?Math.min(hover,times.length-1):null;
  const tickCount=w<500?3:5;
  const ticks=[...new Set(Array.from({length:tickCount},(_,i)=>Math.round(i/(tickCount-1)*(times.length-1))))];
  return <div className="plot" ref={container} onMouseLeave={()=>setHover(null)}>
    <svg viewBox={`0 0 ${w} ${height}`} role="img" aria-label={series.map(s=>s.name).join(', ')+' 시계열 차트'} onMouseMove={e=>{const rect=e.currentTarget.getBoundingClientRect();setHover(Math.max(0,Math.min(times.length-1,Math.round(((e.clientX-rect.left)/rect.width*w-pad.left)/(w-pad.left-pad.right)*(times.length-1)))));}}>
      <defs><clipPath id={id}><rect x={pad.left} y={pad.top} width={w-pad.left-pad.right} height={height-pad.top-pad.bottom}/></clipPath></defs>
      {Array.from({length:5},(_,i)=>{const v=lo+(hi-lo)*i/4;return <g key={i}><line className="grid-line" x1={pad.left} x2={w-pad.right} y1={y(v)} y2={y(v)}/><text x={w-pad.right+12} y={y(v)+4}>{money(v,0)}</text></g>;})}
      {ticks.map((idx,i)=><g key={idx}><line className="grid-line vertical" x1={x(idx)} x2={x(idx)} y1={pad.top} y2={height-pad.bottom}/><text x={x(idx)} y={height-8} textAnchor={i===0?'start':i===ticks.length-1?'end':'middle'}>{stamp(times[idx]).slice(5,10)} {times.length<100?stamp(times[idx]).slice(11):''}</text></g>)}
      <g clipPath={`url(#${id})`}>{[...series].reverse().map(s=><polyline key={s.name} fill="none" stroke={s.color} strokeWidth="1.8" vectorEffect="non-scaling-stroke" strokeDasharray={s.dash?'4 5':undefined} points={s.values.map((v,i)=>`${x(i)},${y(v)}`).join(' ')}/>)}</g>
      {markers.map((m,i)=><circle key={i} cx={x(m.index)} cy={y(series[0].values[m.index])} r="4" fill={m.side==='buy'?'#c5ef71':'#ef8c83'} stroke="#101214" strokeWidth="2"/>)}
      {times.length===1 && series.map(s=><circle key={s.name} cx={x(0)} cy={y(s.values[0])} r="3" fill={s.color}/>)}
      {active!==null && <line x1={x(active)} x2={x(active)} y1={pad.top} y2={height-pad.bottom} stroke="#79838c" strokeDasharray="3 4"/>}
    </svg>
    {active!==null && <div className="chart-tooltip"><span>{stamp(times[active])} UTC</span>{series.map(s=><span key={s.name} style={{color:s.color}}>{s.name} {money(s.values[active])}</span>)}</div>}
  </div>;
}

export function PriceChart({candles,events}:{candles:Candle[];events:Decision[]}) {
  const last=candles.at(-1);
  const displayed=candles.slice(-400);
  const markers=events.filter(e=>e.side!=='hold').flatMap(e=>{const index=displayed.findIndex(c=>e.time>=c.time && e.time<c.time+900000);return index<0?[]:[{index,side:e.side}];});
  return <><div className="panel-heading"><div><h2>BTC / USDT</h2><p>Binance Spot · 15분봉</p></div><div className="ohlc">{last?<><span>시 <b>{money(last.open)}</b></span><span>고 <b>{money(last.high)}</b></span><span>저 <b>{money(last.low)}</b></span><span>종 <b className="accent">{money(last.close)}</b></span></>:<span>시세 대기 중</span>}</div></div><Plot times={displayed.map(c=>c.time)} series={[{name:'BTC/USDT',color:'#c5ef71',values:displayed.map(c=>c.close)}]} height={290} markers={markers}/></>;
}

export function EquityChart({points,strategy}:{points:Point[];strategy:string}) {
  const legend=[{name:strategy==='jev'?'Jev':'선택 전략',color:'#c5ef71',values:points.map(p=>p.equity)},
    {name:'Buy & hold',color:'#a4b0c0',values:points.map(p=>p.buy_hold)},
    {name:'규칙 전략',color:'#7ea3c0',values:points.map(p=>p.rule)},
    {name:'현금',color:'#68737c',values:points.map(()=>10000),dash:true}];
  return <section className="panel equity"><div className="panel-heading"><h2>계좌 자산 비교</h2><div className="legend">{legend.map(s=><span key={s.name}><i style={{background:s.color}}/>{s.name}</span>)}</div></div><Plot times={points.map(p=>p.time)} series={legend} height={210}/><div className="chart-footnote">동일한 초기 자금 · 수수료 0.10% · 슬리피지 0.05% / 편도</div></section>;
}
