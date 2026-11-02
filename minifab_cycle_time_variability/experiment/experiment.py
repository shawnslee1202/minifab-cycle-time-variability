"""Experiment runner: independent pilots, calibrated loads, replicated factorials.
Run python -m minifab_cycle_time_variability.experiment.experiment --phase pilot, then --phase main, then analyze.py.
"""
from pathlib import Path
import argparse,json,itertools,time,sqlite3
import numpy as np
import pandas as pd
from scipy.stats import t
from minifab_cycle_time_variability.model.model import Config,simulate
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'results';DATA.mkdir(exist_ok=True)
LOGS=DATA/'events';LOGS.mkdir(exist_ok=True)
FACTORS=list(itertools.product([0,1],repeat=4))
def config(bits,**kw):return Config(**dict(zip('ABCD',bits)),**kw)
def theory(e,r):
    rows=[];warm=r['warm_days']*1440;end=(r['warm_days']+r['days'])*1440
    for station,m in [('Diffusion',2),('Implant',2),('Lithography',1)]:
        x=e[(e.station==station)&(e.start>=warm)&e.end.notna()].copy()
        arrivals=np.sort(e.loc[(e.station==station)&(e.queue_in>=warm),'queue_in'].to_numpy())
        gaps=np.diff(arrivals);ca=np.var(gaps,ddof=1)/np.mean(gaps)**2
        if station=='Diffusion':
            z=x.groupby('batch_id').agg(start=('start','first'),end=('end','first'),ready=('queue_in','max'),n=('step','size'))
            eff=(z.end-z.start).to_numpy();bgaps=np.diff(np.sort(z.ready))
            ca=np.var(bgaps,ddof=1)/np.mean(bgaps)**2
            lam=len(z)/(end-warm)
            formation=float((x.groupby('batch_id').queue_in.transform('max')-x.queue_in).mean())
            classical=r['interval_actual'] # (3-1)/(2*lambda_recipe), per visit
        else:
            eff=(x.end-x.start).to_numpy();lam=len(x)/(end-warm);formation=0;classical=0
        te=np.mean(eff);ce=np.var(eff,ddof=1)/te**2;u=lam*te/m
        naive=(ca+ce)/2*u/max(1e-6,1-u)*te
        corrected=(ca+ce)/2*u**(np.sqrt(2*(m+1))-1)/(m*max(1e-6,1-u))*te
        observed=float((x.start-x.queue_in).mean())
        estimate=corrected+classical if station=='Diffusion' else corrected
        rows.append(dict(station=station,ca2=ca,ce2=ce,te=te,u=u,servers=m,
            naive_vut=naive,multiserver_vut=corrected,batch_formation_observed=formation,
            batch_formation_renewal=classical,estimated_queue=estimate,observed_queue=observed,
            error_pct=100*(estimate-observed)/observed))
    return rows

def pilot():
    logs=[];cal=[]
    # Two independent pilot seeds averaged; update interval proportional to measured utilization.
    for load in [.70,.85,.95]:
        interval=115/((690/720)*load)
        for iteration in range(12):
            rr=[]
            for rep in range(2):
                r,e,l,a,s=simulate(Config(load=load,rep=rep,seed=9811,days=120,warm_days=45,interval=interval))
                rr.append(r['litho_util'])
                logs.append(dict(load=load,iteration=iteration,interval=interval,rep=rep,util=r['litho_util'],ct=r['mean_ct']))
            obs=np.mean(rr)
            if abs(obs-load)<.006:break
            interval*=obs/load
        cal.append(dict(load=load,interval=interval,observed=obs))
    pd.DataFrame(logs).to_csv(DATA/'calibration.csv',index=False)
    (DATA/'design.json').write_text(json.dumps({'baseline_intervals':cal,'warm_days':90,'days':365,'replications':5},indent=2))
    # Welch ensemble across all baseline loads, with independent seeds.
    ss=[];rs=[]
    for item in cal:
        for rep in range(5):
            r,e,l,a,s=simulate(Config(load=item['load'],rep=rep,seed=19331,days=365,warm_days=0,interval=item['interval']))
            s['load']=item['load'];s['rep']=rep;ss.append(s);rs.append(r)
    pd.concat(ss).to_csv(DATA/'warmup_samples.csv',index=False)
    pd.DataFrame(rs).to_csv(DATA/'pilot_runs.csv',index=False)
    print('Pilot completed',cal,flush=True)

def main_run():
    design=json.loads((DATA/'design.json').read_text());results=[];theories=[]
    db=sqlite3.connect(DATA/'reporting.sqlite')
    # Resume completed runs, including their event logs.
    checkpoint=DATA/'runs.csv'
    if checkpoint.exists():results=pd.read_csv(checkpoint).to_dict('records')
    tt=DATA/'theory.csv'
    if tt.exists():theories=pd.read_csv(tt).to_dict('records')
    existing={r['run_id'] for r in results}
    for view in ['equal_starts','equal_utilization']:
      for item in design['baseline_intervals']:
       load=item['load']
       for bits in FACTORS:
        scenario=config(bits).scenario
        interval=item['interval']
        # Equal utilization targets occupied/available litho time, including operator blocking.
        # Baseline reused, other scenarios independently calibrated using pilot seeds.
        if view=='equal_utilization' and any(bits):
            key=DATA/f'cal_{load}_{scenario}.json'
            if key.exists():interval=json.loads(key.read_text())['interval']
            else:
                history=[]
                for iteration in range(12):
                    obs=[]
                    for rep in range(2):
                        r,*_=simulate(config(bits,load=load,rep=rep,seed=18801,days=90,warm_days=45,interval=interval))
                        obs.append(r['litho_util'])
                    u=float(np.mean(obs));history.append(dict(interval=interval,util=u))
                    if abs(u-load)<.007:break
                    interval*=u/load
                key.write_text(json.dumps(dict(interval=interval,history=history),indent=2))
        for rep in range(design['replications']):
            rid=f'{view}_{int(load*100)}_{scenario}_{rep}'
            if rid in existing:continue
            c=config(bits,load=load,rep=rep,days=design.get('days_by_load',{}).get(str(load),design['days']),warm_days=design['warm_days'],interval=interval,view=view)
            r,e,l,a,s=simulate(c);r['run_id']=rid
            for tab in [e,l,a,s]:tab.insert(0,'run_id',rid)
            e.to_csv(LOGS/(rid+'.csv.gz'),index=False,compression={'method':'gzip','compresslevel':1})
            # Every lot and machine interval retained; compact SQL contains all run summaries,
            # plus six representative detailed replications. All detailed events remain in gzip.
            l.to_csv(LOGS/(rid+'_lots.csv.gz'),index=False,compression={'method':'gzip','compresslevel':1})
            a.to_csv(LOGS/(rid+'_activity.csv.gz'),index=False,compression={'method':'gzip','compresslevel':1})
            if view=='equal_starts' and load==.85 and rep==0 and scenario in ['Baseline','A','B','C','D','ABCD']:
                for name,tab in [('events',e),('lots',l),('activity',a),('wip_samples',s)]:
                    tab.to_sql(name,db,if_exists='append',index=False)
            for row in theory(e,r):theories.append(row|dict(run_id=rid,scenario=scenario,load=load,view=view,rep=rep))
            results.append(r);pd.DataFrame(results).to_csv(checkpoint,index=False)
            pd.DataFrame(theories).to_csv(tt,index=False)
            print(f'{len(results)}/480 {rid}: CT {r["mean_ct"]/60:.2f} h, u {r["litho_util"]:.3f}',flush=True)
    pd.DataFrame(results).to_sql('runs',db,if_exists='replace',index=False)
    db.close()

def extras():
    d=json.loads((DATA/'design.json').read_text());interval=next(x['interval'] for x in d['baseline_intervals'] if x['load']==.85)
    rr=pd.read_csv(DATA/'extras.csv').to_dict('records') if (DATA/'extras.csv').exists() else []
    completed_extra={(r['case'],r['rep']) for r in rr}
    cases=[('mix_baseline',dict(mix=True)),('mix_all',dict(mix=True,A=1,B=1,C=1,D=1))]
    cases +=[(f'A_wait_{v}',dict(A=1,partial_wait=v)) for v in [30,60,240,360]]
    cases +=[(f'B_scale_{v}',dict(B=1,setup_scale=v)) for v in [0,.25,.75]]
    cases +=[(f'C_scale_{v}',dict(C=1,repair_scale=v)) for v in [0,.25,.75]]
    cases += [('benchmark_exp',dict(mix=True,interval=120)),('benchmark_constant',dict(mix=True,interval=120,D=1))]
    for name,kw in cases:
        for rep in range(5):
            if (name,rep) in completed_extra:continue
            opts=dict(load=.85,interval=interval,rep=rep,days=d['days'],warm_days=d['warm_days'],view='sensitivity');opts.update(kw)
            r,e,l,a,s=simulate(Config(**opts));r['case']=name;rid=f'extra_{name}_{rep}';r['run_id']=rid
            for tab,suffix in [(e,''),(l,'_lots'),(a,'_activity')]:
                tab.insert(0,'run_id',rid);tab.to_csv(LOGS/(rid+suffix+'.csv.gz'),index=False,compression={'method':'gzip','compresslevel':1})
            rr.append(r);pd.DataFrame(rr).to_csv(DATA/'extras.csv',index=False)
            print(name,rep,round(r['mean_ct']/60,2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['pilot','main','extras'],required=True)
    {'pilot':pilot,'main':main_run,'extras':extras}[p.parse_args().phase]()



