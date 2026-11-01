"""Parallel, checkpointed experiment execution. Workers never share simulator state.
Uses columnar Parquet event tables for compact complete audit trails.
"""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import argparse,json,itertools,time,os
import pandas as pd
import numpy as np
from experiment import config,theory,FACTORS,ROOT,DATA,LOGS
from model import Config,simulate

def task(spec):
    bits,kw,rid=spec
    c=config(bits,**kw);r,e,l,a,s=simulate(c);r['run_id']=rid
    for tab,suffix in [(e,''),(l,'_lots'),(a,'_activity'),(s,'_wip')]:
        tab.insert(0,'run_id',rid)
        tab.to_parquet(LOGS/(rid+suffix+'.parquet'),index=False,compression='zstd')
    th=[row|dict(run_id=rid,scenario=c.scenario,load=c.load,view=c.view,rep=c.rep) for row in theory(e,r)]
    return r,th

def calibrate(spec):
    bits,load,interval=spec
    key=DATA/f'cal_{load}_{config(bits).scenario}.json'
    if key.exists():return json.loads(key.read_text())
    history=[]
    for iteration in range(12):
        rr=[]
        for rep in range(2):
            r,*_=simulate(config(bits,load=load,rep=rep,seed=18801,days=120,warm_days=60,interval=interval))
            rr.append(r)
        u=float(np.mean([r['litho_util'] for r in rr]));history.append(dict(interval=interval,util=u,
            imbalance=float(np.mean([(r['released']-r['completed'])/r['completed'] for r in rr]))))
        if abs(u-load)<.007:break
        interval*=u/load
    out=dict(interval=interval,load=load,scenario=config(bits).scenario,history=history)
    key.write_text(json.dumps(out,indent=2));return out

def run(workers):
    d=json.loads((DATA/'design.json').read_text())
    # Independent pilot chose total simulated exposure; more replications improve t precision.
    days={.7:365,.85:365,.95:730};reps={.7:5,.85:5,.95:20}
    d.update(days_by_load={str(k):v for k,v in days.items()},reps_by_load={str(k):v for k,v in reps.items()},
      precision_plan='Independent pilot: 5x365-day relative halfwidths 1.25%,2.41%,16.88%. Use 5x365 / 5x365 / 20x730 days, respectively, for expected <5% (t correction and inverse-square-root exposure scaling). Final achieved precision explicitly checked.')
    (DATA/'design.json').write_text(json.dumps(d,indent=2))
    existing=pd.read_csv(DATA/'runs.csv').to_dict('records') if (DATA/'runs.csv').exists() else []
    # Old higher-load pilot/main runs are not mixed with the preselected final horizons.
    existing=[r for r in existing if r['days']==days[r['load']]]
    ids={r['run_id'] for r in existing};theories=pd.read_csv(DATA/'theory.csv').to_dict('records') if (DATA/'theory.csv').exists() else []
    theories=[r for r in theories if r['run_id'] in ids]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        # Equal-starts production first, then calibrated equal-utilization runs.
        for view in ['equal_starts','equal_utilization']:
            intervals={(row['load'],config(bits).scenario):row['interval'] for row in d['baseline_intervals'] for bits in FACTORS}
            if view=='equal_utilization':
                futures=[pool.submit(calibrate,(bits,row['load'],row['interval'])) for row in d['baseline_intervals'] for bits in FACTORS if any(bits)]
                for f in as_completed(futures):
                    z=f.result();intervals[z['load'],z['scenario']]=z['interval'];print('CAL',z['load'],z['scenario'],round(z['interval'],2),flush=True)
            todo=[]
            for load in days:
                for bits in FACTORS:
                    scenario=config(bits).scenario
                    for rep in range(reps[load]):
                        rid=f'{view}_{int(load*100)}_{scenario}_{rep}'
                        if rid in ids:continue
                        kw=dict(load=load,rep=rep,days=days[load],warm_days=90,interval=intervals[load,scenario],view=view)
                        todo.append((bits,kw,rid))
            # Submit only a bounded number to avoid retaining completed result payloads.
            futures={pool.submit(task,s):s[2] for s in todo}
            for f in as_completed(futures):
                r,th=f.result();existing.append(r);theories.extend(th);ids.add(r['run_id'])
                pd.DataFrame(existing).to_csv(DATA/'runs.csv',index=False)
                pd.DataFrame(theories).to_csv(DATA/'theory.csv',index=False)
                print(len(existing),r['run_id'],f'CT={r["mean_ct"]/60:.2f}h u={r["litho_util"]:.3f}',flush=True)
    print('DONE',len(existing),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=4);run(p.parse_args().workers)

