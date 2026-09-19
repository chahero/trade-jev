import {useCallback,useEffect,useRef,useState} from 'react';
import {api} from './api';
import type {Config,Run,Saved} from './types';

export function useTrader() {
  const [run,setRun] = useState<Run|null>(null);
  const [saved,setSaved] = useState<Saved[]>([]);
  const [ready,setReady] = useState(false);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [playing,setPlaying] = useState(false);
  const [speed,setSpeed] = useState(4);
  const [view,setView] = useState<number|null>(null);
  const inFlight = useRef(false);
  const generation = useRef(0);
  const refresh = useCallback(async()=>setSaved(await api<Saved[]>('/runs')),[]);
  useEffect(()=> { Promise.all([api<{jev_configured:boolean}>('/status').then(s=>setReady(s.jev_configured)),refresh()]).catch(e=>setError(e.message)); },[refresh]);
  const create = async(config:Config) => {
    if(inFlight.current) return;
    generation.current++; inFlight.current=true; setBusy(true);setPlaying(false);setError('');
    try {setRun(await api<Run>('/runs',config));setView(null);await refresh();}
    catch(e){setError((e as Error).message);}
    finally {inFlight.current=false;setBusy(false);}
  };
  const load = async(id:string)=> {
    if(inFlight.current) return;
    generation.current++; inFlight.current=true;setBusy(true);setPlaying(false);setError('');
    try {setRun(await api<Run>(`/runs/${id}`));setView(null);}
    catch(e){setError((e as Error).message);}
    finally{inFlight.current=false;setBusy(false);}
  };
  const step = useCallback(async()=> {
    if(!run || inFlight.current || run.finished) return;
    inFlight.current=true;setBusy(true);setError('');
    try {const updated=await api<Run>(`/runs/${run.id}/step`,{});setRun(updated);setView(null);if(updated.finished)setPlaying(false);}
    catch(e){setError((e as Error).message);setPlaying(false);const latest=await api<Run>(`/runs/${run.id}`).catch(()=>null);if(latest)setRun(latest);}
    finally{inFlight.current=false;setBusy(false);}
  },[run]);
  useEffect(()=> {
    if(!playing || busy || !run) return;
    const timer=window.setTimeout(()=>{
      if(view!==null && view<run.points.length){setView(view+1);if(view+1===run.points.length)setPlaying(false);}
      else if(view===null && !run.finished) void step();
      else setPlaying(false);
    },1000/speed);
    return ()=>clearTimeout(timer);
  },[playing,busy,run,view,speed,step]);
  useEffect(()=> {
    if(!run || run.mode!=='live' || !run.running) return;
    const id=run.id, token=generation.current;
    let polling=false;
    const timer=window.setInterval(async()=>{
      if(polling)return;polling=true;
      try{const next=await api<Run>(`/runs/${id}`);if(token===generation.current){setRun(next);if(next.error)setError(next.error);}}
      catch(e){if(token===generation.current)setError((e as Error).message);}
      finally{polling=false;}
    },2000);
    return ()=>clearInterval(timer);
  },[run?.id,run?.running,run?.mode]);
  const toggleLive=async()=>{
    if(!run || inFlight.current)return;
    inFlight.current=true;setBusy(true);setError('');
    try{setRun(await api<Run>(`/runs/${run.id}/live`,{running:!run.running}));await refresh();}
    catch(e){setError((e as Error).message);}
    finally{inFlight.current=false;setBusy(false);}
  };
  const clear=()=>{if(inFlight.current||run?.running)return;generation.current++;setPlaying(false);setRun(null);setView(null);};
  return {run,saved,ready,busy,error,setError,playing,setPlaying,speed,setSpeed,view,setView,create,load,step,toggleLive,refresh,clear};
}
